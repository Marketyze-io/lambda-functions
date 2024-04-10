import json
import gspread

# GSpread Authentication
credentials = {

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

    dicts = []

    for list in records:
        dict = {
            "name": list[0],
            "id": list[1],
            "objective": list[3],
            "buying_type": list[4],
            "status": list[5],
            "special_ad_categories": list[11]
        }
        dicts.append(dict)

    # print(dicts_json)

    return dicts
