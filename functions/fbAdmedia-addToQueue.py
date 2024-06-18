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
SQS_ADMEDIA_QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdmediaCreation.fifo"
SQS_ADCAROUSEL_QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdmediaCarouselCreation.fifo"
LAMBDA_ARN = "arn:aws:lambda:ap-southeast-1:533267173231:function:fbAdmedia-checkStatus"
ROLE_ARN = "arn:aws:iam::533267173231:role/Scheduler_fbAdmedia-checkStatus"

GOOGLE_DRIVE_ROOT_URL = 'https://www.googleapis.com/drive/v3/'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets'
CREATIVES_SHEET_NAME = '📝 FB Adcopies'
MEDIA_SHEET_NAME = '🤖Rob_FB_Media'
ADCOPIES_TABLE_RANGE = 'A2:M'

FACEBOOK_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'

TIMEOUT = 30
CONCURRENCY = 10

def get_dict_index(array, key, value):
    for i in range(len(array)):
        if array[i][key] == value:
            return i
    return -1

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
    channel_id      = event['channel_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    ad_account_name = event['ad_account_name']

    admedia_created = 0
    sqs = boto3.client('sqs', region_name='ap-southeast-1')
    scheduler = boto3.client('scheduler', region_name='ap-southeast-1')

    # Get the token from AWS Parameter Store
    token = get_aws_secret(SECRET_NAME)

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_post_message(channel_id, token, ':rocket: Starting bulk admedia upload! :rocket:')
    slack_post_message(channel_id, token, f':robot_face: I\'m now uploading media to {ad_account_name} :robot_face:\nPlease don\'t do anything to the spreadsheet\nThis will take a few seconds...')
    print("Ack sent to Slack")

    # Get the column of google drive media links
    adcopies_table_endpoint = f"{GOOGLE_SHEETS_ROOT_URL}/{spreadsheet_id}/values/{CREATIVES_SHEET_NAME}!{ADCOPIES_TABLE_RANGE}?access_token={gs_access_token}"
    gs_response = requests.get(adcopies_table_endpoint)
    print(gs_response.json())
    adcopies_table = gs_response.json()['values']
    print("Adcopies table retrieved from Google Sheets")
    print(adcopies_table)

    carousels = [
        {
            'id': 'carousel1',
            'media': []
        }
    ]

    # Upload each piece of media to Facebook
    for adcopy in adcopies_table[1:]:
        # Check if there is already a creative id
        if adcopy[9] != '':
            print(f"Media hash already exists for {adcopy[1]}, skipping...")
            continue

        carousel        = adcopy[0]
        media_link      = adcopy[1]
        caption         = adcopy[2]
        headline        = adcopy[3]
        description     = adcopy[4]
        call_to_action  = adcopy[5].upper().replace(" ", "_")
        link_url        = adcopy[7]
        page_id         = adcopy[11]

        # Extract the file id from the URL
        file_id = media_link.split('/')[-2]

        # Get the row index of the adcopy
        media_row_index = adcopies_table.index(adcopy) + 3
        print(f"Media row index: {media_row_index}")

        if carousel != '':
            index = get_dict_index(carousels, 'id', carousel)
            # Create a new carousel if it doesn't exist
            if index == -1:
                carousels.append({
                    'id': carousel,
                    'media': []
                })
                index = len(carousels) - 1
            # Append the media to the carousel
            carousels[index]['media'].append({
                'file_id': file_id,
                'page_id': page_id,
                'link_url': link_url,
                'caption': caption,
                'headline': headline,
                'description': description,
                'call_to_action': call_to_action
            })
            continue

        payload = {
            'ad_account_id': ad_account_id,
            'access_token': fb_access_token,
            'spreadsheet_id': spreadsheet_id,
            'gs_access_token': gs_access_token,            
            'row_number': media_row_index,
            'carousel': carousel,
            'file_id': file_id,
            'page_id': page_id,
            'link_url': link_url,
            'caption': caption,
            'headline': headline,
            'description': description,
            'call_to_action': call_to_action
        }

        # Send a message to the SQS queue
        response = sqs.send_message(
            QueueUrl=SQS_ADMEDIA_QUEUE_URL,
            MessageBody=json.dumps(payload),
            MessageGroupId=f'admedia-{file_id}'
        )
        print(f'Media upload message sent to SQS: {response}')

        admedia_created += 1

    for carousel in carousels:
        if len(carousel['media']) == 0:
            continue

        payload = {
            'ad_account_id': ad_account_id,
            'access_token': fb_access_token,
            'spreadsheet_id': spreadsheet_id,
            'gs_access_token': gs_access_token,
            'carousel': carousel
        }

        # Send a message to the SQS queue
        response = sqs.send_message(
            QueueUrl=SQS_ADCAROUSEL_QUEUE_URL,
            MessageBody=json.dumps(payload),
            MessageGroupId=f'admedia-{carousel["id"]}'
        )
        print(f'Media upload message sent to SQS: {response}')

        admedia_created += 1

    if admedia_created == 0:
        slack_post_message(channel_id, token, f':question: No new media to upload for {ad_account_name} :question:')
        return {
            'statusCode': 200
        }
    
    timer_seconds_full = math.ceil(admedia_created / CONCURRENCY) * TIMEOUT
    timer_seconds = timer_seconds_full % 60
    timer_minutes = timer_seconds_full // 60

    # Get the current time in UTC
    datetime_now = datetime.datetime.now()
    # Get the seconds to the next minute
    seconds_to_next_minute = 60 - datetime_now.second
    if seconds_to_next_minute < timer_seconds:
        datetime_timer = datetime_now + datetime.timedelta(minutes=timer_minutes+2) - datetime.timedelta(seconds=datetime_now.second)
    else:
        datetime_timer = datetime_now + datetime.timedelta(minutes=timer_minutes+1) - datetime.timedelta(seconds=datetime_now.second)
    
    # Create a scheduled event to check the status of the admedia
    response = scheduler.create_schedule(
        ActionAfterCompletion='DELETE',
        Description='Check the status of the admedia created',
        FlexibleTimeWindow={
            'Mode': 'OFF'
        },
        Name='fbAdmedia-checkStatus',
        ScheduleExpression=f'at({datetime_timer.strftime("%Y-%m-%dT%H:%M:%S")})',
        Target={
            'Arn': LAMBDA_ARN,
            'Input': json.dumps({
                'channel_id': channel_id,
                'admedia_queued': admedia_created
            }),
            'RoleArn': ROLE_ARN,
        }
    )
    print(f"Scheduler response: {response}")
    print(f"Scheduled event created at {datetime_now.strftime('%Y-%m-%d %H:%M:%S')} for {datetime_timer.strftime('%Y-%m-%d %H:%M:%S')}")

    # Send a summary of the results to the user in Slack
    timer_local = datetime_timer + datetime.timedelta(hours=7)
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':hand: {admedia_created} pieces of admedia have been queued for creation! :hand:')
    slack_post_message(channel_id, token, f':hourglass_flowing_sand: I\'ll get back to you at around {timer_local.strftime("%H:%M")} :hourglass_flowing_sand:')
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }