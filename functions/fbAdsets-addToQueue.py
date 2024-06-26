import json
import os
import boto3
import datetime
import math
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
SQS_QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdsetCreation.fifo"
LAMBDA_ARN = "arn:aws:lambda:ap-southeast-1:533267173231:function:fbAdsets-checkStatus"
ROLE_ARN = "arn:aws:iam::533267173231:role/Scheduler_fbAdsets-checkStatus"

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '🤖Rob_FB_Adsets'

TIMEOUT = 10
CONCURRENCY = 10

def slack_post_message(channel_id, token, message):
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())

def get_aws_secret(secret_name):
    secret_name = urlparse.quote(secret_name, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")
    return token

def lambda_handler(event, context):
    channel_id    = event['channel_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id = event['spreadsheet_id']

    adsets_created = 0
    sqs = boto3.client('sqs', region_name='ap-southeast-1')
    scheduler = boto3.client('scheduler', region_name='ap-southeast-1')
    
    # Get the token from AWS Parameter Store
    token = get_aws_secret(SECRET_NAME)

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_post_message(channel_id, token, ':rocket: Starting bulk adset creation! :rocket:')
    print("Ack sent to Slack")

    # Get the data from Google Sheets
    gs_count_endpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A1?access_token={gs_access_token}'
    response = requests.get(gs_count_endpoint)
    if response.status_code != 200:
        print(response.json())
    row_count = response.json()['values'][0][0]
    print(f"Number of rows in Google Sheets: {row_count}")
    row_num = str(int(row_count) + 2)
    gs_endpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A3:Q{row_num}?access_token={gs_access_token}'
    print("Getting data from Google Sheets")
    response = requests.get(gs_endpoint)
    if response.status_code != 200:
        print(response.json())
    data = response.json()['values']
    print("Data retrieved from Google Sheets")
    print(data)

    # Create the adsets for rows without an adset ID
    for row in data:
        if row[1] == "":
            adset_name        = row[0]
            campaign_id       = row[2]
            destination_type  = row[3]
            optimization_goal = row[4]
            bid_strategy      = row[5]
            bid_amount        = row[6]
            billing_event     = row[7]
            daily_budget      = row[8]
            status            = row[10]
            targeting         = row[13]
            start_time        = row[14]
            end_time          = row[15]

            payload = {
                'ad_account_id': ad_account_id,
                'access_token': fb_access_token,
                'adset_name': adset_name,
                'campaign_id': campaign_id,
                'destination_type': destination_type,
                'optimization_goal': optimization_goal,
                'bid_strategy': bid_strategy,
                'bid_amount': bid_amount,
                'billing_event': billing_event,
                'daily_budget': daily_budget,
                'targeting': json.dumps(targeting),
                'status': status,
                'start_time': start_time,
                'end_time': end_time,
                'spreadsheet_id': spreadsheet_id,
                'row_number': f'{data.index(row) + 3}',
                'gs_access_token': gs_access_token
            }

            # Send a message to the SQS queue
            print("Sending message to SQS")
            response = sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(payload),
                MessageGroupId=f'adset-{adset_name}'
            )
            print(f"Message sent to SQS: {response}")

            adsets_created += 1

    if adsets_created == 0:
        slack_post_message(channel_id, token, ':question: No adsets were created! :question:')
        return {
            'statusCode': 200
        }

    timer_seconds_full = math.ceil(adsets_created/CONCURRENCY)*TIMEOUT
    timer_minutes = math.floor(timer_seconds_full/60)
    timer_seconds = timer_seconds_full % 60

    # Get the current time in UTC
    datetime_now = datetime.datetime.now()
    # Get the seconds to the next minute
    seconds_to_next_minute = 60 - datetime_now.second
    if seconds_to_next_minute < timer_seconds:
        datetime_timer = datetime_now + datetime.timedelta(minutes=timer_minutes+2) - datetime.timedelta(seconds=datetime_now.second)
    else:
        datetime_timer = datetime_now + datetime.timedelta(minutes=timer_minutes+1) - datetime.timedelta(seconds=datetime_now.second)

    # Create a scheduled event to check the status of the adsets
    response = scheduler.create_schedule(
        ActionAfterCompletion='DELETE',
        Description='Check the status of the adsets created',
        FlexibleTimeWindow={
            'Mode': 'OFF'
        },
        Name='fbAdsets-checkStatus',
        ScheduleExpression=f'at({datetime_timer.strftime("%Y-%m-%dT%H:%M:%S")})',
        Target={
            'Arn': LAMBDA_ARN,
            'Input': json.dumps({
                'channel_id': channel_id,
                'adsets_queued': adsets_created
            }),
            'RoleArn': ROLE_ARN,
        }
    )
    print(f"Scheduler response: {response}")
    print(f"Scheduled event created at {datetime_now.strftime('%Y-%m-%d %H:%M:%S')} for {datetime_timer.strftime('%Y-%m-%d %H:%M:%S')}")

    # Send a summary of the results to the user in Slack
    timer_local = datetime_timer + datetime.timedelta(hours=7)
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':hand: {adsets_created} adsets have been queued for creation! :hand:')
    slack_post_message(channel_id, token, f':hourglass_flowing_sand: I\'ll get back to you at around {timer_local.strftime("%H:%M")} :hourglass_flowing_sand:')
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }