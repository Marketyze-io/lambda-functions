import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

def lambda_handler(event, context):
    channel_id    = event['channelId']
    fbAccessToken = event['fbAccessToken']
    adAccountId   = event['adAccountId']
    gsAccessToken = event['gsAccessToken']
    spreadsheetId = event['spreadsheetId']

    campaignsCreated = 0

    # Get the data from Google Sheets
    gsCountEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'campaign-details\'!A1?access_token={gsAccessToken}'
    rowCount = requests.get(gsCountEndpoint).json()['values'][0][0]
    gsEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'campaign-details\'!A3:L{rowCount}?access_token={gsAccessToken}'
    data = requests.get(gsEndpoint).json()['values']

    # Create the campaigns in Facebook Ads Manager for rows without a campaign ID
    for row in data:
        if row[1] == "":
            campaign_name = row[0]
            campaign_objective = row[3]
            campaign_buying_type = row[4]
            campaign_status = row[5]
            special_ad_categories = row[11]

            if len(special_ad_categories) == 0:
                special_ad_categories = ["NONE"]

            payload = {
                'campaign_name': campaign_name,
                'campaign_objective': campaign_objective,
                'campaign_buying_type': campaign_buying_type,
                'campaign_status': campaign_status,
                'special_ad_categories': special_ad_categories,
                'access_token': fbAccessToken,
                'ad_account_id': adAccountId
            }

            # Call the createFbCampaign Lambda function
            url = f'https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/campaigns/single'
            response = requests.post(url, data=payload)
            response_data = response.json()
            campaign_id = response_data['id']

            # Update the Google Sheet with the campaign ID
            gsUpdateEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'campaign-details\'!B{data.index(row)+3}?access_token={gsAccessToken}'
            requests.put(gsUpdateEndpoint, data=json.dumps({'values': [[campaign_id]]}))
            campaignsCreated += 1

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)

    # Send a summary of the results to the user in Slack
    slackEndpoint = 'https://slack.com/api/chat.postMessage'
    slackPayload = {
        'channel': channel_id,
        'text': f'{campaignsCreated} campaigns created successfully!'
    }
    requests.post(slackEndpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slackPayload)

    return {
        'statusCode': 200
    }