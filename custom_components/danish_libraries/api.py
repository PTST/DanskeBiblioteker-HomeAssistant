import asyncio
import re

try:
    # pylint: disable=invalid-name
    from homeassistant.helpers.httpx_client import create_async_httpx_client, httpx
except ImportError:
    import httpx

    create_async_httpx_client = httpx.AsyncClient

from .const import (
    COMMON_LOGIN_BASE_URL,
    COMMON_LOGIN_HEADERS,
    COVER_BASE_URL,
    DEFAULT_IMAGE_URL,
    FBS_OPEN_PLATFORM_BASE_URL,
    INFO_BASE_URL,
    INFO_GRAPG_QL_QUERY,
    LIBRARIES,
    LOGGER,
    PUBHUB_BASE_URL,
)
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


def reauth_on_fail(func):
    async def wrapper(*args):
        library: Library = args[0]
        try:
            LOGGER.debug(func.__name__)
            if not library.user_token:
                await library.authenticate()
            return await func(*args)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                await library.authenticate()
                return await func(*args)
            if e.response.status_code >= 500:
                LOGGER.debug(e, exc_info=True)
                LOGGER.debug("Unknown error, retrying in 30sec")
                await asyncio.sleep(30)
                return await func(*args)
            raise e
        except httpx.ConnectError as e:
            LOGGER.debug(e)
            LOGGER.debug("Connect error, retrying in 30sec", exc_info=True)
            await asyncio.sleep(30)
            return await func(*args)
        except Exception as e:
            LOGGER.debug(e)
            LOGGER.debug("Unknown error, retrying in 30sec", exc_info=True)
            await asyncio.sleep(30)
            return await func(*args)

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
        try:
            LOGGER.debug("Authenticating")
            self.session = (
                create_async_httpx_client()
                if not self.hass
                else create_async_httpx_client(self.hass)
            )
            self.session.cookies.clear()
            r = await self.session.get(
                self.municipality.url, follow_redirects=True, timeout=None
            )
            r.raise_for_status()
            login_page_request = await self.session.get(
                f"{self.municipality.url}/login?current-path=/user/me/dashboard",
                follow_redirects=True,
                timeout=None,
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
                timeout=None,
            )
            r.raise_for_status()
            token_response = await self.session.get(
                f"{self.municipality.url}/dpl-react/user-tokens",
                follow_redirects=False,
                timeout=None,
            )
            token_response.raise_for_status()
            token_text = token_response.text

            self.user_token = re.search(r"\"user\",\s*\"(.*?)\"", token_text).group(1)
            self.library_token = re.search(
                r"\"library\",\s*\"(.*?)\"", token_text
            ).group(1)
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                LOGGER.debug(e, exc_info=True)
                LOGGER.debug("Unknown error, retrying in 30sec")
                await asyncio.sleep(30)
                return await self.authenticate()
            raise e
        except httpx.ConnectError as e:
            LOGGER.debug(e)
            LOGGER.debug("Connect error, retrying in 30sec", exc_info=True)
            await asyncio.sleep(30)
            return await self.authenticate()
        except Exception as e:
            LOGGER.debug(e)
            LOGGER.debug("Unknown error, retrying in 30sec", exc_info=True)
            await asyncio.sleep(30)
            return await self.authenticate()

    @reauth_on_fail
    async def get_profile_info(self) -> ProfileInfo:
        headers = {"Authorization": self.user_bearer_token}
        profile_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patrons/patronid/v2",
            headers=headers,
            follow_redirects=True,
            timeout=None,
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
            timeout=None,
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
            timeout=None,
        )
        loans_response.raise_for_status()
        tasks = []
        for res in loans_response.json():
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_info(res["loanDetails"]["recordId"], res, Loan)
                )
            )
        return await self.unpack_results(tasks)

    @reauth_on_fail
    async def get_ereolen_loans(self):
        headers = {"Authorization": self.user_bearer_token}
        loans_response = await self.session.get(
            f"{PUBHUB_BASE_URL}/v1/user/loans",
            headers=headers,
            follow_redirects=True,
            timeout=None,
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
        return await self.unpack_results(tasks)

    @reauth_on_fail
    async def get_reservations(self) -> list[Reservation]:
        headers = {"Authorization": self.user_bearer_token}
        reservations_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/v1/agencyid/patrons/patronid/reservations/v2",
            headers=headers,
            follow_redirects=True,
            timeout=None,
        )
        reservations_response.raise_for_status()
        tasks = []
        for res in reservations_response.json():
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_info(res["recordId"], res, Reservation)
                )
            )
        return await self.unpack_results(tasks)

    @reauth_on_fail
    async def get_ereolen_reservations(self):
        headers = {"Authorization": self.user_bearer_token}
        reservations_response = await self.session.get(
            f"{PUBHUB_BASE_URL}/v1/user/reservations",
            headers=headers,
            follow_redirects=True,
            timeout=None,
        )
        reservations_response.raise_for_status()
        tasks = []
        for res in reservations_response.json()["reservations"]:
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.get_ereolen_info(res["identifier"], res, EreolenReservation)
                )
            )
        return await self.unpack_results(tasks)

    @reauth_on_fail
    async def get_info(self, identifier: str, original_object, output_type: type):
        headers = {"Authorization": self.user_bearer_token}
        body = {
            "query": INFO_GRAPG_QL_QUERY,
            "variables": {"faust": identifier},
        }
        tasks = []
        urls = [
            f"{INFO_BASE_URL}/fbcms-vis/graphql",
            f"{INFO_BASE_URL}/DDFCMS-VIS/graphql",
            f"{INFO_BASE_URL}/opac/graphql",
        ]
        for url in urls:
            tasks.append(
                asyncio.get_event_loop().create_task(
                    self.session.post(
                        url, headers=headers, json=body, follow_redirects=False
                    )
                )
            )
        pid = None
        info = None
        results: list[httpx.Response] = await self.unpack_results(tasks)
        for res in results:
            if res.status_code != 200:
                continue
            info = Library.get_nested_value(res.json(), ["data", "manifestation"])
            if info is None:
                continue
            pid = info.get("pid")
            if pid is not None:
                break

        if pid is None:
            LOGGER.error(
                "Could not extract PID from object, maybe this municipality uses a new url. MUNICIPALITY=%s",
                self.municipality,
            )

        image_url = await self.get_image_cover(pid, "pid")
        return output_type(
            original_object,
            info,
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
            timeout=None,
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
            "sizes": "small,medium,large",
        }
        image_headers = {"Authorization": self.library_bearer_token}
        image_response = await self.session.get(
            f"{COVER_BASE_URL}/api/v2/covers",
            headers=image_headers,
            params=params,
            follow_redirects=True,
            timeout=None,
        )
        image_response.raise_for_status()
        results = image_response.json()
        if len(results) == 0:
            LOGGER.debug("No image results found for title")
            LOGGER.debug(image_response.request.__dict__)
            return DEFAULT_IMAGE_URL
        image_json = results[0]
        image_urls = image_json["imageUrls"]
        if "small" in image_urls.keys() and "url" in image_urls["small"].keys():
            return image_json["imageUrls"]["small"]["url"]
        if "medium" in image_urls.keys() and "url" in image_urls["medium"].keys():
            return image_json["imageUrls"]["medium"]["url"]
        if "large" in image_urls.keys() and "url" in image_urls["large"].keys():
            return image_json["imageUrls"]["large"]["url"]
        LOGGER.debug("No images returned for title")
        LOGGER.debug(image_response.request.__dict__)
        return DEFAULT_IMAGE_URL

    async def unpack_results(self, tasks):
        if len(tasks) == 0:
            return []
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        for x in done:
            if ex := x.exception():
                LOGGER.exception(ex)
        return [x.result() for x in done]

    @staticmethod
    def get_nested_value(d: dict[str, any], keys: list[str]) -> any:
        next_key = keys.pop(0)
        value = d[next_key]
        if len(keys) == 0 or value is None:
            return value
        return Library.get_nested_value(value, keys)
