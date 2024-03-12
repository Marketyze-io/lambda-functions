import json
import requests
import urllib.parse

SLACK_OPEN_VIEWS_ENDPOINT = "https://slack.com/api/views.open"

# HTTP Headers
headers = {
	"Authorization": "Bearer xoxb-241133470262-6786705625524-lM5i9Ider3NSERhR6wRSitDu",
}

# Modal Payload
modal = {
	"type": "modal",
	"callback_id": "modal-identifier",
	"title": {
		"type": "plain_text",
		"text": "FB Marketing Bot"
	},
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Hi, here's what I can help you with:"
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "section",
			"block_id": "section-bulk-campaigns",
			"text": {
				"type": "mrkdwn",
				"text": "*Bulk Import* Facebook Ad Campaigns"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Get Started"
				},
				"action_id": "button-bulk-fb-campaigns"
			}
		},
		{
			"type": "section",
			"block_id": "section-bulk-adsets",
			"text": {
				"type": "mrkdwn",
				"text": "*Bulk Import* Facebook Adsets"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Get Started"
				},
				"action_id": "button-bulk-fb-adsets"
			}
		},
		{
			"type": "section",
			"block_id": "section-bulk-ads",
			"text": {
				"type": "mrkdwn",
				"text": "*Bulk Import* Facebook Ads"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Get Started"
				},
				"action_id": "button-bulk-fb-ads"
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "section",
			"block_id": "section-manage-targeting",
			"text": {
				"type": "mrkdwn",
				"text": "*Manage* Facebook Audiences/Targeting"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Get Started"
				},
				"action_id": "button-bulk-fb-ads"
			}
		},
		{
			"type": "section",
			"block_id": "section-upload-adcreatives",
			"text": {
				"type": "mrkdwn",
				"text": "*Upload* Facebook Ad Creatives"
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Get Started"
				},
				"action_id": "button-upload-fb-ad-creatives"
			}
		}
	]
}

def lambda_handler(event, context):
	event_body = event['body']
	event_params = urllib.parse.parse_qs(event_body)
	response_url = event_params['response_url'][0]
	trigger_id = event_params['trigger_id'][0]
	user_id = event_params['user_id'][0]
	channel_id = event_params['channel_id'][0]
	modal['private_metadata'] = channel_id

	data = {
		"trigger_id": trigger_id,
		"view": json.dumps(modal)
	}

	response = requests.post(SLACK_OPEN_VIEWS_ENDPOINT, data=data, headers=headers)

	return {
		'statusCode': 200
	}
