/* global fetch*/
async function callAPI(uri, body) {
    const response = fetch(uri, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    return response;
}

export const handler = async (event) => {
    console.log(event)
    const event_body = JSON.parse(event.body);
    callAPI('https://srdb19dj4h.execute-api.ap-southeast-1.amazonaws.com/default/campaigns/bulk/create', {
        channel_id    : event_body.channel_id,
        fbAccessToken : event_body.fbAccessToken,
        adAccountId   : event_body.adAccountId,
        gsAccessToken : event_body.gsAccessToken,
        spreadsheetId : event_body.spreadsheetId,
        });
  
    const response = {
      statusCode: 200
    };
    return response;
  };
  