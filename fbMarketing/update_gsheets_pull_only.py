import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

def lambda_handler(event, context):
    channel_id      = event['channel_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']

    campaigns_updated_count = 0

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_endpoint = 'https://slack.com/api/chat.postMessage'
    slack_payload = {
        'channel': channel_id,
        'text': f'Pulling Facebook campaign data!'
    }
    slack_request = requests.post(slack_endpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())
    print("Ack sent to Slack")

    # Get the campaigns from Facebook
    print("Getting campaigns from Facebook")
    fb_endpoint = f'https://graph.facebook.com/v19.0/{ad_account_id}/campaigns?fields=["id", "name", "objective", "buying_type", "status", "special_ad_categories"]&access_token={fb_access_token}'
    fb_request = requests.get(fb_endpoint)
    fb_campaigns = fb_request.json()['data']
    print("Campaigns retrieved from Facebook")
    print(fb_campaigns)

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }