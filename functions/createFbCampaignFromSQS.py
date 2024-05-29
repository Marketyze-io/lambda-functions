import json
import requests
import boto3

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
GOOGLE_SHEETS_SHEET_NAME = '🤖Rob_FB_Campaigns'

SUCCESS_QUEUE_URL = 'https://sqs.ap-southeast-1.amazonaws.com/533267173231/fbCampaigns-successfulInvocation'

def lambda_handler(event, context):
  event_params          = json.loads(event['Records'][0]['body'])
  campaign_name         = event_params['campaign_name']
  campaign_objective    = event_params['campaign_objective']
  campaign_buying_type  = event_params['campaign_buying_type']
  campaign_status       = event_params['campaign_status']
  special_ad_categories = event_params['special_ad_categories']
  access_token          = event_params['access_token']
  ad_account_id         = event_params['ad_account_id']
  spreadsheet_id        = event_params['spreadsheet_id']
  row_number            = event_params['row_number']
  gs_access_token       = event_params['gs_access_token']
  if len(special_ad_categories) == 0:
    special_ad_categories = ["NONE"]

  form_data = {
    'name'                 : campaign_name,
    'objective'            : campaign_objective,
    'buying_type'          : campaign_buying_type,
    'status'               : campaign_status,
    'special_ad_categories': special_ad_categories,
    'access_token'         : access_token
  }
  print(f'form_data: {form_data}')

  sqs = boto3.client('sqs', region_name='ap-southeast-1')

  # Create the campaign in Facebook Ads Manager
  url = f'https://graph.facebook.com/v19.0/{ad_account_id}/campaigns'
  response = requests.post(url, data=form_data)
  if response.status_code != 200:
    return {
      "statusCode": response.status_code,
    }

  response_data = response.json()
  print(f'response_data: {response_data}')

  # Update the Google Sheets row with the campaign ID
  campaign_id = response_data['id']
  gsEndpoint = f'{GOOGLE_SHEETS_ROOT_URL}{spreadsheet_id}/values/\'{GOOGLE_SHEETS_SHEET_NAME}\'!B{row_number}?valueInputOption=USER_ENTERED&access_token={gs_access_token}'
  gsPayload = {
    'range': f'\'{GOOGLE_SHEETS_SHEET_NAME}\'!B{row_number}',
    'values': [[campaign_id]]
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
      'campaign_id': campaign_id,
      'row_number': row_number
      })
  )
  print(f'Success message sent to SQS: {response}')
  
  return {
    "statusCode": 200
  }
