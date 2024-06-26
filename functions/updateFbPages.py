import json
import requests
import datetime

PAGES_SHEET_NAME = '🤖Rob_FB_Pages'

def lambda_handler(event, context):
    event_params    = json.loads(event['body'])
    print(event_params)
    fb_access_token = event_params['fb_access_token']
    ad_account_id   = event_params['ad_account_id']
    gs_access_token = event_params['gs_access_token']
    spreadsheet_id  = event_params['spreadsheet_id']

    # Get the saved audiences from Facebook
    pages_endpoint = f'https://graph.facebook.com/v19.0/{ad_account_id}/promote_pages'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {fb_access_token}'
    }
    response = requests.get(pages_endpoint, headers=headers)
    print(response.json())

    # Append the saved audiences to Google Sheets
    gs_append_payload = {
        "range": f"{PAGES_SHEET_NAME}!A3",
        "majorDimension": "ROWS",
        "values": [],
    }
    for page in response.json()['data']:
        gs_append_payload['values'].append([page['name'], page['id']])
    
    # Clear the existing data in the sheet
    gs_clear_endpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{PAGES_SHEET_NAME}!A3:C:clear?access_token={gs_access_token}'
    response = requests.post(gs_clear_endpoint)

    # Append the new data
    gs_append_endpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{PAGES_SHEET_NAME}!A3:append?valueInputOption=RAW&access_token={gs_access_token}'
    response = requests.post(gs_append_endpoint, data=json.dumps(gs_append_payload))
    print(response.status_code)
    print(response.text)

    # Update the "Last updated: " cell with the current time in UTC+7
    current_time = datetime.datetime.now() + datetime.timedelta(hours=7)
    gs_update_payload = {
        "values": [[f'Last updated: {current_time.strftime("%Y-%m-%d %H:%M:%S")} (UTC+7)']]
    }
    gs_update_endpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{PAGES_SHEET_NAME}!A1?valueInputOption=USER_ENTERED&access_token={gs_access_token}'
    response = requests.put(gs_update_endpoint, data=json.dumps(gs_update_payload))
    
    return {
        'statusCode': response.status_code
    }