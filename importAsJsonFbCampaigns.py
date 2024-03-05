import json
import requests
import base64
import urllib.parse
import gspread

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
    # Extract all the event parameters
    ad_account_id = event['account_id']
    access_token = event['access_token']
    spreadsheet_id = event['spreadsheet_id']

    # Read the sheet
    workbook = gc.open_by_key(spreadsheet_id)
    sheet = workbook.worksheet("campaign-details")
    num_campaigns = sheet.col_values(1)[-1]
    last_row = int(num_campaigns) + 1
    range = f"A2:L{str(last_row)}"

    records = sheet.batch_get([range])[0]

    # for list in records:


    print(records)

    # Return a success message to the channel
    return {
        'statusCode': 200,
        'body': json.dumps('Command completed successfully.')
    }

if __name__ == "__main__":
    event = {
        "account_id": "1084205746169117",
        "access_token": "EAAjcdUNrk3MBO5NNXKZAGsX0USmluou0jBJz4W9SmNGJNdVZAMd4yrFV871Gm5ERDBSICF9GWFUaedZCPgEigiKF0aFht9p62Yi5643NiXbJzoxUA2vOXQLLz2vVV8RMih5kXE3cJzAQe00XPeluZC4ojWU0z8rkcA6DfwwPwEMjzsGOZBlBkILJ62qPrcG9G",
        "spreadsheet_id": "1GbDDulj8-J9M73Xrbeq0qmqwZPp_eppAdJ8ZcukL_3c"
    }

    lambda_handler(event, None)

