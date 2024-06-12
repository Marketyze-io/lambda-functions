import json
import os
import urllib.parse as urlparse
import urllib.request
import requests
import datetime

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
UPDATE_SAVED_AUDIENCES_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/audiences/update"
UPDATE_PAGES_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/pages/update"
UPDATE_ADSPIXELS_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/adspixels/update"

MASTER_SHEET_ID = "1am9nNSWcUYpbvHFA8nk0GAvzedYvyBGTqNNT9YAX0wM"
MASTER_WORSKSHEET_NAME = "spreadsheet-master-list"

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CAMPAIGNS_SHEET = {'name': '🤖Rob_FB_Campaigns', 'id': '987478379'}
ADSETS_SHEET = {'name': '🤖Rob_FB_Adsets', 'id': '655550453'}
ADS_SHEET = {'name': '🤖Rob_FB_Ads', 'id': '224614968'}
AUDIENCES_SHEET = {'name': '🤖Rob_FB_Audiences', 'id': '862287605'}
MEDIA_SHEET = {'name': '🤖Rob_FB_Media', 'id': '1547157615'}
PAGES_SHEET = {'name': '🤖Rob_FB_Pages', 'id': '1337036354'}

TARGETING_SPEC_FORMULA_CELL = "N3"
CREATIVE_HASH_FORMULA_CELL = "N3"
XLOOKUP_FORMULA_CELL = "J3"
FORMATTED_CTA_FORMULA_CELL = "O3"
PAGE_ID_FORMULA_CELL = "P3"

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
    ad_account_name = event['ad_account_name']

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
    new_sheet_ids = {}
    master_sheet_ids = {
        CAMPAIGNS_SHEET['name']: CAMPAIGNS_SHEET['id'],
        ADSETS_SHEET['name']: ADSETS_SHEET['id'],
        ADS_SHEET['name']: ADS_SHEET['id'],
        AUDIENCES_SHEET['name']: AUDIENCES_SHEET['id'],
        MEDIA_SHEET['name']: MEDIA_SHEET['id'],
        PAGES_SHEET['name']: PAGES_SHEET['id']
    }
    gs_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}?access_token={gs_access_token}"
    gs_response = requests.get(gs_endpoint)
    gs_sheets = gs_response.json()['sheets']

    # Payload for fixing the broken references
    refs_payload = {
        "requests": []
    }

    # Check if the sheet already exists, then remove it from the master list
    for sheet in gs_sheets:
        sheet_name = sheet['properties']['title']
        sheet_id = sheet['properties']['sheetId']
        if sheet_name in master_sheet_ids:
            print(f"{sheet_name} sheet already exists")
            new_sheet_ids[sheet_name] = sheet_id
            del master_sheet_ids[sheet_name]
        
    # Create the worksheets that don't exist
    for sheet_name in master_sheet_ids:
        sheet_id = master_sheet_ids[sheet_name]
        # Create the worksheet
        payload = {
            "destinationSpreadsheetId": spreadsheet_id,
        }
        gs_copy_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + MASTER_SHEET_ID}/sheets/{sheet_id}:copyTo?access_token={gs_access_token}"
        gs_response = requests.post(gs_copy_endpoint, json=payload)
        # Check for errors during sheet creation
        if gs_response.status_code != 200:
            print(gs_response.json())
            slack_post_message(channel_id, token, 'Whoops! I couldn\'t duplicate one of the Rob worksheets. Please try again later :disappointed:')
            print("Error msg sent to Slack")
            return {
                'statusCode': 500,
                'body': json.dumps('Error creating sheet')
            }
        # Rename the sheet
        new_sheet_id = gs_response.json()['sheetId']
        payload = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": new_sheet_id,
                            "title": sheet_name
                        },
                        "fields": "title"
                    }
                }
            ]
        }
        gs_rename_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
        gs_response = requests.post(gs_rename_endpoint, json=payload)
        new_sheet_ids[sheet_name] = new_sheet_id

    print(new_sheet_ids)

    # Update the saved audiences sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_SAVED_AUDIENCES_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, 'Whoops! I couldn\'t update the saved audiences. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    # Update the pages sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_PAGES_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, 'Whoops! I couldn\'t update the pages. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    # Update the adspixels sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_ADSPIXELS_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, 'Whoops! I couldn\'t update the adspixels. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    # Add spreadsheet id to the master-list
    gs_append_endpoint = GOOGLE_SHEETS_ROOT_URL + MASTER_SHEET_ID + f"/values/'{MASTER_WORSKSHEET_NAME}'!A3:append?access_token={gs_access_token}&valueInputOption=USER_ENTERED"
    datetime_now = datetime.datetime.now() + datetime.timedelta(hours=7)
    gs_append_body = {
        "range": "'spreadsheet-master-list'!A3",
        "majorDimension": "ROWS",
        "values": [[
          ad_account_name,
          ad_account_id,
          spreadsheet_id,
          datetime_now.strftime("%Y-%m-%d %H:%M:%S"),
        ]],
      }
    gs_append_response = requests.post(gs_append_endpoint, json=gs_append_body)

      # Handle the error if the gs_append endpoint was not called successfully
    if gs_append_response.status_code != 200:
        slack_post_message(channel_id, token, 'Whoops! I couldn\'t update the master list. Please contact one of the app maintainers. :disappointed:')
        print("Error msg sent to Slack")
    else:
        slack_post_message(channel_id, token, f":tada: {spreadsheet_name} is now ready for use! :tada:\nFeel free to start working on the spreadsheet again :smile:")

    return {
        'statusCode': 200
    }
