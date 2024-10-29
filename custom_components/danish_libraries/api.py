import asyncio
import re

try:
    # pylint: disable=invalid-name
    from homeassistant.helpers.httpx_client import get_async_client, httpx
except ImportError:
    import httpx

    get_async_client = httpx.AsyncClient

from .const import (
    COMMON_LOGIN_BASE_URL,
    COMMON_LOGIN_HEADERS,
    COVER_BASE_URL,
    FBS_OPEN_PLATFORM_BASE_URL,
    INFO_BASE_URL,
    INFO_GRAPG_QL_QUERY,
    LIBRARIES,
    PUBHUB_BASE_URL,
)
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


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


class Library:
    def __init__(self, municipality: str, user_id: str, pin: str, hass):
        if municipality.lower() not in LIBRARIES.keys():
            raise ValueError(f'Municipality "{municipality}" not found in list')
        self.municipality = LIBRARIES[municipality.lower()]
        self.user_id = user_id
        self.pin = pin
        self.session = None
        self.user_token = None
        self.library_token = None
        self.hass = hass

    @property
    def user_bearer_token(self):
        return f"Bearer {self.user_token}"

    @property
    def library_bearer_token(self):
        return f"Bearer {self.library_token}"

    async def authenticate(self):
        self.session = (
            get_async_client() if not self.hass else get_async_client(self.hass)
        )
        r = await self.session.get(self.municipality.url, follow_redirects=True)
        r.raise_for_status()
        login_page_request = await self.session.get(
            f"{self.municipality.url}/login?current-path=/user/me/dashboard",
            follow_redirects=True,
        )
        login_page_request.raise_for_status()
        login_page_text = login_page_request.text
        login_path = re.search(r"action=\"(.*?)\"", login_page_text).group(1)
        common_login_url = f"{COMMON_LOGIN_BASE_URL}{login_path}"
        payload = {
            "agency": self.municipality.branch_id,
            "libraryName": self.municipality.name,
            "loginBibDkUserId": self.user_id,
            "pincode": self.pin,
        }
        r = await self.session.post(
            common_login_url,
            headers=COMMON_LOGIN_HEADERS,
            data=payload,
            follow_redirects=True,
        )
        r.raise_for_status()
        token_response = await self.session.get(
            f"{self.municipality.url}/dpl-react/user-tokens", follow_redirects=False
        )
        token_response.raise_for_status()
        token_text = token_response.text
        self.user_token = re.search(r"\"user\",\s*\"(.*?)\"", token_text).group(1)
        self.library_token = re.search(r"\"library\",\s*\"(.*?)\"", token_text).group(1)

    @reauth_on_fail
    async def get_profile_info(self) -> ProfileInfo:
        headers = {"Authorization": self.user_bearer_token}
        profile_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patrons/patronid/v2",
            headers=headers,
            follow_redirects=True,
        )
        profile_response.raise_for_status()
        return ProfileInfo(profile_response.json()["patron"])

    @reauth_on_fail
    async def get_fees(self):
        headers = {"Authorization": self.user_bearer_token}
        params = {"includepaid": True, "includenonpayable": True}
        fee_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patron/patronid/fees/v2",
            headers=headers,
            follow_redirects=True,
            params=params,
        )
        fee_response.raise_for_status()
        return fee_response.json()

    @reauth_on_fail
    async def get_loans(self):
        headers = {"Authorization": self.user_bearer_token}
        loans_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patrons/patronid/loans/v2",
            headers=headers,
            follow_redirects=True,
        )
        loans_response.raise_for_status()
        tasks = []
        for res in loans_response.json():
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_info(res["loanDetails"]["recordId"], res, Loan)
                )
            )
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        return [x.result() for x in done]

    @reauth_on_fail
    async def get_ereolen_loans(self):
        headers = {"Authorization": self.user_bearer_token}
        loans_response = await self.session.get(
            f"{PUBHUB_BASE_URL}/v1/user/loans",
            headers=headers,
            follow_redirects=True,
        )
        loans_response.raise_for_status()
        tasks = []
        for res in loans_response.json()["loans"]:
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_ereolen_info(
                        res["libraryBook"]["identifier"], res, EreolenLoan
                    )
                )
            )
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        return [x.result() for x in done]

    @reauth_on_fail
    async def get_reservations(self) -> list[Reservation]:
        headers = {"Authorization": self.user_bearer_token}
        reservations_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/v1/agencyid/patrons/patronid/reservations/v2",
            headers=headers,
            follow_redirects=True,
        )
        reservations_response.raise_for_status()
        tasks = []
        for res in reservations_response.json():
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_info(res["recordId"], res, Reservation)
                )
            )
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        return [x.result() for x in done]

    @reauth_on_fail
    async def get_ereolen_reservations(self):
        headers = {"Authorization": self.user_bearer_token}
        reservations_response = await self.session.get(
            f"{PUBHUB_BASE_URL}/v1/user/reservations",
            headers=headers,
            follow_redirects=True,
        )
        reservations_response.raise_for_status()
        tasks = []
        for res in reservations_response.json()["reservations"]:
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_ereolen_info(res["identifier"], res, EreolenReservation)
                )
            )
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        return [x.result() for x in done]

    @reauth_on_fail
    async def get_info(self, identifier: str, original_object, output_type: type):
        headers = {"Authorization": self.user_bearer_token}
        body = {
            "query": INFO_GRAPG_QL_QUERY,
            "variables": {"faust": identifier},
        }
        url = f"{INFO_BASE_URL}/fbcms-vis/graphql"
        info_response = await self.session.post(
            url, headers=headers, json=body, follow_redirects=True
        )
        info_response.raise_for_status()
        info = info_response.json()
        image_url = await self.get_image_cover(
            info["data"]["manifestation"]["pid"], "pid"
        )
        return output_type(
            original_object,
            info["data"]["manifestation"],
            image_url,
        )

    @reauth_on_fail
    async def get_ereolen_info(
        self, identifier: str, original_object, output_type: type
    ):
        headers = {"Authorization": self.user_bearer_token}
        info_response = await self.session.get(
            f"{PUBHUB_BASE_URL}/v1/products/{identifier}",
            headers=headers,
            follow_redirects=True,
        )
        info_response.raise_for_status()
        info = info_response.json()
        image_url = await self.get_image_cover(identifier, "isbn")
        return output_type(
            original_object,
            info["product"],
            image_url,
        )

    @reauth_on_fail
    async def get_image_cover(self, identifier: str, id_type: str):
        params = {
            "type": id_type,
            "identifiers": identifier,
            "sizes": "small",
        }
        image_headers = {"Authorization": self.library_bearer_token}
        image_response = await self.session.get(
            f"{COVER_BASE_URL}/api/v2/covers",
            headers=image_headers,
            params=params,
            follow_redirects=True,
        )
        image_response.raise_for_status()
        image_json = image_response.json()[0]
        return image_json["imageUrls"]["small"]["url"]
