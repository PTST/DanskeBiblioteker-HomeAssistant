import requests
import re
import json

libraries = {}
library = {}
with open("libraries.json", "r", encoding="UTF8") as f:
    libraries = json.loads(f.read())

municipality = 'Aalborg'

try:
    library = libraries[municipality.lower()]
except:
    raise Exception('Could not get library')


def get_book_info(book_id: str, session: requests.session, user_token, library_token):
    headers={
        'Authorization': f'Bearer {user_token}'
    }
    body={
        "query": "query getManifestationViaMaterialByFaust($faust: String!) { manifestation(faust: $faust) { titles { full } creators { display } pid } }",
        "variables": {
            "faust": book_id
        }
    }
    url = "https://temp.fbi-api.dbc.dk/fbcms-vis/graphql"
    book_response = session.post(url, headers=headers, json=body, allow_redirects=True, verify=False)
    book = book_response.json()
    params = {
        "type": "pid",
        "identifiers": book["data"]["manifestation"]["pid"],
        "sizes": "small"
    }
    image_headers={
        'Authorization': f'Bearer {library_token}'
    }
    image_url = 'https://cover.dandigbib.org/api/v2/covers'

    image_response = session.get(image_url, headers=image_headers, params=params, allow_redirects=True, verify=False)
    image_json = image_response.json()[0]
    book["data"]["manifestation"]["image_url"] = image_json["imageUrls"]["small"]["url"]
    print(book)

session = requests.session()
session.get(library["url"], allow_redirects=True, verify=False)

r = session.get(f'{library["url"]}/login?current-path=/user/me/dashboard', verify=False)

login = re.search(r'action=\"(.*?)\"', r.text).group(1)

url = f"https://login.bib.dk{login}"

payload= {
    "agency": library["branchId"],
    "libraryName": library["name"],
    "loginBibDkUserId": "CPR",
    "pincode": "PIN"
}
headers = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'Accept-Language': 'en-US,en;q=0.9,da;q=0.8',
  'Cache-Control': 'max-age=0',
  'Connection': 'keep-alive',
  'Content-Type': 'application/x-www-form-urlencoded',
  'Origin': 'https://login.bib.dk',
  'Referer': 'https://login.bib.dk/login',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'same-origin',
  'Sec-Fetch-User': '?1',
  'Upgrade-Insecure-Requests': '1',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0',
  'sec-ch-ua': '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"'
}
print(session.cookies)

response = session.post(url, headers=headers, data=payload, verify=False, allow_redirects=True)
token_response = session.get(f'{library["url"]}/dpl-react/user-tokens', allow_redirects=True, verify=False)
user_token = re.search(r'\"user\",\s*\"(.*?)\"', token_response.text).group(1)
library_token = re.search(r'\"library\",\s*\"(.*?)\"', token_response.text).group(1)

headers={
    'Authorization': f'Bearer {user_token}'
}

loans_response = session.get('https://fbs-openplatform.dbc.dk/external/agencyid/patrons/patronid/loans/v2', headers=headers, allow_redirects=True, verify=False)
reservations_response = session.get('https://fbs-openplatform.dbc.dk/external/v1/agencyid/patrons/patronid/reservations/v2', headers=headers, allow_redirects=True, verify=False)

for book in loans_response.json():
    book_id = book["loanDetails"]["recordId"]
    get_book_info(book_id, session, library_token, library_token)

for book in reservations_response.json():
    book_id = book["recordId"]
    get_book_info(book_id, session, library_token, library_token)