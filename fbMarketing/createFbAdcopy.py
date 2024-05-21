import json
import os
import urllib.parse as urlparse
import urllib.request
import requests
import datetime

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

FB_ROOT_ENDPOINT = 'https://graph.facebook.com/v19.0/'

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
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    adset_id        = event['adset_id']
    name            = event['name']
    page_id         = event['page_id']
    media_hash      = event['media_hash']
    message         = event['message']
    caption         = event['caption']
    description     = event['description']
    call_to_action  = event['call_to_action']
    link_url        = event['link_url']
    status          = event['status']

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

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

    # Create Ad Creative
    ad_creatives_endpoint = f'{FB_ROOT_ENDPOINT}{ad_account_id}/adcreatives'
    ad_creatives_response = requests.post(ad_creatives_endpoint, data=payload)
    ad_creatives_response = ad_creatives_response.json()

    print(ad_creatives_response)

    # Prepare Adcopy payload
    payload = {
        'access_token': fb_access_token,
        'name': name,
        'adset_id': adset_id,
        'creative': {
            'creative_id': ad_creatives_response.id
        },
        'status': status,
    }

    # Create Adcopy
    ad_copies_endpoint = f'{FB_ROOT_ENDPOINT}{ad_account_id}/ads'
    ad_copies_response = requests.post(ad_copies_endpoint, data=payload)
    ad_copies_response = ad_copies_response.json()

    print(ad_copies_response)

    return {
        'statusCode': 200,
        'body': {
            'creative_id': ad_creatives_response.id,
            'ad_id':       ad_copies_response.id
        }
    }