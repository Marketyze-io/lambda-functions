import json
import os
import boto3
import requests
import shutil

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
TEMP_FILE_PATH = '/tmp/'
SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdmedia-successfulInvocation'

GOOGLE_DRIVE_ROOT_URL = 'https://www.googleapis.com/drive/v3/'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets'
CREATIVES_SHEET_NAME = '📝 FB Adcopies'
MEDIA_SHEET_NAME = '🤖Rob_FB_Media'
CREATIVES_NAME_COLUMN = 'H'

FACEBOOK_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

FILE_TYPES = {
    'png': 'IMAGE',
    'jpg': 'IMAGE',
    'jpeg': 'IMAGE',
    'gif': 'IMAGE',
    'mp4': 'VIDEO'
}

def download_from_google_drive(file_id, file_name, gs_access_token):
    headers = {
        'Authorization': f'Bearer {gs_access_token}'
    }
    gd_file_endpoint = f"{GOOGLE_DRIVE_ROOT_URL}files/{file_id}?alt=media"
    gd_file_response = requests.get(gd_file_endpoint, stream=True, headers=headers)
    if gd_file_response.status_code != 200:
        print(f"Error retrieving file: {gd_file_response.json()}")
        return {
            'statusCode': gd_file_response.status_code
        }
    with open(f'{TEMP_FILE_PATH}{file_name}', 'wb') as f:
        shutil.copyfileobj(gd_file_response.raw, f)
    print("File retrieved")

def upload_image_media(file_name, ad_account_id, fb_access_token):
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
    return media_hash

def upload_video_media(file_name, ad_account_id, fb_access_token):
    fb_media_headers = {
        'Authorization': f'Bearer {fb_access_token}'
    }
    fb_media_payload = {
        'filename': open(f'{TEMP_FILE_PATH}{file_name}', 'rb')
    }
    fb_ad_media_endpoint = f"{FACEBOOK_ROOT_ENDPOINT}{ad_account_id}/advideos"
    fb_media_request = requests.post(fb_ad_media_endpoint, headers=fb_media_headers, files=fb_media_payload)
    fb_media_response = fb_media_request.json()
    print(fb_media_response)
    video_id = fb_media_response['id']
    print(f"Video ID: {video_id}")
    return video_id

def update_adcopy_table(file_name, media_hash, spreadsheet_id, gs_access_token, row_number):
    media_hash_range = f"{CREATIVES_SHEET_NAME}!{CREATIVES_NAME_COLUMN}{row_number}"
    media_hash_update_headers = {
        'Authorization': f'Bearer {gs_access_token}'
    }
    media_hash_update_payload = {
        'range': media_hash_range,
        'values': [[file_name, media_hash]]
    }
    media_hash_update_endpoint = f"{GOOGLE_SHEETS_ROOT_URL}/{spreadsheet_id}/values/{media_hash_range}?valueInputOption=USER_ENTERED"
    media_hash_update_request = requests.put(media_hash_update_endpoint, headers=media_hash_update_headers, json=media_hash_update_payload)
    print(media_hash_update_request.status_code)
    print(media_hash_update_request.json())

def lambda_handler(event, context):
    event_params    = json.loads(event['Records'][0]['body'])
    file_id         = event_params['file_id']
    ad_account_id   = event_params['ad_account_id']
    fb_access_token = event_params['access_token']
    row_number      = event_params['row_number']
    spreadsheet_id  = event_params['spreadsheet_id']
    gs_access_token = event_params['gs_access_token']

    sqs = boto3.client('sqs', region_name='ap-southeast-1')

    # Get the file metadata
    gd_metadata_endpoint = f"{GOOGLE_DRIVE_ROOT_URL}files/{file_id}?fields=name,thumbnailLink&access_token={gs_access_token}"
    gd_metadata_response = requests.get(gd_metadata_endpoint)
    gd_metadata = gd_metadata_response.json()
    print(gd_metadata)
    file_name = gd_metadata['name']
    thumbnail_link = gd_metadata['thumbnailLink']
    print(f"File name: {file_name}")
    print(f"Thumbnail link: {thumbnail_link}")
    
    # Get the file extension
    file_extension = file_name.split('.')[-1]
    
    # Get the file
    download_from_google_drive(file_id, file_name, gs_access_token)

    # Upload the file to Facebook
    if FILE_TYPES[file_extension] == 'IMAGE':
        media_hash = upload_image_media(file_name, ad_account_id, fb_access_token)
    elif FILE_TYPES[file_extension] == 'VIDEO':
        media_hash = upload_video_media(file_name, ad_account_id, fb_access_token)
    else:
        print("Invalid file type")
        return {
            'statusCode': 400
        }

    # Update the media hash in the creatives sheet
    update_adcopy_table(file_name, media_hash, spreadsheet_id, gs_access_token, row_number)

    # Delete the temporary file
    os.remove(f'{TEMP_FILE_PATH}{file_name}')
    print("Temporary file deleted")

    # Send a success message to the SQS
    response = sqs.send_message(
        QueueUrl=SUCCESS_QUEUE_URL,
        MessageBody=json.dumps({
            'file_id': file_id,
            'row_number': row_number
        })
    )

    print(f'Success message sent to SQS: {response}')

    return {
        'statusCode': 200
    }