import pytest
import asyncio
from custom_components.danish_libraries.api import Library
import dotenv
import os

dotenv.load_dotenv()

async def test_auth():
    user = os.getenv('LIBRARY_USER_ID')
    pin = os.getenv('LIBRARY_PIN')
    lib = Library("Aalborg", user, pin)
    await lib.authenticate()
    assert lib.user_bearer_token != None

async def test_loans():
    user = os.getenv('LIBRARY_USER_ID')
    pin = os.getenv('LIBRARY_PIN')
    lib = Library("Aalborg", user, pin)
    loans = await lib.get_loans()
    assert loans != None
    assert len(loans) > 0

async def test_reservations():
    user = os.getenv('LIBRARY_USER_ID')
    pin = os.getenv('LIBRARY_PIN')
    lib = Library("Aalborg", user, pin)
    reservations = await lib.get_reservations()
    assert reservations != None
    assert len(reservations) > 0