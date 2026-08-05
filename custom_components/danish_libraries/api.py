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
    DEFAULT_IMAGE_URL,
    FBS_OPEN_PLATFORM_BASE_URL,
    IMAGE_FROM_PID_GRAPH_QL_QUERY,
    INFO_BASE_URL,
    INFO_GRAPH_QL_QUERY,
    LIBRARIES,
    LOGGER,
    MAX_RETRIES,
    PUBHUB_BASE_URL,
    SEARCH_ISBN_GRAPH_QL_QUERY,
)
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


def _log_response(label: str, response: httpx.Response) -> None:
    LOGGER.debug(
        "%s (status=%s, url=%s): %s",
        label,
        response.status_code,
        response.request.url,
        response.text,
    )


def reauth_on_fail(func):
    async def wrapper(*args, _retry_count=0):
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
            if e.response.status_code < 500 or _retry_count >= MAX_RETRIES:
                raise
            LOGGER.debug(e, exc_info=True)
            LOGGER.debug(
                "Server error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
            )
            await asyncio.sleep(30)
            return await wrapper(*args, _retry_count=_retry_count + 1)
        except httpx.ConnectError as e:
            if _retry_count >= MAX_RETRIES:
                raise
            LOGGER.debug(e)
            LOGGER.debug(
                "Connect error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
                exc_info=True,
            )
            await asyncio.sleep(30)
            return await wrapper(*args, _retry_count=_retry_count + 1)
        except Exception as e:
            if _retry_count >= MAX_RETRIES:
                raise
            LOGGER.debug(e)
            LOGGER.debug(
                "Unknown error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
                exc_info=True,
            )
            await asyncio.sleep(30)
            return await wrapper(*args, _retry_count=_retry_count + 1)

    return wrapper


