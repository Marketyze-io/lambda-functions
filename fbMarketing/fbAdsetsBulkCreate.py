import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'
GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = 'adset-details'

def slack_post_message(channel_id, token, message):
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())

def lambda_handler(event, context):
    channel_id    = event['channel_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id = event['spreadsheet_id']

    adsets_created = 0
    gs_payload = {
        "valueInputOption": "USER_ENTERED",
        "data": []
    }
    error_flag = False
    
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
    slack_post_message(channel_id, token, ':rocket: Starting bulk adset creation! :rocket:')
    print("Ack sent to Slack")

    # Get the data from Google Sheets
    gs_count_endpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A1?access_token={gs_access_token}'
    response = requests.get(gs_count_endpoint)
    if response.status_code != 200:
        print(response.json())
    row_count = response.json()['values'][0][0]
    print(f"Number of rows in Google Sheets: {row_count}")
    row_num = str(int(row_count) + 2)
    gs_endpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!A3:P{row_num}?access_token={gs_access_token}'
    print("Getting data from Google Sheets")
    response = requests.get(gs_endpoint)
    if response.status_code != 200:
        print(response.json())
    data = response.json()['values']
    print("Data retrieved from Google Sheets")
    print(data)

    # Create the adsets for rows without an adset ID
    for row in data:
        if row[1] == "":
            adset_name = row[0]
            campaign_id = row[2]
            destination_type = row[3]
            optimization_goal = row[4]
            bid_strategy = row[5]
            bid_amount = row[6]
            billing_event = row[7]
            daily_budget = row[8]
            targeting = row[10]
            status = row[11]
            start_time = row[14]
            end_time = row[15]

            # temporary targeting as placeholder
            targeting = {
                "age_min": 21,
                "targeting_automation": {
                    "advantage_audience": 1
                },
                "flexible_spec": [
                    {
                        "behaviors": [{"id":6002714895372,"name":"All travelers"}],
                        "interests": [
                            {"id":6003107902433,"name":"Association football (Soccer)"},
                            {"id":6003139266461,"name":"Movies"}
                        ]
                    },
                    {
                        "interests": [{"id":6003020834693,"name":"Music"}],
                        "life_events": [{"id":6002714398172,"name":"Newlywed (1 year)"}]
                    },
                    {},
                    {}
                ],
                "geo_locations": {"countries":["TH"]}
            }

            payload = {
                'ad_account_id': ad_account_id,
                'access_token': fb_access_token,
                'adset_name': adset_name,
                'campaign_id': campaign_id,
                'destination_type': destination_type,
                'optimization_goal': optimization_goal,
                'bid_strategy': bid_strategy,
                'bid_amount': bid_amount,
                'billing_event': billing_event,
                'daily_budget': daily_budget,
                'targeting': json.dumps(targeting),
                'status': status,
                'start_time': start_time,
                'end_time': end_time
            }

            # Call the createFbAdset Lambda function
            url = f'https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/adsets/single'
            print("Creating adset in Facebook Ads Manager")
            print(f'Payload: {payload}')
            response = requests.post(url, data=payload)
            response_data = response.json()
            print(f'Response_data: {response_data}')

            if 'error' in response_data:
                print(f"Error creating adset: {response_data['error']['error_user_msg']}")
                slack_post_message(channel_id, token, f":warning: Whoops! There's been a problem with creating an adset! :warning:\n\nAdset Name: {adset_name}\nError: {response_data['error']['error_user_msg']}\n\nAll subsequent adsets will not be created. Please check the data in Google Sheets and try again.")
                error_flag = True
                break

            adset_id = response_data['id']
            print(f"Created adset with ID: {adset_id}")
            adsets_created += 1

            # Append the adset details to the list for updating Google Sheets
            request_data = {
                "range": f"'{GOOGLE_SHEETS_SHEET_NAME}'!B{data.index(row)+3}",
                "majorDimension": "ROWS",
                "values": [[adset_id]]
            }
            gs_payload['data'].append(request_data)

    # Update the Google Sheet with the campaign IDs
    gsUpdateEndpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values:batchUpdate?access_token={gs_access_token}'
    print("Updating Google Sheets with the adset IDs")
    requests.post(gsUpdateEndpoint, data=json.dumps(gs_payload))
    print("Google Sheets updated")

    # Send a summary of the results to the user in Slack
    print("Sending summary to Slack")
    slack_post_message(channel_id, token, f':tada: {adsets_created} adsets created successfully! :tada:')
    if error_flag:
        slack_post_message(channel_id, token, "But there was an error with one of the adsets. Please check the data in Google Sheets and try again.")
    print("Summary sent to Slack")

    return {
        'statusCode': 200
    }