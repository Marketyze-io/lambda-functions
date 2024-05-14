import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

TEMPLATE_SPREADSHEET_ID = "1am9nNSWcUYpbvHFA8nk0GAvzedYvyBGTqNNT9YAX0wM"
TEMPLATE_SHEET_ID = "987478379"

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CAMPAIGNS_SHEET_NAME   = '🤖Rob_FB_Campaigns'
ADSETS_SHEET_NAME      = '🤖Rob_FB_Adsets'
ADCOPIES_SHEET_NAME    = '🤖Rob_FB_Adcopies'
AUDIENCES_SHEET_NAME   = '🤖Rob_FB_Audiences'
MEDIA_SHEET_NAME       = '🤖Rob_FB_Media'

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

    # Check if each worksheet already exists
    worksheet_names = [CAMPAIGNS_SHEET_NAME, ADSETS_SHEET_NAME, ADCOPIES_SHEET_NAME, AUDIENCES_SHEET_NAME, MEDIA_SHEET_NAME]
    for name in worksheet_names:
        gs_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + name}/values/campaign-details?access_token={gs_access_token}"
        gs_response = requests.get(gs_endpoint)
        if gs_response.status_code == 200:
            print(f"{name} sheet already exists")
        else:
            # Create the worksheet sheet
            payload = {
                "destinationSpreadsheetId": spreadsheet_id,
            }
            gs_copy_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + TEMPLATE_SPREADSHEET_ID}/sheets/{TEMPLATE_SHEET_ID}:copyTo?access_token={gs_access_token}"
            gs_response = requests.post(gs_copy_endpoint, json=payload)
            # Check for errors during sheet creation
            if gs_response.status_code != 200:
                print(gs_response.json())
                # Send a message to Slack
                slack_endpoint = 'https://slack.com/api/chat.postMessage'
                slack_payload = {
                    'channel': channel_id,
                    'text': f'Whoops! I couldn\'t duplicate one of the Rob worksheets. Please try again later :disappointed:'
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
                                "title": name
                            },
                            "fields": "title"
                        }
                    }
                ]
            }
            gs_rename_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
            gs_response = requests.post(gs_rename_endpoint, json=payload)

    return {
        'statusCode': 200
    }
