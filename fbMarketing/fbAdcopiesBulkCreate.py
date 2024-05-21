import json
import os
import urllib.parse as urlparse
import urllib.request
import requests
import datetime

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
CREATE_ADCOPY_ENDPOINT = 'https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/adcopies/single'

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CAMPAIGNS_SHEET = {'name': '🤖Rob_FB_Campaigns'}
ADSETS_SHEET = {'name': '🤖Rob_FB_Adsets'}
ADCOPIES_SHEET = {'name': '🤖Rob_FB_Adcopies'}
AUDIENCES_SHEET = {'name': '🤖Rob_FB_Audiences'}
MEDIA_SHEET = {'name': '🤖Rob_FB_Media'}

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

    adcopies_created = 0
    error_flag = False

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_post_message(channel_id, token, ':rocket: Starting bulk adcopy creation! :rocket:')
    print("Ack sent to Slack")

    # Get creative data from Google Sheets
    gs_creatives_count_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!A1?access_token={gs_access_token}"
    gs_creatives_count_response = requests.get(gs_creatives_count_endpoint)
    gs_creatives_count = int(gs_creatives_count_response.json()['values'][0][0])
    if gs_creatives_count == 0:
        slack_post_message(channel_id, token, f':robot_face: No adcopies to create in {ad_account_name} :robot_face:')
        return {
            'statusCode': 200,
            'body': json.dumps('No adcopies to create')
        }
    
    gs_creatives_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!A3:O{2+gs_creatives_count}?access_token={gs_access_token}"
    gs_creatives_response = requests.get(gs_creatives_endpoint)
    gs_creatives = gs_creatives_response.json()['values']

    # Create Adcopies
    for creative in gs_creatives:
        # Skip if adcopy is already created
        if creative[13]:
            print(f"Adcopy already created for {creative[0]}")
            continue

        # Prepare Adcopy payload
        payload = {
            'fb_access_token': fb_access_token,
            'ad_account_id': ad_account_id,
            'adset_id': creative[2],
            'name': creative[0],
            'page_id': creative[14],
            'media_hash': creative[6],
            'message': creative[7],
            'caption': creative[8],
            'description': creative[9],
            'call_to_action': creative[11],
            'link_url': creative[12],
            'status': creative[4]
        }

        print(f"Creating adcopy for {creative[0]}")
        print(payload)

        # Create Adcopy
        adcopy_response = requests.post(CREATE_ADCOPY_ENDPOINT, json=payload)
        print(adcopy_response)
        adcopy_data = adcopy_response.json()
        print(adcopy_data)

        if adcopy_data['statusCode'] != 200:
                if 'error' in adcopy_data:
                    print(f"Error creating adcopy: {adcopy_data['error']}")
                    slack_post_message(channel_id, token, f":warning: Whoops! There's been a problem with creating an adcopy! :warning:\n\nAdcopy Name: {creative[0]}\nError: {adcopy_data['error']['error_user_msg']}\n\nAll subsequent adcopies will not be created. Please check the data in Google Sheets and try again.")
                elif 'message' in adcopy_data:
                    print(f"Error creating adcopy: {adcopy_data['message']}")
                    slack_post_message(channel_id, token, f":warning: Whoops! There's been a problem with creating an adcopy! :warning:\n\nAdset Name: {creative[0]}\nError: {adcopy_data['message']}\n\nAll subsequent adcopies will not be created. Please check the data in Google Sheets and try again.")
                else:
                    print(f"Error creating adcopy: {adcopy_data}")
                    slack_post_message(channel_id, token, f":warning: Whoops! There's been a problem with creating an adcopy! :warning:\n\nAdset Name: {creative[0]}\nError: {adcopy_data}\n\nAll subsequent adcopies will not be created. Please check the data in Google Sheets and try again.")
                error_flag = True
                break

        # Update IDs in Google Sheets
        creative_id = adcopy_data['body']['creative_id']
        adcopy_id = adcopy_data['body']['ad_id']
        creative_row_index = gs_creatives.index(creative) + 3
        print(f"Updating Google Sheets for creative {creative_id}")
        gs_update_ad_id_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!B{creative_row_index}?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
        gs_update_ad_id_payload = {
            'range': f"{ADCOPIES_SHEET['name']}!B{creative_row_index}",
            'values': [[adcopy_id]]
        }
        gs_update_ad_id_response = requests.put(gs_update_ad_id_endpoint, json=gs_update_ad_id_payload)
        print(gs_update_ad_id_response.json())
        gs_update_creative_id_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!N{creative_row_index}?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
        gs_update_creative_id_payload = {
            'range': f"{ADCOPIES_SHEET['name']}!N{creative_row_index}",
            'values': [[creative_id]]
        }
        gs_update_creative_id_response = requests.put(gs_update_creative_id_endpoint, json=gs_update_creative_id_payload)
        print(gs_update_creative_id_response.json())

        adcopies_created += 1

    # Send a summary of the results to the user in Slack
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':tada: {adcopies_created} adcopies created successfully! :tada:')
    if error_flag:
        slack_post_message(channel_id, token, "But there was an error with one of the adcopies. Please check the data in Google Sheets and try again.")
    print("Summary sent to Slack")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }