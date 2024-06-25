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
SQS_QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdmediaCarouselCreation.fifo"
LAMBDA_ARN = "arn:aws:lambda:ap-southeast-1:533267173231:function:fbAdmediaCarousel-checkStatus"
ROLE_ARN = "arn:aws:iam::533267173231:role/Scheduler_fbAdmedia-checkStatus"

GOOGLE_DRIVE_ROOT_URL = 'https://www.googleapis.com/drive/v3/'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets'
CAROUSELS_SHEET_NAME = '📝 FB Carousels'
MEDIA_SHEET_NAME = '🤖Rob_FB_Media'
CAROUSELS_TABLE_RANGE = 'A3:AB'

FACEBOOK_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'

FILE_TYPES = {
    'png': 'IMAGE',
    'jpg': 'IMAGE',
    'jpeg': 'IMAGE',
    'gif': 'IMAGE',
    'mp4': 'VIDEO'
}

TIMEOUT = 30
CONCURRENCY = 10

def slack_post_message(channel_id, token, message):
    """Send a message to a Slack channel"""
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())

def get_aws_secret(secret_name):
    """Get a secret from AWS Parameter Store"""
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
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']
    ad_account_name = event['ad_account_name']

    carousels_created = 0
    sqs = boto3.client('sqs', region_name='ap-southeast-1')
    scheduler = boto3.client('scheduler', region_name='ap-southeast-1')

    # Get the token from AWS Parameter Store
    token = get_aws_secret(SECRET_NAME)

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_post_message(channel_id, token, ':rocket: Starting carousel creation! :rocket:')
    print("Ack sent to Slack")

    # Get the column of google drive media links
    carousels_table_endpoint = f"{GOOGLE_SHEETS_ROOT_URL}/{spreadsheet_id}/values/{CAROUSELS_SHEET_NAME}!{CAROUSELS_TABLE_RANGE}?access_token={gs_access_token}"
    gs_response = requests.get(carousels_table_endpoint)
    print(gs_response.json())
    carousels_table = gs_response.json()['values']
    print("Carousels table retrieved from Google Sheets")
    print(carousels_table)

    # Create each carousel
    for carousel in carousels_table:
        # Skip if the creative ID already exists
        if carousel[26] != '':
            print(f"Creative ID already exists for {carousel[0]}, skipping...")
            continue

        # Skip if there is no carousel name
        if carousel[0] == '':
            print("Empty row, skipping...")
            continue

        name    = carousel[0]
        message = carousel[1]
        link    = carousel[2]
        caption = carousel[3]
        media   = carousel[15:25]
        page_id = carousel[25]

        child_attachments = []

        for item in media:
            if item == '':
                continue
            split_string = item.split(',')
            file_extension = split_string[0].split('.')[-1]
            if FILE_TYPES[file_extension] == 'IMAGE':
                item = {
                    'image_hash'    : split_string[1],
                    'name'          : split_string[2],
                    'description'   : split_string[3],
                    'call_to_action': {
                        'type': split_string[4].upper().replace(" ", "_")
                    },
                    'link'          : split_string[5]
                }
                child_attachments.append(item)
            elif FILE_TYPES[file_extension] == 'VIDEO':
                item = {
                    'video_id'     : split_string[1].split(';')[0],
                    'image_hash'   : split_string[1].split(';')[1],
                    'name'         : split_string[2],
                    'description'  : split_string[3],
                    'call_to_action': {
                        'type': split_string[4].upper().replace(" ", "_")
                    },
                    'link'         : split_string[5]
                }
                child_attachments.append(item)
            else:
                continue

        payload = {
            'fb_access_token': fb_access_token,
            'ad_account_id': ad_account_id,
            'gs_access_token': gs_access_token,
            'spreadsheet_id': spreadsheet_id,
            'row_number': carousels_table.index(carousel) + 3,
            'carousel_name': name,
            'page_id': page_id,
            'message': message,
            'link': link,
            'caption': caption,
            'child_attachments': child_attachments
        }

        # Get the row index of the adcopy
        carousel_row_index = carousels_table.index(carousel) + 3
        print(f"Carousel row index: {carousel_row_index}")

        # Send a message to the SQS queue
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(payload),
            MessageGroupId=f'carousel-{name.replace(" ", "_")}'
        )
        print(f'Carousel creation message sent to SQS: {response}')

        carousels_created += 1

    if carousels_created == 0:
        slack_post_message(channel_id, token, f':question: No carousels to create for {ad_account_name} :question:')
        return {
            'statusCode': 200
        }
    
    timer_seconds_full = math.ceil(carousels_created / CONCURRENCY) * TIMEOUT
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
    
    # Create a scheduled event to check the status of the carousels
    response = scheduler.create_schedule(
        ActionAfterCompletion='DELETE',
        Description='Check the status of the carousels created',
        FlexibleTimeWindow={
            'Mode': 'OFF'
        },
        Name='fbAdmedia-checkStatus',
        ScheduleExpression=f'at({datetime_timer.strftime("%Y-%m-%dT%H:%M:%S")})',
        Target={
            'Arn': LAMBDA_ARN,
            'Input': json.dumps({
                'channel_id': channel_id,
                'carousels_queued': carousels_created
            }),
            'RoleArn': ROLE_ARN,
        }
    )
    print(f"Scheduler response: {response}")
    print(f"Scheduled event created at {datetime_now.strftime('%Y-%m-%d %H:%M:%S')} for {datetime_timer.strftime('%Y-%m-%d %H:%M:%S')}")

    # Send a summary of the results to the user in Slack
    timer_local = datetime_timer + datetime.timedelta(hours=7)
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':hand: {carousels_created} carousels have been queued for creation! :hand:')
    slack_post_message(channel_id, token, f':hourglass_flowing_sand: I\'ll get back to you at around {timer_local.strftime("%H:%M")} :hourglass_flowing_sand:')
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }