# pylint: disable=line-too-long
import json
import pathlib

from .models import LibraryConfig

DOMAIN = "danish_libraries"

COMMON_LOGIN_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9,da;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://login.bib.dk",
    "Referer": "https://login.bib.dk/login",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
    "sec-ch-ua": '"Chromium";v="130", "Microsoft Edge";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}
COMMON_LOGIN_BASE_URL = "https://login.bib.dk"
FBS_OPEN_PLATFORM_BASE_URL = "https://fbs-openplatform.dbc.dk"
INFO_BASE_URL = "https://temp.fbi-api.dbc.dk"
INFO_GRAPG_QL_QUERY = "query getManifestationViaMaterialByFaust($faust: String!) { manifestation(faust: $faust) { titles { full } creators { display } abstract pid } }"
COVER_BASE_URL = "https://cover.dandigbib.org"
PUBHUB_BASE_URL = "https://pubhub-openplatform.dbc.dk"

LIBRARIES: dict[str, LibraryConfig] = {}
with open(
    pathlib.Path(__file__).parent.joinpath("libraries.json"), "r", encoding="UTF8"
) as f:
    LIBRARIES = LibraryConfig.from_json(json.loads(f.read()))