import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

def lambda_handler(event, context):
    channel_id    = event['channel_id']
    fbAccessToken = event['fb_access_token']
    adAccountId   = event['ad_account_id']
    gsAccessToken = event['gs_access_token']
    spreadsheetId = event['spreadsheet_id']

    campaignsCreated = 0
    campaignDetails = {
        "valueInputOption": "USER_ENTERED",
        "data": []
    }
    
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
    slackEndpoint = 'https://slack.com/api/chat.postMessage'
    slackPayload = {
        'channel': channel_id,
        'text': f'Starting bulk campaign creation!'
    }
    slackRequest = requests.post(slackEndpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slackPayload)
    print(slackRequest.json())
    print("Ack sent to Slack")

    # Get the data from Google Sheets
    gsCountEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'campaign-details\'!A1?access_token={gsAccessToken}'
    response = requests.get(gsCountEndpoint)
    if response.status_code != 200:
        print(response.json())
    rowCount = response.json()['values'][0][0]
    print(f"Number of rows in Google Sheets: {rowCount}")
    rowNum = str(int(rowCount) + 2)
    gsEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/\'campaign-details\'!A3:L{rowNum}?access_token={gsAccessToken}'
    print("Getting data from Google Sheets")
    response = requests.get(gsEndpoint)
    if response.status_code != 200:
        print(response.json())
    data = response.json()['values']
    print("Data retrieved from Google Sheets")
    print(data)

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
            print("Creating campaign in Facebook Ads Manager")
            print(f'Payload: {payload}')
            response = requests.post(url, data=payload)
            response_data = response.json()
            print(f'Response_data: {response_data}')
            campaign_id = response_data['id']
            print(f"Created campaign with ID: {campaign_id}")
            campaignsCreated += 1

            # Append the campaign details to the list for updating Google Sheets
            requestData = {
                "range": f"'campaign-details'!B{data.index(row)+3}",
                "majorDimension": "ROWS",
                "values": [[campaign_id]]
            }
            campaignDetails['data'].append(requestData)

    # Update the Google Sheet with the campaign IDs
    gsUpdateEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values:batchUpdate?access_token={gsAccessToken}'
    print("Updating Google Sheets with the campaign IDs")
    requests.post(gsUpdateEndpoint, data=json.dumps(campaignDetails))
    print("Google Sheets updated")

    # Send a summary of the results to the user in Slack
    print("Sending summary to Slack")
    slackEndpoint = 'https://slack.com/api/chat.postMessage'
    slackPayload = {
        'channel': channel_id,
        'text': f'{campaignsCreated} campaigns created successfully!'
    }
    slackRequest = requests.post(slackEndpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slackPayload)
    print(slackRequest.json())
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }