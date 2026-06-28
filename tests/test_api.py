import importlib
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS_ROOT = ROOT / "custom_components"
DANISH_LIBRARIES_ROOT = CUSTOM_COMPONENTS_ROOT / "danish_libraries"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def ensure_package(name: str, path: Path) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    return module


ensure_package("custom_components", CUSTOM_COMPONENTS_ROOT)
ensure_package("custom_components.danish_libraries", DANISH_LIBRARIES_ROOT)

api_module = importlib.import_module("custom_components.danish_libraries.api")
models_module = importlib.import_module("custom_components.danish_libraries.models")

Library = api_module.Library
EreolenLoan = models_module.EreolenLoan
EreolenReservation = models_module.EreolenReservation
LibraryConfig = models_module.LibraryConfig
Loan = models_module.Loan
ProfileInfo = models_module.ProfileInfo
Reservation = models_module.Reservation

import dotenv
import pytest

dotenv.load_dotenv()


async def test_auth():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin, None)
    await lib.authenticate()
    assert lib.user_bearer_token != None


async def test_loans():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin, None)
    loans = await lib.get_loans()
    assert loans != None
    assert len(loans) > 0
    assert isinstance(loans[0], Loan)
    assert loans[0].title != None
    assert loans[0].author != None
    assert loans[0].image_url != None
    assert "wikimedia" not in loans[0].image_url


async def test_reservations():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    municipality = os.getenv("MUNICIPALITY")
    lib = Library(municipality, user, pin, None)
    reservations : list[Reservation] = await lib.get_reservations()
    assert reservations != None
    assert len(reservations) > 0
    assert isinstance(reservations[0], Reservation)
    assert reservations[0].title != None
    assert reservations[0].author != None
    assert reservations[0].image_url != None
    assert "wikimedia" not in reservations[0].image_url


async def test_profile():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin, None)
    profile = await lib.get_profile_info()
    assert profile != None
    assert isinstance(profile, ProfileInfo)
    assert "gmail.com" in profile.email_address


async def test_ereolen_loans():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin, None)
    loans = await lib.get_ereolen_loans()
    assert loans != None
    assert len(loans) > 0
    assert isinstance(loans[0], EreolenLoan)


async def test_ereolen_reservations():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin, None)
    reservations = await lib.get_ereolen_reservations()
    assert reservations != None
    assert len(reservations) > 0
    assert isinstance(reservations[0], EreolenReservation)
