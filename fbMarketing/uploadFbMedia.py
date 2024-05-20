import json
import os
import urllib.parse as urlparse
import urllib.request
import requests
import datetime
import shutil

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
TEMP_FILE_PATH = '/tmp/'

GOOGLE_DRIVE_ROOT_URL = 'https://www.googleapis.com/drive/v3/'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CREATIVES_SHEET_NAME = '📝 FB Adcopies'
MEDIA_SHEET_NAME = '🤖Rob_FB_Media'

FACEBOOK_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

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

    # Get the column of google drive media links
    media_links_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{CREATIVES_SHEET_NAME}!A3:B?access_token={gs_access_token}"
    gs_response = requests.get(media_links_endpoint)
    print(gs_response.json())
    media_links = gs_response.json()['values']

    print(media_links)

    slack_post_message(channel_id, token, f':robot_face: I\'m now uploading media to {ad_account_name} :robot_face:\nPlease don\'t do anything to the spreadsheet\nThis will take a few seconds...')

    # Upload each piece of media to Facebook
    for link in media_links:
        media_hash = link[0]
        media_link = link[1]

        # Check if there is already a media hash
        if media_hash:
            print(f"Media hash already exists for {media_link}")
            continue

        # Extract the file id from the URL
        file_id = media_link.split('/')[-2]
        print(f"Uploading media for {file_id}")

        # Get the row index of the media link
        media_row_index = media_links.index(['', media_link]) + 3
        print(f"Media row index: {media_row_index}")

        # Get the file metadata
        gd_metadata_endpoint = f"{GOOGLE_DRIVE_ROOT_URL}files/{file_id}?fields=name,thumbnailLink&access_token={gs_access_token}"
        gd_metadata_response = requests.get(gd_metadata_endpoint)
        gd_metadata = gd_metadata_response.json()
        print(gd_metadata)
        file_name = gd_metadata['name']
        thumbnail_link = gd_metadata['thumbnailLink']
        print(f"File name: {file_name}")
        print(f"Thumbnail link: {thumbnail_link}")

        # Get the file
        headers = {
            'Authorization': f'Bearer {gs_access_token}'
        }
        gd_file_endpoint = f"{GOOGLE_DRIVE_ROOT_URL}files/{file_id}?alt=media"
        gd_file_response = requests.get(gd_file_endpoint, stream=True, headers=headers)
        if gd_file_response.status_code != 200:
            print(f"Error retrieving file: {gd_file_response.json()}")
            continue
        with open(f'{TEMP_FILE_PATH}{file_name}', 'wb') as f:
            shutil.copyfileobj(gd_file_response.raw, f)
        print(f"File retrieved")

        # Upload the file to Facebook
        fb_media_headers = {
            'Authorization': f'Bearer {fb_access_token}'
        }
        fb_media_payload = {
            'filename': open(f'{TEMP_FILE_PATH}{file_name}', 'rb')
        }
        fb_ad_media_endpoint = f"{FACEBOOK_ROOT_ENDPOINT}{ad_account_id}/adimages"
        fb_media_request = requests.post(fb_ad_media_endpoint, headers=fb_media_headers, files=fb_media_payload)
        fb_media_response = fb_media_request.json()
        print(fb_media_response)
        media_hash = fb_media_response['images'][file_name]['hash']
        print(f"Media hash: {media_hash}")

        # Update the spreadsheet with the media thumbnail, name and hash
        media_thumbnail = f'=IMAGE("{thumbnail_link}")'
        media_update_payload = {
            'values': [[media_thumbnail, file_name, media_hash]]
        }
        media_update_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{MEDIA_SHEET_NAME}!A3:C3:append?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
        media_update_request = requests.post(media_update_endpoint, json=media_update_payload)
        print(media_update_request.json())

        # Update the media hash in the adcopies sheet
        media_hash_range = f"{CREATIVES_SHEET_NAME}!A{media_row_index}"
        media_hash_update_payload = {
            'range': media_hash_range,
            'values': [[media_hash]]
        }
        media_hash_update_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{media_hash_range}?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
        media_hash_update_request = requests.put(media_hash_update_endpoint, json=media_hash_update_payload)
        print(media_hash_update_request.status_code)
        print(media_hash_update_request.json())

    return {
        'statusCode': 200
    }