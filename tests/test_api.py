# import sys
# import pathlib
# path = str(pathlib.Path(__file__).parent.parent.joinpath('custom_components').joinpath("danish_libraries").resolve())
# sys.path.insert(0, path)

import asyncio
import os

import dotenv
import pytest

from custom_components.danish_libraries.api import Library
from custom_components.danish_libraries.models import (
    EreolenLoan,
    EreolenReservation,
    LibraryConfig,
    Loan,
    ProfileInfo,
    Reservation,
)

dotenv.load_dotenv()


async def test_auth():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    await lib.authenticate()
    assert lib.user_bearer_token != None


async def test_loans():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    loans = await lib.get_loans()
    assert loans != None
    assert len(loans) > 0
    assert isinstance(loans[0], Loan)


async def test_reservations():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    reservations = await lib.get_reservations()
    assert reservations != None
    assert len(reservations) > 0
    assert isinstance(reservations[0], Reservation)


async def test_profile():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    profile = await lib.get_profile_info()
    assert profile != None
    assert isinstance(profile, ProfileInfo)
    assert "gmail.com" in profile.email_address


async def test_ereolen_loans():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    loans = await lib.get_ereolen_loans()
    assert loans != None
    assert len(loans) > 0
    assert isinstance(loans[0], EreolenLoan)


async def test_ereolen_reservations():
    user = os.getenv("LIBRARY_USER_ID")
    pin = os.getenv("LIBRARY_PIN")
    lib = Library(os.getenv("MUNICIPALITY"), user, pin)
    reservations = await lib.get_ereolen_reservations()
    assert reservations != None
    assert len(reservations) > 0
    assert isinstance(reservations[0], EreolenReservation)
