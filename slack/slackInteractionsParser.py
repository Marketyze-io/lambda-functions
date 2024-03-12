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
          "text": ":wave: Hey David!\n\nWe'd love to hear from you how we can make this place the best place you’ve ever worked.",
          "emoji": True
        }
      },
      {
        "type": "divider"
      },
      {
        "type": "input",
        "label": {
          "type": "plain_text",
          "text": "You enjoy working here at Pistachio & Co",
          "emoji": True
        },
        "element": {
          "type": "radio_buttons",
          "options": [
            {
              "text": {
                "type": "plain_text",
                "text": "Strongly agree",
                "emoji": True
              },
              "value": "1"
            },
            {
              "text": {
                "type": "plain_text",
                "text": "Agree",
                "emoji": True
              },
              "value": "2"
            },
            {
              "text": {
                "type": "plain_text",
                "text": "Neither agree nor disagree",
                "emoji": True
              },
              "value": "3"
            },
            {
              "text": {
                "type": "plain_text",
                "text": "Disagree",
                "emoji": True
              },
              "value": "4"
            },
            {
              "text": {
                "type": "plain_text",
                "text": "Strongly disagree",
                "emoji": True
              },
              "value": "5"
            }
          ]
        }
      },
      {
        "type": "input",
        "label": {
          "type": "plain_text",
          "text": "What do you want for our team weekly lunch?",
          "emoji": True
        },
        "element": {
          "type": "multi_static_select",
          "placeholder": {
            "type": "plain_text",
            "text": "Select your favorites",
            "emoji": True
          },
          "options": [
            {
              "text": {
                "type": "plain_text",
                "text": ":pizza: Pizza",
                "emoji": True
              },
              "value": "value-0"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":fried_shrimp: Thai food",
                "emoji": True
              },
              "value": "value-1"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":desert_island: Hawaiian",
                "emoji": True
              },
              "value": "value-2"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":meat_on_bone: Texas BBQ",
                "emoji": True
              },
              "value": "value-3"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":hamburger: Burger",
                "emoji": True
              },
              "value": "value-4"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":taco: Tacos",
                "emoji": True
              },
              "value": "value-5"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":green_salad: Salad",
                "emoji": True
              },
              "value": "value-6"
            },
            {
              "text": {
                "type": "plain_text",
                "text": ":stew: Indian",
                "emoji": True
              },
              "value": "value-7"
            }
          ]
        }
      },
      {
        "type": "input",
        "label": {
          "type": "plain_text",
          "text": "What can we do to improve your experience working here?",
          "emoji": True
        },
        "element": {
          "type": "plain_text_input",
          "multiline": True
        }
      },
      {
        "type": "input",
        "label": {
          "type": "plain_text",
          "text": "Anything else you want to tell us?",
          "emoji": True
        },
        "element": {
          "type": "plain_text_input",
          "multiline": True
        },
        "optional": True
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
