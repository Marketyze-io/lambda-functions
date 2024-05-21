import json
import os
import urllib.parse as urlparse
import urllib.request
import requests
import datetime

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
UPDATE_SAVED_AUDIENCES_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/audiences/update"
UPDATE_PAGES_ENDPOINT = "https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/pages/update"

MASTER_SHEET_ID = "1am9nNSWcUYpbvHFA8nk0GAvzedYvyBGTqNNT9YAX0wM"
MASTER_WORSKSHEET_NAME = "spreadsheet-master-list"

GOOGLE_SHEETS_ROOT_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
CAMPAIGNS_SHEET = {'name': '🤖Rob_FB_Campaigns', 'id': '987478379'}
ADSETS_SHEET = {'name': '🤖Rob_FB_Adsets', 'id': '655550453'}
ADCOPIES_SHEET = {'name': '🤖Rob_FB_Adcopies', 'id': '224614968'}
AUDIENCES_SHEET = {'name': '🤖Rob_FB_Audiences', 'id': '862287605'}
MEDIA_SHEET = {'name': '🤖Rob_FB_Media', 'id': '1547157615'}
PAGES_SHEET = {'name': '🤖Rob_FB_Pages', 'id': '1337036354'}

SLACK_POST_MESSAGE_ENDPOINT = 'https://slack.com/api/chat.postMessage'

def slack_post_message(channel_id, token, message):
    slack_payload = {
        'channel': channel_id,
        'text': message
    }
    slack_request = requests.post(SLACK_POST_MESSAGE_ENDPOINT, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())


