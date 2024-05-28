import json
import os
import boto3
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
SQS_QUEUE_URL = "https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbCampaignCreation.fifo"

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '🤖Rob_FB_Campaigns'

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
    fbAccessToken = event['fb_access_token']
    adAccountId   = event['ad_account_id']
    gsAccessToken = event['gs_access_token']
    spreadsheetId = event['spreadsheet_id']

    campaignsCreated = 0
    sqs = boto3.client('sqs', region_name='ap-southeast-1')
    
    # Get the token from AWS Parameter Store
    token = get_aws_secret(SECRET_NAME)

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_post_message(channel_id, token, ':rocket: Starting bulk campaign creation! :rocket:')
    print("Ack sent to Slack")

    # Get the data from Google Sheets
    gsCountEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A1?access_token={gsAccessToken}'
    response = requests.get(gsCountEndpoint)
    if response.status_code != 200:
        print(response.json())
    rowCount = response.json()['values'][0][0]
    print(f"Number of rows in Google Sheets: {rowCount}")
    rowNum = str(int(rowCount) + 2)
    gsEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A3:L{rowNum}?access_token={gsAccessToken}'
    print("Getting data from Google Sheets")
    response = requests.get(gsEndpoint)
    if response.status_code != 200:
        print(response.json())
    data = response.json()['values']
    print("Data retrieved from Google Sheets")
    print(data)

    # Create the campaigns in Facebook Ads Manager for rows without a campaign ID
    for row in data:
        if row[1] == "":
            campaign_name = row[0]
            campaign_objective = row[3]
            campaign_buying_type = row[4]
            campaign_status = row[5]
            special_ad_categories = row[11]
            if len(special_ad_categories) == 0:
                special_ad_categories = ["NONE"]

            payload = {
                'campaign_name': campaign_name,
                'campaign_objective': campaign_objective,
                'campaign_buying_type': campaign_buying_type,
                'campaign_status': campaign_status,
                'special_ad_categories': special_ad_categories,
                'access_token': fbAccessToken,
                'ad_account_id': adAccountId
            }

            # Send a message to the SQS queue
            print("Sending message to SQS")
            response = sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(payload),
                MessageGroupId=f'campaign-{campaign_name}'
            )
            print(f"Message sent to SQS: {response}")

            campaignsCreated += 1

    # Send a summary of the results to the user in Slack
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':hand: {campaignsCreated} campaigns have been queued for creation! :hand:')
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }