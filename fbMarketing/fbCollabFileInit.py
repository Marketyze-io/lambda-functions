import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
UPDATE_SAVED_AUDIENCES_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/audiences/update"

TEMPLATE_SPREADSHEET_ID = "1am9nNSWcUYpbvHFA8nk0GAvzedYvyBGTqNNT9YAX0wM"

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CAMPAIGNS_SHEET = {
    'name': '🤖Rob_FB_Campaigns',
    'id'  : '987478379'}
ADSETS_SHEET = {
    'name': '🤖Rob_FB_Adsets',
    'id': '655550453'}
ADCOPIES_SHEET = {
    'name': '🤖Rob_FB_Adcopies',
    'id': '224614968'}
AUDIENCES_SHEET = {
    'name': '🤖Rob_FB_Audiences',
    'id': '862287605'}
MEDIA_SHEET = {
    'name': '🤖Rob_FB_Media',
    'id': '1547157615'}

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'

def slack_post_message(channel_id, token, message):
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())


def lambda_handler(event, context):
    channel_id      = event['channel_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

    # Get spreadsheet name
    gs_name_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}?access_token={gs_access_token}"
    gs_response = requests.get(gs_name_endpoint)
    spreadsheet_name = gs_response.json()['properties']['title']

    slack_post_message(channel_id, token, f':robot_face: I\'m now initialising {spreadsheet_name} :robot_face:\nPlease don\'t do anything to the spreadsheet\nThis will take a few seconds...')

    # Check if each worksheet already exists
    worksheet_names = [CAMPAIGNS_SHEET, ADSETS_SHEET, ADCOPIES_SHEET, AUDIENCES_SHEET, MEDIA_SHEET]
    for sheet in worksheet_names:
        gs_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{sheet['name']}?access_token={gs_access_token}"
        gs_response = requests.get(gs_endpoint)
        if gs_response.status_code == 200:
            print(f"{sheet} sheet already exists")
        else:
            # Create the worksheet sheet
            payload = {
                "destinationSpreadsheetId": spreadsheet_id,
            }
            gs_copy_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + TEMPLATE_SPREADSHEET_ID}/sheets/{sheet['id']}:copyTo?access_token={gs_access_token}"
            gs_response = requests.post(gs_copy_endpoint, json=payload)
            # Check for errors during sheet creation
            if gs_response.status_code != 200:
                print(gs_response.json())
                slack_post_message(channel_id, token, f'Whoops! I couldn\'t duplicate one of the Rob worksheets. Please try again later :disappointed:')
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
                                "title": sheet['name']
                            },
                            "fields": "title"
                        }
                    }
                ]
            }
            gs_rename_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
            gs_response = requests.post(gs_rename_endpoint, json=payload)

    # Update the saved audiences sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_SAVED_AUDIENCES_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, f'Whoops! I couldn\'t update the saved audiences. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    slack_post_message(channel_id, token, f":tada: {spreadsheet_name} is now ready for use! :tada:\nFeel free to start working on the spreadsheet again :smile:")

    return {
        'statusCode': 200
    }