def lambda_handler(event, context):
    channel_id      = event['channel_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    ad_account_name = event['ad_account_name']

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

    # Get spreadsheet name
    gs_name_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}?access_token={gs_access_token}"
    gs_response = requests.get(gs_name_endpoint)
    spreadsheet_name = gs_response.json()['properties']['title']

    slack_post_message(channel_id, token, f':robot_face: I\'m now initialising {spreadsheet_name} :robot_face:\nPlease don\'t do anything to the spreadsheet\nThis will take a few seconds...')

    # Check if each worksheet already exists
    new_sheet_ids = {}
    master_sheet_ids = {
        CAMPAIGNS_SHEET['name']: CAMPAIGNS_SHEET['id'],
        ADSETS_SHEET['name']: ADSETS_SHEET['id'],
        ADCOPIES_SHEET['name']: ADCOPIES_SHEET['id'],
        AUDIENCES_SHEET['name']: AUDIENCES_SHEET['id'],
        MEDIA_SHEET['name']: MEDIA_SHEET['id'],
        PAGES_SHEET['name']: PAGES_SHEET['id']
    }
    gs_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}?access_token={gs_access_token}"
    gs_response = requests.get(gs_endpoint)
    gs_sheets = gs_response.json()['sheets']
    # Check if the sheet already exists, then remove it from the master list
    for sheet in gs_sheets:
        sheet_name = sheet['properties']['title']
        sheet_id = sheet['properties']['sheetId']
        if sheet_name in master_sheet_ids:
            print(f"{sheet_name} sheet already exists")
            new_sheet_ids[sheet_name] = sheet_id
            del master_sheet_ids[sheet_name]
        
    # Create the worksheets that don't exist
    for sheet_name in master_sheet_ids:
        sheet_id = master_sheet_ids[sheet_name]
        # Create the worksheet
        payload = {
            "destinationSpreadsheetId": spreadsheet_id,
        }
        gs_copy_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + MASTER_SHEET_ID}/sheets/{sheet_id}:copyTo?access_token={gs_access_token}"
        gs_response = requests.post(gs_copy_endpoint, json=payload)
        # Check for errors during sheet creation
        if gs_response.status_code != 200:
            print(gs_response.json())
            slack_post_message(channel_id, token, f'Whoops! I couldn\'t duplicate one of the Rob worksheets. Please try again later :disappointed:')
            print("Error msg sent to Slack")
            return {
                'statusCode': 500,
                'body': json.dumps('Error creating sheet')
            }
        # Rename the sheet
        new_sheet_id = gs_response.json()['sheetId']
        payload = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": new_sheet_id,
                            "title": sheet_name
                        },
                        "fields": "title"
                    }
                }
            ]
        }
        gs_rename_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
        gs_response = requests.post(gs_rename_endpoint, json=payload)
        new_sheet_ids[sheet_name] = sheet_id

    print(new_sheet_ids)

    # Get the formula for the targeting spec in the adset sheet
    gs_formulas_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADSETS_SHEET['name']}!K3?valueRenderOption=FORMULA&access_token={gs_access_token}"
    gs_response = requests.get(gs_formulas_endpoint)
    targeting_spec_formula = gs_response.json()['values'][0][0]
    
    print(targeting_spec_formula)

    # Get the formula for the creative hash in the adcopy sheet
    gs_formulas_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!G3?valueRenderOption=FORMULA&access_token={gs_access_token}"
    gs_response = requests.get(gs_formulas_endpoint)
    creative_hash_formula = gs_response.json()['values'][0][0]

    print(creative_hash_formula)

    # Get the formula for the xlookups in the adcopy sheet
    gs_formulas_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!H3?valueRenderOption=FORMULA&access_token={gs_access_token}"
    gs_response = requests.get(gs_formulas_endpoint)
    xlookup_formula = gs_response.json()['values'][0][0]

    print(xlookup_formula)

    # Get the formula for the formatted CTA in the adcopy sheet
    gs_formulas_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!L3?valueRenderOption=FORMULA&access_token={gs_access_token}"
    gs_response = requests.get(gs_formulas_endpoint)
    formatted_cta_formula = gs_response.json()['values'][0][0]

    print(formatted_cta_formula)

    # Get the formula for the Page ID in the adcopy sheet
    gs_formulas_endpoint = f"{GOOGLE_SHEETS_ROOT_URL + spreadsheet_id}/values/{ADCOPIES_SHEET['name']}!O3?valueRenderOption=FORMULA&access_token={gs_access_token}"
    gs_response = requests.get(gs_formulas_endpoint)
    page_id_formula = gs_response.json()['values'][0][0]

    print(page_id_formula)

    # Fix the broken references in the adset sheet
    payload = {
        "requests": [
            # Clear existing data validation rules in the Adsets Audience columm
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADSETS_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 9,
                        "endColumnIndex": 10
                    }
                }
            },
            # Recreate the data validation rules in the Audience column
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADSETS_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 9,
                        "endColumnIndex": 10
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [
                                {
                                    "userEnteredValue": f"='{AUDIENCES_SHEET['name']}'!$A$3:$A"
                                }
                            ]
                        },
                        "inputMessage": "Please select an audience from the dropdown list",
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            },
            # Overwrite the targeting spec formulas in the adset sheet
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_ids['🤖Rob_FB_Adsets'],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 10,
                        "endColumnIndex": 11
                    },
                    "cell": {
                        "userEnteredValue": {
                            "formulaValue": targeting_spec_formula
                        }
                    },
                    "fields": "*"
                }
            },
            # Clear existing data validation rules in the Adcopies sheet Creative columm
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADCOPIES_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 5,
                        "endColumnIndex": 6
                    }
                }
            },
            # Recreate the data validation rules in the Adcopies sheet Creative column
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADCOPIES_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 5,
                        "endColumnIndex": 6
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [
                                {
                                    "userEnteredValue": f"='{MEDIA_SHEET['name']}'!$B$3:$B"
                                }
                            ]
                        },
                        "inputMessage": "Please select a Creative from the dropdown list",
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            },
            # Clear existing data validation rules in the Adcopies sheet CTA_formatted columm
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADCOPIES_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 11,
                        "endColumnIndex": 12
                    }
                }
            },
            # Overwrite the creative hash formulas in the adcopy sheet
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_ids['🤖Rob_FB_Adcopies'],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 11,
                        "endColumnIndex": 12
                    },
                    "cell": {
                        "userEnteredValue": {
                            "formulaValue": creative_hash_formula
                        }
                    },
                    "fields": "*"
                }
            },
            # Overwrite the xlookup formulas in the adcopy sheet
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_ids['🤖Rob_FB_Adcopies'],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 7,
                        "endColumnIndex": 11
                    },
                    "cell": {
                        "userEnteredValue": {
                            "formulaValue": xlookup_formula
                        }
                    },
                    "fields": "*"
                }
            },
            # Overwrite the formatted CTA formulas in the adcopy sheet
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_ids['🤖Rob_FB_Adcopies'],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 11,
                        "endColumnIndex": 12
                    },
                    "cell": {
                        "userEnteredValue": {
                            "formulaValue": formatted_cta_formula
                        }
                    },
                    "fields": "*"
                }
            },
            # Clear existing data validation rules in the Adcopies sheet Facebook Page columm
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADCOPIES_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 13,
                        "endColumnIndex": 14
                    }
                }
            },
            # Recreate the data validation rules in the Adcopies sheet Facebook Page column
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": new_sheet_ids[ADCOPIES_SHEET['name']],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 13,
                        "endColumnIndex": 14
                    },
                    "rule": {
                        "condition": {
                            "type": "ONE_OF_RANGE",
                            "values": [
                                {
                                    "userEnteredValue": f"='{PAGES_SHEET['name']}'!$A$3:$A"
                                }
                            ]
                        },
                        "inputMessage": "Please select a Facebook Page from the dropdown list",
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            },
            # Overwrite the Page ID formulas in the adcopy sheet
            {
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_ids['🤖Rob_FB_Adcopies'],
                        "startRowIndex": 2,
                        "endRowIndex": 102,
                        "startColumnIndex": 14,
                        "endColumnIndex": 15
                    },
                    "cell": {
                        "userEnteredValue": {
                            "formulaValue": page_id_formula
                        }
                    },
                    "fields": "*"
                }
            }
        ]
    }
    gs_fix_references_endpoint = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}"
    gs_response = requests.post(gs_fix_references_endpoint, json=payload)
    print(gs_response.json())

    # Update the saved audiences sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_SAVED_AUDIENCES_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, f'Whoops! I couldn\'t update the saved audiences. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    # Update the pages sheet
    payload = {
        "spreadsheet_id" : spreadsheet_id,
        "gs_access_token": gs_access_token,
        "fb_access_token": fb_access_token,
        "ad_account_id"  : ad_account_id
    }
    response = requests.post(UPDATE_PAGES_ENDPOINT, json=payload)
    if response.status_code != 200:
        slack_post_message(channel_id, token, f'Whoops! I couldn\'t update the pages. Please try it manually later. :disappointed:')
        print("Error msg sent to Slack")

    # Add spreadsheet id to the master-list
    gs_append_endpoint = GOOGLE_SHEETS_ROOT_URL + MASTER_SHEET_ID + f"/values/'{MASTER_WORSKSHEET_NAME}'!A3:append?access_token={gs_access_token}&valueInputOption=USER_ENTERED"
    datetime_now = datetime.datetime.now() + datetime.timedelta(hours=7)
    gs_append_body = {
        "range": "'spreadsheet-master-list'!A3",
        "majorDimension": "ROWS",
        "values": [[
          ad_account_name,
          ad_account_id,
          spreadsheet_id,
          datetime_now.strftime("%Y-%m-%d %H:%M:%S"),
        ]],
      };
    gs_append_response = requests.post(gs_append_endpoint, json=gs_append_body)

      # Handle the error if the gs_append endpoint was not called successfully
    if gs_append_response.status_code != 200:
        slack_post_message(channel_id, token, f'Whoops! I couldn\'t update the master list. Please contact one of the app maintainers. :disappointed:')
        print("Error msg sent to Slack")
    else:
        slack_post_message(channel_id, token, f":tada: {spreadsheet_name} is now ready for use! :tada:\nFeel free to start working on the spreadsheet again :smile:")

    return {
        'statusCode': 200
    }
