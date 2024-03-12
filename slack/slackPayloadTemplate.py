import json
import urllib.parse as urlparse

def lambda_handler(event, context):
    urlQueryString = event['body']
    parsedUrl = urlparse.parse_qs(urlQueryString)
    payload = json.loads(parsedUrl['payload'][0])

    return {}
