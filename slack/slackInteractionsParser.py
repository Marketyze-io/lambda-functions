import json
import urllib.parse as urlparse
import requests

SLACK_PUSH_VIEWS_ENDPOINT = "https://slack.com/api/views.push"

# HTTP Headers
headers = {
    "Authorization": "Bearer xoxb-241133470262-6669054380198-ac8cNCGQl10GtHNojwRIj59C",
}

modal_bulkFbCampaigns = {
	"type": "modal",
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

    trigger_id = payload['trigger_id']
    action = payload['actions'][0]['action_id']

    match action:
        case 'button-bulk-fb-campaigns':
            requests.post(SLACK_PUSH_VIEWS_ENDPOINT, headers=headers, data={
                "trigger_id": trigger_id,
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
