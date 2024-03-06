import json
import requests

def lambda_handler(event, context):
  campaign_name = event['campaign_name']
  campaign_objective = event['campaign_objective']
  campaign_buying_type = event['campaign_buying_type']
  campaign_status = event['campaign_status']
  special_ad_categories = event['special_ad_categories']
  access_token = event['access_token']
  ad_account_id = event['ad_account_id']

  form_data = {
    'name': campaign_name,
    'objective': campaign_objective,
    'buying_type': campaign_buying_type,
    'status': campaign_status,
    'special_ad_categories': special_ad_categories,
    'access_token': access_token
  }

  url = f'https://graph.facebook.com/v19.0/act_{ad_account_id}/campaigns'
  response = requests.post(url, data=form_data)
  response_data = response.json()
  return response_data