import urllib.parse as urlparse

def lambda_handler(event, context):
    urlQueryString = event['body']
    # print(urlQueryString)
    parsedUrl = urlparse.parse_qs(urlQueryString)
    # print(parsedUrl)
    channel_id = parsedUrl['channel_id'][0]
    text = parsedUrl['text'][0]

    params = text.split()

    return {
        'channel_id': channel_id,
        'account_id': params[0],
        'access_token': params[1],
        'spreadsheet_id': params[2]
    }
