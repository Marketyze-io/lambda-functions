import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

SLACK_PUSH_VIEWS_ENDPOINT = "https://slack.com/api/views.push"
SLACK_UPDATE_VIEWS_ENDPOINT = "https://slack.com/api/views.update"
SLACK_POST_MESSAGE_ENDPOINT = "https://slack.com/api/chat.postMessage"
AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"

SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

# HTTP Headers
headers = {
	"Authorization": "Bearer ",
}

modal_bulkFbCampaigns = {
	"type": "modal",
	"callback_id": "fbBulkCampaign-form",
	"submit": {
		"type": "plain_text",
		"text": "Submit",
		"emoji": True
	},
	"close": {
		"type": "plain_text",
		"text": "Cancel",
		"emoji": True
	},
	"title": {
		"type": "plain_text",
		"text": "Facebook Campaigns",
		"emoji": True
	},
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": ":wave: Hey David!\n\nHere's the info I need before I can create those campaigns for you.",
				"emoji": True
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "input",
			"block_id": "spreadsheet_url_input",
			"element": {
				"type": "url_text_input",
				"action_id": "spreadsheet_url_input-action"
			},
			"label": {
				"type": "plain_text",
				"text": "Spreadsheet URL",
				"emoji": True
			}
		},
		{
			"type": "input",
			"block_id": "ad_acc_id_input",
			"element": {
				"type": "plain_text_input",
				"action_id": "ad_acc_id_input-action"
			},
			"label": {
				"type": "plain_text",
				"text": "Ad Account ID",
				"emoji": True
			}
		},
		{
			"type": "input",
			"block_id": "token_input",
			"element": {
				"type": "plain_text_input",
				"action_id": "token_input-action"
			},
			"label": {
				"type": "plain_text",
				"text": "Access Token",
				"emoji": True
			}
		}
	]
}

def lambda_handler(event, context):
	urlQueryString = event['body']
	parsedUrl = urlparse.parse_qs(urlQueryString)
	payload = json.loads(parsedUrl['payload'][0])

	# Get the token from AWS Parameter Store
	secret_name = urlparse.quote(SECRET_NAME, safe="")
	endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
	req = urllib.request.Request(endpoint)
	req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
	token = urllib.request.urlopen(req).read()
	token = json.loads(token)
	headers['Authorization'] = f"Bearer {token['Parameter']['Value']}"

	match payload['type']:
		case 'view_submission':
			view_type = payload['view']['callback_id']
			match view_type:
				case 'fbBulkCampaign-form':
					submission = payload['view']['state']['values']
					spreadsheet_url = submission['spreadsheet_url_input']['spreadsheet_url_input-action']['value']
					ad_acc_id = submission['ad_acc_id_input']['ad_acc_id_input-action']['value']
					token = submission['token_input']['token_input-action']['value']
					channel_id = payload['view']['private_metadata']
					# Do something with the data
					requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers=headers, data={
						"channel": channel_id,
						"text": f"Spreadsheet URL: {spreadsheet_url}\nAd Account ID: {ad_acc_id}\nAccess Token: {token}"
					})
					return {
						"statusCode": 200
					}
				case _:
					return json.dumps({
						"statusCode": 200
					})
		
		case 'block_actions':
			trigger_id = payload['trigger_id']
			view_id = payload['view']['id']
			action = payload['actions'][0]['action_id']
			channel_id = payload['view']['private_metadata']
			match action:
				case 'button-bulk-fb-campaigns':
					modal_bulkFbCampaigns['private_metadata'] = channel_id
					requests.post(SLACK_UPDATE_VIEWS_ENDPOINT, headers=headers, data={
						"view_id": view_id,
						"view": json.dumps(modal_bulkFbCampaigns)
					})
				case _:
					requests.post(SLACK_PUSH_VIEWS_ENDPOINT, headers=headers, data={
						"trigger_id": trigger_id,
						"view": json.dumps(modal_bulkFbCampaigns)
					})

	return {
		'statusCode': 200
	}
