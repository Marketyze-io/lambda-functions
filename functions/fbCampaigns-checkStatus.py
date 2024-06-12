import json
import os
import boto3
import requests
import urllib.parse as urlparse
import urllib.request

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbCampaigns-successfulInvocation'

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'

def slack_post_message(channel_id, token, message):
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())

def get_aws_secret(secret_name):
    secret_name = urlparse.quote(secret_name, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")
    return token

def lambda_handler(event, context):
    print(event)
    channel_id       = event['channel_id']
    campaigns_queued = int(event['campaigns_queued'])

    # Get the token from AWS Parameter Store
    token = get_aws_secret(SECRET_NAME)

    sqs = boto3.client('sqs', region_name='ap-southeast-1')

    # Get the number of messages in the queue
    queue_attributes = sqs.get_queue_attributes(
        QueueUrl=SUCCESS_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    message_count = int(queue_attributes['Attributes']['ApproximateNumberOfMessages'])

    # Send the message to Slack
    slack_post_message(channel_id, token, f':tada: {message_count} campaigns created! :tada:')
    if campaigns_queued > message_count:
        slack_post_message(channel_id, token, f':warning: There are {campaigns_queued - message_count} campaigns that have not been created! :warning:')

    # Purge the queue
    sqs.purge_queue(QueueUrl=SUCCESS_QUEUE_URL)

    return {
        'statusCode': 200
    }