class Library:
    def __init__(self, municipality: str, user_id: str, pin: str, hass):
        if municipality.lower() not in LIBRARIES.keys():
            raise ValueError(f'Municipality "{municipality}" not found in list')
        self.municipality = LIBRARIES[municipality.lower()]
        self.user_id = user_id
        self.pin = pin
        self.session: httpx.AsyncClient | None = None
        self.user_token = None
        self.library_token = None
        self.hass = hass

    @property
    def user_bearer_token(self):
        return f"Bearer {self.user_token}"

    @property
    def library_bearer_token(self):
        return f"Bearer {self.library_token}"

    async def authenticate(self, _retry_count=0):
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
            LOGGER.debug(
                "Auth homepage response (status=%s, url=%s)", r.status_code, r.url
            )
            login_page_request = await self.session.get(
                f"{self.municipality.url}/login?current-path=/user/me/dashboard",
                follow_redirects=True,
                timeout=None,
            )
            login_page_request.raise_for_status()
            LOGGER.debug(
                "Auth login page response (status=%s, url=%s)",
                login_page_request.status_code,
                login_page_request.url,
            )
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
            LOGGER.debug(
                "Auth login submit response (status=%s, url=%s)", r.status_code, r.url
            )
            token_response = await self.session.get(
                f"{self.municipality.url}/dpl-react/user-tokens",
                follow_redirects=False,
                timeout=None,
            )
            token_response.raise_for_status()
            # Body intentionally not logged: it contains the live bearer tokens.
            LOGGER.debug(
                "Auth token response (status=%s, url=%s)",
                token_response.status_code,
                token_response.url,
            )
            token_text = token_response.text

            self.user_token = re.search(r"\"user\",\s*\"(.*?)\"", token_text).group(1)
            self.library_token = re.search(
                r"\"library\",\s*\"(.*?)\"", token_text
            ).group(1)
        except httpx.HTTPStatusError as e:
            if e.response.status_code < 500 or _retry_count >= MAX_RETRIES:
                raise
            LOGGER.debug(e, exc_info=True)
            LOGGER.debug(
                "Server error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
            )
            await asyncio.sleep(30)
            return await self.authenticate(_retry_count=_retry_count + 1)
        except httpx.ConnectError as e:
            if _retry_count >= MAX_RETRIES:
                raise
            LOGGER.debug(e)
            LOGGER.debug(
                "Connect error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
                exc_info=True,
            )
            await asyncio.sleep(30)
            return await self.authenticate(_retry_count=_retry_count + 1)
        except Exception as e:
            if _retry_count >= MAX_RETRIES:
                LOGGER.error("Unknown error", exc_info=True)
                raise
            LOGGER.debug(e)
            LOGGER.debug(
                "Unknown error, retrying in 30sec (%s/%s)",
                _retry_count + 1,
                MAX_RETRIES,
                exc_info=True,
            )
            await asyncio.sleep(30)
            return await self.authenticate(_retry_count=_retry_count + 1)

    @reauth_on_fail
    async def get_profile_info(self) -> ProfileInfo:
        headers = {"Authorization": self.user_bearer_token}
        profile_response = await self.session.get(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patrons/patronid/v4",
            headers=headers,
            follow_redirects=True,
            timeout=None,
        )
        profile_response.raise_for_status()
        _log_response("Raw profile response", profile_response)
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
        _log_response("Raw fees response", fee_response)
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
        _log_response("Raw loans response", loans_response)
        tasks = []
        for res in loans_response.json():
            tasks.append(
                asyncio.create_task(
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
        _log_response("Raw ereolen loans response", loans_response)
        tasks = []
        for res in loans_response.json()["loans"]:
            tasks.append(
                asyncio.create_task(
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
        _log_response("Raw reservations response", reservations_response)
        tasks = []
        for res in reservations_response.json():
            tasks.append(
                asyncio.create_task(self.get_info(res["recordId"], res, Reservation))
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
        _log_response("Raw ereolen reservations response", reservations_response)
        tasks = []
        for res in reservations_response.json()["reservations"]:
            tasks.append(
                asyncio.create_task(
                    self.get_ereolen_info(res["identifier"], res, EreolenReservation)
                )
            )
        return await self.unpack_results(tasks)

    @reauth_on_fail
    async def get_info(self, identifier: str, original_object, output_type: type):
        headers = {"Authorization": self.user_bearer_token}
        body = {
            "query": INFO_GRAPH_QL_QUERY,
            "variables": {"faust": identifier},
        }
        urls = [
            f"{INFO_BASE_URL}/fbcms-vis/graphql",
            f"{INFO_BASE_URL}/DDFCMS-VIS/graphql",
            f"{INFO_BASE_URL}/opac/graphql",
            f"{INFO_BASE_URL}/next-present/graphql",
        ]
        tasks = [
            asyncio.create_task(
                self.session.post(
                    url, headers=headers, json=body, follow_redirects=False
                )
            )
            for url in urls
        ]
        pid = None
        info = None
        results: list[httpx.Response] = await self.unpack_results(tasks)
        for res in results:
            _log_response("Raw get_info response", res)
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

        image_url = await self.get_image_cover(pid)
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
        _log_response("Raw ereolen info response", info_response)
        info = info_response.json()
        pid = await self.convert_isbn_to_pid(identifier)
        image_url = await self.get_image_cover(pid)
        return output_type(
            original_object,
            info["product"],
            image_url,
        )

    @reauth_on_fail
    async def convert_isbn_to_pid(self, isbn: str):
        try:
            payload = {
                "query": SEARCH_ISBN_GRAPH_QL_QUERY,
                "variables": {
                    "cql": f"term.isbn={isbn}",
                    "offset": 0,
                    "limit": 1,
                    "filters": {},
                },
            }
            headers = {"Authorization": self.library_bearer_token}
            urls = [
                f"{INFO_BASE_URL}/fbcms-soeg/graphql",
                f"{INFO_BASE_URL}/next/graphql",
            ]
            tasks = [
                asyncio.create_task(
                    self.session.post(
                        url,
                        headers=headers,
                        json=payload,
                        follow_redirects=False,
                        timeout=None,
                    )
                )
                for url in urls
            ]
            results: list[httpx.Response] = await self.unpack_results(tasks)
            for response in results:
                _log_response("Raw convert_isbn_to_pid response", response)
                if response.status_code != 200:
                    continue
                data = (
                    response.json()
                    .get("data", {})
                    .get("complexSearch", {})
                    .get("works", [])
                )
                if not data or len(data) < 1 or data[0] is None:
                    continue
                pid = (
                    data[0]
                    .get("manifestations", {})
                    .get("bestRepresentation", {})
                    .get("pid")
                )
                if pid:
                    return pid

            raise ValueError(
                f"Could not convert ISBN {isbn} to PID, maybe this municipality uses a new url. MUNICIPALITY={self.municipality}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise e
        except Exception as e:
            LOGGER.exception(e)

    @reauth_on_fail
    async def get_image_cover(self, pid: str):
        if not pid:
            return DEFAULT_IMAGE_URL
        try:
            payload = {
                "query": IMAGE_FROM_PID_GRAPH_QL_QUERY,
                "variables": {"pids": [pid]},
            }
            image_headers = {"Authorization": self.library_bearer_token}
            cover_urls = [
                f"{INFO_BASE_URL}/fbcms-soeg/graphql",
                f"{INFO_BASE_URL}/next/graphql",
            ]
            tasks = [
                asyncio.create_task(
                    self.session.post(
                        url,
                        headers=image_headers,
                        json=payload,
                        follow_redirects=False,
                        timeout=None,
                    )
                )
                for url in cover_urls
            ]
            results: list[httpx.Response] = await self.unpack_results(tasks)

            for image_response in results:
                _log_response("Raw get_image_cover response", image_response)
                if image_response.status_code != 200:
                    continue
                manifestations = (
                    image_response.json().get("data", {}).get("manifestations", [])
                )
                if (
                    not manifestations
                    or len(manifestations) < 1
                    or manifestations[0] is None
                ):
                    continue
                image_urls = manifestations[0].get("cover", {})
                if image_urls and any(
                    size in image_urls for size in ["small", "medium", "large"]
                ):
                    break

            if not image_urls:
                LOGGER.debug("No images returned for title")
                return DEFAULT_IMAGE_URL

            image_url = None
            if "small" in image_urls.keys() and "url" in image_urls["small"].keys():
                image_url = image_urls["small"]["url"]
            if "medium" in image_urls.keys() and "url" in image_urls["medium"].keys():
                image_url = image_urls["medium"]["url"]
            if "large" in image_urls.keys() and "url" in image_urls["large"].keys():
                image_url = image_urls["large"]["url"]

            return DEFAULT_IMAGE_URL if not image_url else image_url
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise e
        except Exception as e:
            LOGGER.exception(e)
            return DEFAULT_IMAGE_URL

    @reauth_on_fail
    async def renew_loan(self, loans: list[Loan]):
        headers = {"Authorization": self.user_bearer_token}
        loan_ids = [loan.loan_id for loan in loans]
        renew_response = await self.session.post(
            f"{FBS_OPEN_PLATFORM_BASE_URL}/external/agencyid/patrons/patronid/loans/renew/v2",
            headers=headers,
            json=loan_ids,
            follow_redirects=True,
            timeout=None,
        )
        renew_response.raise_for_status()
        _log_response("Raw renew_loan response", renew_response)

    async def unpack_results(self, tasks):
        if len(tasks) == 0:
            return []
        done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
        results = []
        for x in done:
            if ex := x.exception():
                LOGGER.exception(ex)
                continue
            results.append(x.result())
        return results

    @staticmethod
    def get_nested_value(d: dict[str, any], keys: list[str]) -> any:
        next_key, *remaining_keys = keys
        value = d[next_key]
        if len(remaining_keys) == 0 or value is None:
            return value
        return Library.get_nested_value(value, remaining_keys)
