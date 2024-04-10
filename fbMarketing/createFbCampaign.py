import json
import requests
import urllib.parse as urlparse

def lambda_handler(event, context):
  is_single = False
  # Check if function is being triggered from another Lambda Function via API Gateway
  if 'campaign_name' not in event:
    is_single = True
    event_body            = event['body']
    event_params          = urlparse.parse_qs(event_body)
    campaign_name         = event_params['campaign_name'][0]
    campaign_objective    = event_params['campaign_objective'][0]
    campaign_buying_type  = event_params['campaign_buying_type'][0]
    campaign_status       = event_params['campaign_status'][0]
    special_ad_categories = event_params['special_ad_categories'][0]
    access_token          = event_params['access_token'][0]
    ad_account_id         = event_params['ad_account_id'][0]
  # If not, then it is being triggered from a Slack workflow
  else:  
    campaign_name = event['campaign_name']
    campaign_objective = event['campaign_objective']
    campaign_buying_type = event['campaign_buying_type']
    campaign_status = event['campaign_status']
    special_ad_categories = event['special_ad_categories']
    access_token = event['access_token']
    ad_account_id = event['ad_account_id']
  
  if len(special_ad_categories) == 0:
    special_ad_categories = ["NONE"]

  form_data = {
    'name': campaign_name,
    'objective': campaign_objective,
    'buying_type': campaign_buying_type,
    'status': campaign_status,
    'special_ad_categories': special_ad_categories,
    'access_token': access_token
  }

  url = f'https://graph.facebook.com/v19.0/{ad_account_id}/campaigns'
  response = requests.post(url, data=form_data)
  response_data = response.json()
    
  if is_single:
    return {
      "isBase64Encoded": False,
      "statusCode": 200,
      "body": json.dumps(response_data)
    }
    
  return response_data