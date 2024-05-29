import json
import requests
import boto3

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '🤖Rob_FB_Adsets'

SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbAdsets-successfulInvocation'

def lambda_handler(event, context):
    event_params          = json.loads(event['Records'][0]['body'])
    start_time = None
    end_time   = None
    ad_account_id      = event_params['ad_account_id']
    access_token       = event_params['access_token']
    adset_name         = event_params['adset_name']
    campaign_id        = event_params['campaign_id']
    destination_type   = event_params['destination_type']
    optimization_goal  = event_params['optimization_goal']
    bid_strategy       = event_params['bid_strategy']
    bid_amount         = event_params['bid_amount']
    billing_event      = event_params['billing_event']
    daily_budget       = event_params['daily_budget']
    targeting          = event_params['targeting']
    status             = event_params['status']
    spreadsheet_id     = event_params['spreadsheet_id']
    row_number         = event_params['row_number']
    gs_access_token    = event_params['gs_access_token']
    if 'start_time' in event_params:
        start_time     = event_params['start_time']
    if 'end_time' in event_params:
        end_time       = event_params['end_time']

    form_data = {
        'name'                 : adset_name,
        'campaign_id'          : campaign_id,
        'destination_type'     : destination_type,
        'optimization_goal'    : optimization_goal,
        'bid_strategy'         : bid_strategy,
        'bid_amount'           : bid_amount,
        'billing_event'        : billing_event,
        'daily_budget'         : daily_budget,
        'targeting'            : targeting,
        'status'               : status
    }
    if start_time is not None:
        form_data['start_time'] = start_time
    if end_time is not None:
        form_data['end_time'] = end_time
    print(f'form_data: {form_data}')

    sqs = boto3.client('sqs', region_name='ap-southeast-1')

    # Create the adset in Facebook Ads Manager
    url = f'https://graph.facebook.com/v19.0/{ad_account_id}/adsets'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.post(url, headers=headers, data=form_data)
    if response.status_code != 200:
        return {
            "statusCode": response.status_code,
        }

    response_data = response.json()
    print(f'response_data: {response_data}')

    # Update the Google Sheets row with the adset ID
    adset_id = response_data['id']
    gsEndpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!B{row_number}?valueInputOption=USER_ENTERED&access_token={gs_access_token}'
    gsPayload = {
        'range': f'\'{GOOGLE_SHEETS_SHEET_NAME}\'!B{row_number}',
        'values': [[adset_id]]
    }
    response = requests.put(gsEndpoint, json=gsPayload)
    if response.status_code != 200:
        print(response.json())
        return {
            "statusCode": response.status_code,
        }
    
    # Send a success message to the SQS
    response = sqs.send_message(
        QueueUrl=SUCCESS_QUEUE_URL,
        MessageBody=json.dumps({
            'adset_id': adset_id,
            'row_number': row_number
            })
    )
    print(f'Success message sent to SQS: {response}')
    
    return {
        "statusCode": 200
    }
