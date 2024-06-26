import json
import requests
import urllib.parse as urlparse

def lambda_handler(event, context):
    event_body = event['body']

    start_time = None
    end_time = None

    # Check if event body is in JSON form
    if event_body.startswith('{'):
        event_params       = json.loads(event_body)
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
        if 'start_time' in event_params:
            start_time     = event_params['start_time']
        if 'end_time' in event_params:
            end_time       = event_params['end_time']

    # If not, then it is in URL-encoded form
    else:
        event_params       = urlparse.parse_qs(event_body)
        ad_account_id      = event_params['ad_account_id'][0]
        access_token       = event_params['access_token'][0]
        adset_name         = event_params['adset_name'][0]
        campaign_id        = event_params['campaign_id'][0]
        destination_type   = event_params['destination_type'][0]
        optimization_goal  = event_params['optimization_goal'][0]
        bid_strategy       = event_params['bid_strategy'][0]
        bid_amount         = event_params['bid_amount'][0]
        billing_event      = event_params['billing_event'][0]
        daily_budget       = event_params['daily_budget'][0]
        targeting          = event_params['targeting'][0]
        status             = event_params['status'][0]
        if 'start_time' in event_params:
            start_time     = event_params['start_time'][0]
        if 'end_time' in event_params:
            end_time       = event_params['end_time'][0]

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

    url = f'https://graph.facebook.com/v19.0/{ad_account_id}/adsets'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.post(url, headers=headers, data=form_data)
    print(f'response: {response.json()}')
    response_data = response.json()
    print(f'response_data: {response_data}')
    
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "body": json.dumps(response_data)
    }
