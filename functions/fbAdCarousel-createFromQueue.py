import json
import requests
import boto3

FB_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '📝 FB Carousels'
CAROUSEL_ID_COLUMN = 'Y'

SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdmediaCarousel-successfulInvocation'

URL_TAGS = 'utm_source=facebook&utm_medium=paid&utm_campaign={{campaign.name}}&utm_content={{adset.name}}&utm_term={{ad.name}}'

def create_carousel_creative(name, page_id, message, link, caption, child_attachments, ad_account_id, fb_access_token):
    fb_headers = {
        'Authorization': f'Bearer {fb_access_token}'
    }
    # Prepare Carousel Creative payload
    payload = {
        'name': name,
        'object_story_spec': {
            'page_id'  :page_id,
            'link_data': {
                'message': message,
                'link': link,
                'caption': caption,
                'child_attachments': child_attachments
                
            }
        },
        'degrees_of_freedom_spec': {
            'creative_features_spec': {
                'standard_enhancements': {
                    'enroll_status': 'OPT_OUT'
                }
            }
        },
        'url_tags': URL_TAGS
    }

    # Create Carousel Creative
    ad_creatives_endpoint = f'{FB_ROOT_ENDPOINT}/{ad_account_id}/adcreatives'
    ad_creatives_response = requests.post(ad_creatives_endpoint, json=payload)
    ad_creatives_response = ad_creatives_response.json()

    print(ad_creatives_response)
    creative_id = ad_creatives_response["id"]
    return creative_id

def lambda_handler(event, context):
    event_params      = json.loads(event['Records'][0]['body'])
    fb_access_token   = event_params['fb_access_token']
    ad_account_id     = event_params['ad_account_id']
    gs_access_token   = event_params['gs_access_token']
    spreadsheet_id    = event_params['spreadsheet_id']
    row_number        = event_params['row_number']
    carousel_name     = event_params['carousel_name']
    page_id           = event_params['page_id']
    message           = event_params['message']
    link              = event_params['link']
    caption           = event_params['caption']
    child_attachments = event_params['child_attachments']

    sqs = boto3.client('sqs', region_name='ap-southeast-1')

    carousel_creative_id = create_carousel_creative(
        name=carousel_name,
        page_id=page_id,
        message=message,
        link=link,
        caption=caption,
        child_attachments=child_attachments,
        ad_account_id=ad_account_id,
        fb_access_token=fb_access_token
    ) 

    # Update the Google Sheets row with the creative ID
    gs_update_endpoint = f"{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/{GOOGLE_SHEETS_SHEET_NAME}!{CAROUSEL_ID_COLUMN}{row_number}?valueInputOption=USER_ENTERED&access_token={gs_access_token}"
    gs_update_payload = {
        'range': f'{GOOGLE_SHEETS_SHEET_NAME}!{CAROUSEL_ID_COLUMN}{row_number}',
        'values': [[carousel_creative_id]]
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
            'creative_id': carousel_creative_id,
            'row_number': row_number
        })
    )
    print(f'Success message sent to SQS: {response}')

    return {
        'statusCode': 200
    }