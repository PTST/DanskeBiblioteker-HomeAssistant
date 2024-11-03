import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import Library
from .const import (
    CONF_GET_EREOLEN,
    CONF_GET_RESERVATIONS,
    CONF_MUNICIPALITY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
)
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


class LibraryCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.library = Library(
            municipality=entry.data[CONF_MUNICIPALITY],
            user_id=entry.data[CONF_USERNAME],
            pin=entry.data[CONF_PASSWORD],
            hass=self.hass,
        )
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=DEFAULT_SCAN_INTERVAL
        )

    async def _async_update_data(self) -> dict:
        data = {
            "loans": [],
            "reservations": [],
            "ereolen_loans": [],
            "ereolen_reservations": [],
            "profile_info": None,
        }

        try:
            LOGGER.debug("Updating data")
            tasks = []
            await self.library.authenticate()
            tasks.append(asyncio.get_event_loop().create_task(self.library.get_loans()))
            tasks.append(
                asyncio.get_event_loop().create_task(self.library.get_profile_info())
            )
            if self.entry.data[CONF_GET_RESERVATIONS]:
                tasks.append(
                    asyncio.get_event_loop().create_task(
                        self.library.get_reservations()
                    )
                )
            if self.entry.data[CONF_GET_EREOLEN]:
                tasks.append(
                    asyncio.get_event_loop().create_task(
                        self.library.get_ereolen_loans()
                    )
                )
            if (
                self.entry.data[CONF_GET_EREOLEN]
                and self.entry.data[CONF_GET_RESERVATIONS]
            ):
                tasks.append(
                    asyncio.get_event_loop().create_task(
                        self.library.get_ereolen_reservations()
                    )
                )
            done, _ = await asyncio.wait(tasks, return_when="ALL_COMPLETED")
            for coroutine in done:
                result = coroutine.result()
                if isinstance(result, ProfileInfo):
                    data["profile_info"] = result
                    continue
                if not isinstance(result, list):
                    continue
                if len(result) == 0:
                    continue
                match result[0]:
                    case Loan():
                        data["loans"] = result
                    case Reservation():
                        data["reservations"] = result
                    case EreolenLoan():
                        data["ereolen_loans"] = result
                    case EreolenReservation():
                        data["ereolen_reservations"] = result
                    case _:
                        LOGGER.warning(
                            "%s found in results", result[0].__class__.__name__
                        )

        except Exception as ex:
            LOGGER.exception(ex)
            raise

        return data
