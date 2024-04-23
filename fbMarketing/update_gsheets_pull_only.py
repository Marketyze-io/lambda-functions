import json
import os
import urllib.parse as urlparse
import urllib.request
import requests

AWS_PARAM_STORE_ENDPOINT = "http://localhost:2773/systemsmanager/parameters/get/"
SECRET_NAME = "/slack/fb-marketing/bot-oauth-token"
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')

def get_index(list, key, value):
    for i, dic in enumerate(list):
        if dic[key] == value:
            return i
    return None

def lambda_handler(event, context):
    channel_id      = event['channel_id']
    fb_access_token = event['fb_access_token']
    ad_account_id   = event['ad_account_id']
    gs_access_token = event['gs_access_token']
    spreadsheet_id  = event['spreadsheet_id']

    # Get the token from AWS Parameter Store
    secret_name = urlparse.quote(SECRET_NAME, safe="")
    endpoint = f"{AWS_PARAM_STORE_ENDPOINT}?name={secret_name}&withDecryption=true"
    req = urllib.request.Request(endpoint)
    req.add_header('X-Aws-Parameters-Secrets-Token', aws_session_token)
    token = urllib.request.urlopen(req).read()
    token = json.loads(token)
    print("Slack token retrieved")

    # Send an ack to Slack
    print("Sending ack to Slack")
    slack_endpoint = 'https://slack.com/api/chat.postMessage'
    slack_payload = {
        'channel': channel_id,
        'text': f'Pulling Facebook campaign data!'
    }
    slack_request = requests.post(slack_endpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())
    print("Ack sent to Slack")

    # Get the campaigns from Facebook
    print("Getting campaigns from Facebook")
    fb_endpoint = f'https://graph.facebook.com/v19.0/{ad_account_id}/campaigns?fields=["id", "name", "objective", "buying_type", "status", "special_ad_categories"]&access_token={fb_access_token}'
    fb_request = requests.get(fb_endpoint)
    fb_campaigns = fb_request.json()['data']
    print("Campaigns retrieved from Facebook")
    print(fb_campaigns)

    # Check if the campaign-details sheet exists
    aws_lambda_endpoint = 'https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/campaigns/update/sheet'
    aws_lambda_payload = {
        'channel_id'     : channel_id,
        'spreadsheet_id' : spreadsheet_id,
        'gs_access_token': gs_access_token
    }
    aws_lambda_request = requests.get(aws_lambda_endpoint, json=aws_lambda_payload)
    print(aws_lambda_request.json())
    if aws_lambda_request.status_code != 200:
        return {
            'statusCode': 500,
            'body': json.dumps('Error updating Google Sheets')
        }

    # Get the data from Google Sheets
    gsCountEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/\'campaign-details\'!A1?access_token={gs_access_token}'
    response = requests.get(gsCountEndpoint)
    if response.status_code != 200:
        print(response.json())
    rowCount = int(response.json()['values'][0][0])
    print(f"Number of rows in Google Sheets: {str(rowCount)}")
    lastRowNum = str(rowCount + 2)
    gsEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/\'campaign-details\'!A3:L{lastRowNum}?access_token={gs_access_token}'
    print("Getting data from Google Sheets")
    response = requests.get(gsEndpoint)
    if response.status_code != 200:
        print(response.json())
    gs_data = response.json()['values']
    print("Data retrieved from Google Sheets")
    print(gs_data)

    # Prepare the data for Google Sheets
    campaigns_updated_count = 0
    campaigns_deleted_count = 0
    campaigns_added_count = 0
    update_payload = {
        "valueInputOption": "USER_ENTERED",
        "data": []
    }
    deletion_payload = {
        "requests": []
    }
    append_payload = {
        "valueInputOption": "USER_ENTERED",
        "data": []
    }

    for row in gs_data:
        # Check if the row has no campaign ID
        if row[1] == "":
            # Ignore this row
            continue
        # Check if the row has a campaign ID and is not found in Facebook campaigns
        elif not any(campaign["id"] == row[1] for campaign in fb_campaigns):
            # Delete this row
            row_index = gs_data.index(row) + 3
            deletion_payload["requests"].append({
                "deleteDimension": {
                    "range": {
                        "sheetId": 0,
                        "dimension": "ROWS",
                        "startIndex": row_index - 1,
                        "endIndex": row_index
                    }
                }
            })
            campaigns_deleted_count += 1
        # Check if the row has a campaign ID and is found in Facebook campaigns
        else:
            # Update this row
            fb_campaigns_index = get_index(fb_campaigns, "id", row[1])
            campaign_name = fb_campaigns[fb_campaigns_index]["name"]
            campaign_id   = fb_campaigns[fb_campaigns_index]["id"]
            campaign_objective = fb_campaigns[fb_campaigns_index]["objective"]
            match campaign_objective:
                case "OUTCOME_AWARENESS":
                    campaign_objective_dropdown = "Awareness"
                case "OUTCOME_TRAFFIC":
                    campaign_objective_dropdown = "Traffic"
                case "OUTCOME_ENGAGEMENT":
                    campaign_objective_dropdown = "Engagement"
                case "OUTCOME_LEADS":
                    campaign_objective_dropdown = "Leads"
                case "OUTCOME_APP_PROMOTION":
                    campaign_objective_dropdown = "App Promotion"
                case "OUTCOME_SALES":
                    campaign_objective_dropdown = "Sales"
            campaign_buying_type = fb_campaigns[fb_campaigns_index]["buying_type"]
            campaign_status = fb_campaigns[fb_campaigns_index]["status"]
            special_ad_categories = fb_campaigns[fb_campaigns_index]["special_ad_categories"]
            credit     = "TRUE" if "CREDIT"                     in special_ad_categories else "FALSE"
            employment = "TRUE" if "EMPLOYMENT"                 in special_ad_categories else "FALSE"
            housing    = "TRUE" if "HOUSING"                    in special_ad_categories else "FALSE"
            politics   = "TRUE" if "ISSUES_ELECTIONS_POLITICS"  in special_ad_categories else "FALSE"
            gambling   = "TRUE" if "ONLINE_GAMBLING_AND_GAMING" in special_ad_categories else "FALSE"

            requestData = {
                "range": f"'campaign-details'!A{str(gs_data.index(row)+3)}:K{str(gs_data.index(row)+4)}",
                "majorDimension": "ROWS",
                "values": [[campaign_name, campaign_id, campaign_objective_dropdown, campaign_objective, campaign_buying_type, campaign_status, credit, employment, housing, politics, gambling]]
            }
            update_payload['data'].append(requestData)
            campaigns_updated_count += 1
            fb_campaigns.pop(fb_campaigns_index)
    
    # Add new rows for campaigns not found in Google Sheets
    for campaign in fb_campaigns:
        campaign_name = campaign["name"]
        campaign_id   = campaign["id"]
        campaign_objective = campaign["objective"]
        match campaign_objective:
            case "OUTCOME_AWARENESS":
                campaign_objective_dropdown = "Awareness"
            case "OUTCOME_TRAFFIC":
                campaign_objective_dropdown = "Traffic"
            case "OUTCOME_ENGAGEMENT":
                campaign_objective_dropdown = "Engagement"
            case "OUTCOME_LEADS":
                campaign_objective_dropdown = "Leads"
            case "OUTCOME_APP_PROMOTION":
                campaign_objective_dropdown = "App Promotion"
            case "OUTCOME_SALES":
                campaign_objective_dropdown = "Sales"
        campaign_buying_type = campaign["buying_type"]
        campaign_status = campaign["status"]
        special_ad_categories = campaign["special_ad_categories"]
        credit     = "TRUE" if "CREDIT"                     in special_ad_categories else "FALSE"
        employment = "TRUE" if "EMPLOYMENT"                 in special_ad_categories else "FALSE"
        housing    = "TRUE" if "HOUSING"                    in special_ad_categories else "FALSE"
        politics   = "TRUE" if "ISSUES_ELECTIONS_POLITICS"  in special_ad_categories else "FALSE"
        gambling   = "TRUE" if "ONLINE_GAMBLING_AND_GAMING" in special_ad_categories else "FALSE"

        new_row_index = int(lastRowNum) + campaigns_added_count
        requestData = {
            "range": f"'campaign-details'!A{str(new_row_index+1)}:K{str(new_row_index+2)}",
            "majorDimension": "ROWS",
            "values": [[campaign_name, campaign_id, campaign_objective_dropdown, campaign_objective, campaign_buying_type, campaign_status, credit, employment, housing, politics, gambling]]
        }
        append_payload['data'].append(requestData)
        campaigns_added_count += 1

    # Update the Google Sheets
    if campaigns_updated_count == 0:
        print("No existing campaigns to update")
    else:
        print("Updating existing campaigns in Google Sheets")
        gsUpdateEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate?access_token={gs_access_token}'
        response = requests.post(gsUpdateEndpoint, json=update_payload)
        print(response.json())
        print("Existing campaigns updated")

    # Add new campaigns to Google Sheets
    if campaigns_added_count == 0:
        print("No new campaigns to add")
    else:
        print("Adding new campaigns to Google Sheets")
        gsAppendEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values:batchUpdate?access_token={gs_access_token}'
        response = requests.post(gsAppendEndpoint, json=append_payload)
        print(response.json())
        print("New campaigns added")

    # Delete rows not found in Facebook campaigns
    if campaigns_deleted_count == 0:
        print("No rows to delete")
    else:
        print("Deleting rows not found in Facebook campaigns")
        gsUpdateEndpoint = f'https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate?access_token={gs_access_token}'
        response = requests.post(gsUpdateEndpoint, json=deletion_payload)
        print(response.json())
        print("Rows deleted")

    # Send a message to Slack
    print("Sending message to Slack")
    slack_payload = {
        'channel': channel_id,
        'text': f'I\'m finished updating the spreadsheet! Here\'s what I did:\n\nRows updated: {campaigns_updated_count}\nRows added: {campaigns_added_count}\nRows deleted: {campaigns_deleted_count}'
    }
    slack_request = requests.post(slack_endpoint, headers
        ={'Authorization': f'Bearer {token['Parameter']['Value']}'}, data=slack_payload)
    print(slack_request.json())
    print("Message sent to Slack")

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }