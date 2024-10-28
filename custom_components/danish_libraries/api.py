import httpx
import json
import re
import httpx
import pathlib
from .models.LibraryConfig import LibraryConfig
from .models.Rerservation import Reservation
import asyncio

LIBRARIES: dict[str, LibraryConfig] = {}
with open(pathlib.Path(__file__).parent.joinpath("libraries.json"), "r", encoding="UTF8") as f:
    LIBRARIES = LibraryConfig.from_json(json.loads(f.read()))

def reauth_on_fail(func):
    async def wrapper(*args):
        library: Library = args[0]
        try:
            if not library.user_token:
                await library.authenticate()
            return await func(*args)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await library.authenticate()
                return await func(*args)
            raise e
    return wrapper

class Library(object):
    def __init__(self, municipality: str, user_id: str, pin: str):
        if municipality.lower() not in LIBRARIES.keys():
            raise ValueError(f'Municipality "{municipality}" not found in list')
        self.municipality = LIBRARIES[municipality.lower()]
        self.user_id = user_id
        self.pin = pin
        self.session = None
        self.user_token = None
        self.library_token = None

    @property
    def user_bearer_token(self):
        return f'Bearer {self.user_token}'
    
    @property
    def library_bearer_token(self):
        return f'Bearer {self.library_token}'

    async def authenticate(self):
        if not self.session:
            self.session = httpx.AsyncClient()
        await self.session.get(self.municipality.url, follow_redirects=True)
        login_page_request = await self.session.get(f'{self.municipality.url}/login?current-path=/user/me/dashboard', follow_redirects=True)
        login_page_text = login_page_request.text
        login_path = re.search(r'action=\"(.*?)\"', login_page_text).group(1)
        common_login_url = f"https://login.bib.dk{login_path}"
        payload= {
            "agency": self.municipality.branch_id,
            "libraryName": self.municipality.name,
            "loginBibDkUserId": self.user_id,
            "pincode": self.pin
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
        await self.session.post(common_login_url, headers=headers, data=payload, follow_redirects=True)
        token_response = await self.session.get(f'{self.municipality.url}/dpl-react/user-tokens', follow_redirects=False)
        token_text = token_response.text
        self.user_token = re.search(r'\"user\",\s*\"(.*?)\"', token_text).group(1)
        self.library_token = re.search(r'\"library\",\s*\"(.*?)\"', token_text).group(1)

    @reauth_on_fail
    async def get_loans(self):
        headers={
            'Authorization': self.user_bearer_token
        }
        loans_response = await self.session.get('https://fbs-openplatform.dbc.dk/external/agencyid/patrons/patronid/loans/v2', headers=headers, follow_redirects=True)
        return loans_response.json()

    @reauth_on_fail
    async def get_reservations(self) -> list[Reservation]:
        headers={
            'Authorization': self.user_bearer_token
        }
        reservations_response = await self.session.get('https://fbs-openplatform.dbc.dk/external/v1/agencyid/patrons/patronid/reservations/v2', headers=headers, follow_redirects=True)
        tasks = []
        for res in reservations_response.json():
           tasks.append(
            asyncio.get_event_loop().create_task(self.get_info(res["recordId"], res, Reservation))
           )
        done, pending = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        return [x.result() for x in done]
            

    
    @reauth_on_fail
    async def get_info(self, book_id: str, original_object, output_type: type):
        headers={
            'Authorization': self.user_bearer_token
        }
        body={
            "query": "query getManifestationViaMaterialByFaust($faust: String!) { manifestation(faust: $faust) { titles { full } creators { display } pid } }",
            "variables": {
                "faust": book_id
            }
        }
        url = "https://temp.fbi-api.dbc.dk/fbcms-vis/graphql"
        book_response = await self.session.post(url, headers=headers, json=body, follow_redirects=True)
        book = book_response.json()
        params = {
            "type": "pid",
            "identifiers": book["data"]["manifestation"]["pid"],
            "sizes": "small"
        }
        image_headers={
            'Authorization': self.library_bearer_token
        }
        image_url = 'https://cover.dandigbib.org/api/v2/covers'

        image_response = await self.session.get(image_url, headers=image_headers, params=params, follow_redirects=True)
        image_json = image_response.json()[0]
        
        return output_type(original_object, book["data"]["manifestation"], image_json["imageUrls"]["small"]["url"])