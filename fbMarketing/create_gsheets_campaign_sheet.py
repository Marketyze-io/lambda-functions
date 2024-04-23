import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

TEMPLATE_SPREADSHEET_ID = "1am9nNSWcUYpbvHFA8nk0GAvzedYvyBGTqNNT9YAX0wM"

def lambda_handler(event, context):
    channel_id      = event['channel_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

    # Check if a campaign-details sheet already exists
    gs_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/campaign-details?access_token={gs_access_token}"
    gs_response = requests.get(gs_endpoint)
    if gs_response.status_code == 200:
        return {
            'statusCode': 200,
            'body': json.dumps('Sheet already exists')
        }
    else:
        # Send a message to Slack
        slack_endpoint = 'https://slack.com/api/chat.postMessage'
        slack_payload = {
            'channel': channel_id,
            'text': f'Looks like the target spreadsheet doesn\'t have a Campaign Details sheet yet. I\'ll fix that for you! :wink:'
        }
        slack_request = requests.post(slack_endpoint, headers
            ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
        print(slack_request.json())
        print("Ack sent to Slack")
    
    # Create the campaign-details sheet
    payload = {
        "destinationSpreadsheetId": spreadsheet_id,
    }
    gs_copy_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{TEMPLATE_SPREADSHEET_ID}/sheets/campaign-details:copyTo?access_token={gs_access_token}"
    gs_response = requests.post(gs_copy_endpoint, json=payload)
    if gs_response.status_code != 200:
        # Send a message to Slack
        slack_endpoint = 'https://slack.com/api/chat.postMessage'
        slack_payload = {
            'channel': channel_id,
            'text': f'Whoops! I couldn\'t create the Campaign Details sheet. Please try again later :disappointed:'
        }
        slack_request = requests.post(slack_endpoint, headers
            ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
        print(slack_request.json())
        print("Error msg sent to Slack")
        return {
            'statusCode': 500,
            'body': json.dumps('Error creating sheet')
        }
    
    # Rename the sheet
    sheet_id = gs_response.json()['sheetId']
    payload = {
        "requests": [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "title": "campaign-details"
                    },
                    "fields": "title"
                }
            }
        ]
    }
    gs_rename_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
    gs_response = requests.post(gs_rename_endpoint, json=payload)

    # Send a message to Slack
    slack_endpoint = 'https://slack.com/api/chat.postMessage'
    slack_payload = {
        'channel': channel_id,
        'text': f'Campaign Details sheet created successfully! :tada:'
    }
    slack_request = requests.post(slack_endpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())
    print("Success msg sent to Slack")
    return {
        'statusCode': 200,
        'body': json.dumps('Sheet created successfully')
    }
