import json
import urllib.parse as urlparse

def lambda_handler(event, context):
    urlQueryString = event['body']
    parsedUrl = urlparse.parse_qs(urlQueryString)
    payload = json.loads(parsedUrl['payload'][0])

    # The payload is now a dictionary
    # Keys are not fixed, use a tool like webhook.site to test what keys are available
    # Take the payload from webhook.site and run it through jsonlint.com to format it
    # and see what keys are available

    return {}
