import json
import requests
import boto3

FB_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '🤖Rob_FB_Ads'

SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAds-successfulInvocation'

def lambda_handler(event, context):
    event_params    = json.loads(event['Records'][0]['body'])
    fb_access_token = event_params['fb_access_token']
    ad_account_id   = event_params['ad_account_id']
    adset_id        = event_params['adset_id']
    name            = event_params['name']
    page_id         = event_params['page_id']
    media_hash      = event_params['media_hash']
    message         = event_params['message']
    caption         = event_params['caption']
    description     = event_params['description']
    call_to_action  = event_params['call_to_action']
    link_url        = event_params['link_url']
    status          = event_params['status']
    spreadsheet_id  = event_params['spreadsheet_id']
    row_number      = event_params['row_number']
    gs_access_token = event_params['gs_access_token']

    # Prepare Ad Creative payload
    payload = {
        'access_token': fb_access_token,
        'name': name,
        'object_story_spec': {
            'page_id'  :page_id,
            'link_data': {
                'call_to_action': {
                    'type': call_to_action,
                    'value': {
                        'link': link_url
                    }
                },
                'image_hash': media_hash,
                'link': link_url,
                'name': caption,
                'message': message,
                'description': description
            }
        },
        'degrees_of_freedom_spec': {
            'creative_features_spec': {
                'standard_enhancements': {
                    'enroll_status': 'OPT_OUT'
                }
            }
        },
        'url_tags': 'utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{adset.name}}&utm_term={{ad.name}}'
    }

    sqs = boto3.client('sqs', region_name='ap-southeast-1')

    # Create Ad Creative
    ad_creatives_endpoint = f'{FB_ROOT_ENDPOINT}{ad_account_id}/adcreatives'
    ad_creatives_response = requests.post(ad_creatives_endpoint, json=payload)
    ad_creatives_response = ad_creatives_response.json()

    print(ad_creatives_response)
    creative_id = ad_creatives_response["id"]

    # Prepare Adcopy payload
    payload = {
        'access_token': fb_access_token,
        'name': name,
        'adset_id': adset_id,
        'creative': {
            'creative_id': creative_id,
        },
        'status': status,
    }

    # Create Adcopy
    ad_copies_endpoint = f'{FB_ROOT_ENDPOINT}{ad_account_id}/ads'
    ad_copies_response = requests.post(ad_copies_endpoint, json=payload)
    ad_copies_response = ad_copies_response.json()

    print(ad_copies_response)
    ad_id = ad_copies_response["id"]

    # Update the Google Sheets row with the ad and creative ID
    gs_update_endpoint = f"{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/{GOOGLE_SHEETS_SHEET_NAME}!B{row_number}?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
    gs_update_payload = {
        'range': f'{GOOGLE_SHEETS_SHEET_NAME}!B{row_number}',
        'values': [[ad_id, creative_id]]
    }
    gs_update_response = requests.put(gs_update_endpoint, json=gs_update_payload)
    print(gs_update_response.json())
    if gs_update_response.status_code != 200:
        return {
            "statusCode": gs_update_response.status_code,
        }
    
    # Send a success message to the SQS
    response = sqs.send_message(
        QueueUrl=SUCCESS_QUEUE_URL,
        MessageBody=json.dumps({
            'ad_id': ad_id,
            'creative_id': creative_id,
            'row_number': row_number
        })
    )
    print(f'Success message sent to SQS: {response}')

    return {
        'statusCode': 200
    }