import json
import requests
import base64
import urllib.parse
import gspread


SLACK_POST_MESSAGE_ENDPOINT = "https://slack.com/api/chat.postMessage"

# HTTP Headers
headers = {
    "Authorization": "Bearer xoxb-241133470262-6669054380198-ac8cNCGQl10GtHNojwRIj59C",
}

# GSpread Authentication
credentials = {
  "type": "service_account",
  "project_id": "automations-415608",
  "private_key_id": "2a4697d55c355263a970a27543d0e1eadf9d737b",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDsVLchexqAqk4/\nZmanobox84CDt9bkNN6cLdtXCDcxQmHe8JWVBP4xXmdSk0JYfqQu655j0JynJ+aA\nIklgb64cnrhpQ87miy3Ab5Qr/hvyAyXd9vpwI1ujvJ3gVNCej85G46JkFN/HuS8Q\nYtMTNx+xCJIOd18BPO+LxtYvgho7Zt67iZdVHvQAWOZjsDVqW6hfOqN10WoD0V3e\niR4T10vwkFU3Ys87jhW1txvWgcCJHgdoA31aMDViMfFVxoYyLjdFuECIAr/Kh5su\ndkePlFZewVEl5B911Jj+GSutnmqdetgcLe67ZPYU/H7jGwukYCGEwrz9QkDHkpe0\nIDkm4m1ZAgMBAAECggEABf9btbqj4F+yDv4rHRZHx+G9QVp71nHDCSVJcOAmqmuG\nrqYzXZicAiZk/92jLDoWh5GiL41JPx1jm50tzd03sXE+Y9Qn3tuUWdMFvcdmmnyF\noahAEHLNQ2P+K7BrVO14V33fuU4lpFy+OtpkhJMnDOfsm6JgOQNSCZ2OV56jyh2/\nN1eHIf53qy2E+ReQWQ6lfx8o7So+y+NjyMWjVworZ6XRuF3v55xAfK1hI9K5485C\nTrjodgKQLQJimz6XfeoX6yLQX58NRRB9FDZ4ounTOa51Qt5JjyM1dZ5sr4IZZ/MG\nstg6Uzt2E54sbZL5iPQEUu4YJDL+7R5NTOTvqXP+wQKBgQD8DLWSSfnk4pN4UWnu\nPHMDt+Q3B+HXP2hTPMVc7LBTSBfq+mfdKnIGsa/HRWHfhyqfvjw3k8g9ufcFQ82/\nvxLEC155nDTdxX5Ev7esFE3SFg16EKG4SO/C936mQdKlDct974Ib0bJbnv51Frb1\n/0ch1iDmsYmPu8+DPFnvhwXX8QKBgQDwCPA3mpyHnacIViy1226zuPaf5HS5DEOI\n4BcCfdxg3djk1cayuFlHisiIOm9fhxJM6Lm5ibSRIhOg1UUVsYke17ohqzgh4ULH\nvYuoBLWNDn3FR8OvHtHqCWRey/RESK97v+j7c7+WhhCAgxZPlRt4XbuBcFwWYwbr\n2m24xioT6QKBgFDVWp3x75zCNX1OzuRCqrg0j5I+iuVXRoP7Z2hn2By9cD5B1HGP\nnUYcUj1cOQlQ9hCJGBLS6FMzgs9DcYbfJouNAd2KhUHihp5Rxfv//v0zaVsOXm8V\npR8n9Iwpa/7XL73RxC5b0BGmKgEvKbo3Bn8Jhz+1DGL2XpS+FDHHYc5hAoGBAIrH\ncDOF1chm8wLT6AfA9dE9OIIbcQzoNUe24DbVlAwBV/x+SOJdyWieqfBxcKEXlBIZ\nYAAQyPA8doK/q7CuM6w8Z+Y9ezfDaHvZcBxVlK4YWcktA8uFEzKv+XMBkpnEOIlg\n3JA9TOD3ZCUZJVYfzIEcGGPvFZ7v5DmK0XNKR1u5AoGBANZyFG2+QW/4lzgV5Af6\nfSbqIo/vFKjBdxvmWSIKir4VmfMY3p1yCykLlmrRW7PJvnFHaiCM1ShXErOORQik\nQ8wxJuUkAQBLij0Rl83TVY3ZcLK+jedrvc54gH7ncf1Mz10+jYnMGMQzNa0e7s0w\ne7i/vIDdwS//k1+h3V4onyS3\n-----END PRIVATE KEY-----\n",
  "client_email": "aws-api-access@automations-415608.iam.gserviceaccount.com",
  "client_id": "111835630461973643619",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/aws-api-access%40automations-415608.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
gc = gspread.service_account_from_dict(credentials)

def lambda_handler(event, context):
    # The body of the event is a base64 encoded string in a URL format
    event_base64 = event['body']
    event_url = base64.b64decode(event_base64).decode('utf-8')
    event_params = urllib.parse.parse_qs(event_url)

    # Extract all the event parameters
    command = event_params['command'][0]
    event_text = event_params['text'][0]
    cmd_params = event_text.split()
    response_url = event_params['response_url'][0]
    trigger_id = event_params['trigger_id'][0]
    user_id = event_params['user_id'][0]
    channel_id = event_params['channel_id'][0]

    # Check if the command is valid
    if len(cmd_params) != 3:
        requests.post()
        return {
            'statusCode': 200,
            'body': json.dumps('Please check your inputs. There should be three inputs separated by space.')
        }

    # Send an acknowledgement to the channel
    requests.post(response_url, json={'text': command + ' command received. Now processing...'})

    # Read the sheet
    sheet_id = cmd_params[0]
    range_name = cmd_params[1]

    # Return a success message to the channel
    return {
        'statusCode': 200,
        'body': json.dumps('Command completed successfully.')
    }
