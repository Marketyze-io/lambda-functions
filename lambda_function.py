import json
import requests
import base64
import urllib.parse


def read_sheet(credentials, sheet_id, range_name):
    # Create a service object for interacting with the Sheets API
    service = build('sheets', 'v4', credentials=credentials)

    # Call the Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print("No data found.")
        return

    return values


def lambda_handler(event, context):
    # The body of the event is a base64 encoded string in a URL format
    event_base64 = event['body']
    event_url = base64.b64decode(event_base64).decode('utf-8')
    event_params = urllib.parse.parse_qs(event_url)

    # Extract the command and text from the event parameters
    command = event_params['command'][0]
    event_text = event_params['text'][0]
    response_url = event_params['response_url'][0]
    cmd_inputs = event_text.split()

    # Check if the command is valid
    if len(cmd_inputs) != 3:
        return {
            'statusCode': 200,
            'body': json.dumps('Please check your inputs. There should be three inputs separated by space.')
        }

    # Send an acknowledgement to the user
    requests.post(response_url, json={'text': command + ' command received. Now processing...'})

    # Read the sheet
    sheet_id = cmd_inputs[0]
    range_name = cmd_inputs[1]
    values = read_sheet(credentials, sheet_id, range_name)

    # Return a success message to the user
    return {
        'statusCode': 200,
        'body': json.dumps('Command completed successfully. The sheet has been read. The values are: ' + str(values))
    }
