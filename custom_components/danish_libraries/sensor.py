# pylint: disable=line-too-long

import hashlib

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LibraryCoordinator
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LibraryCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors: list[Entity] = [
        LoanSensor(coordinator),
        ReservationSensor(coordinator),
        EreolenLoanSensor(coordinator),
        EreolenReservationSensor(coordinator),
    ]
    async_add_entities(sensors)


class LoanSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator

    @property
    def profile_info(self) -> ProfileInfo:
        return self.coordinator.data["profile_info"]

    @property
    def loans(self) -> list[Loan]:
        return self.coordinator.data["loans"]
    
    @property
    def next_due_loan(self) -> Loan | None:
        if len(self.loans) > 0:
            return min(self.loans, key=lambda x: x.due_date)
        return None

    @property
    def unique_id(self):
        uuid = f"{self.profile_info.patron_id}_library_loans"
        return hashlib.sha1(uuid.encode("utf-8")).hexdigest()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} library loans"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return len(self.loans)

    @property
    def extra_state_attributes(self) -> dict[str, int | float]:
        return {
            "type": "library_loan",
            "next_due_loan": (
                self.next_due_loan.to_json() if self.next_due_loan is not None else None
            ),
            "data": [loan.to_json() for loan in self.loans],
        }


class ReservationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator

    @property
    def profile_info(self) -> ProfileInfo:
        return self.coordinator.data["profile_info"]

    @property
    def reservations(self) -> list[Reservation]:
        return self.coordinator.data["reservations"]
    
    @property
    def ready_for_pickup(self) -> list[Reservation]:
        data = [
            res for res in self.reservations if res.pickup_deadline is not None
        ]
        if len(data) > 0:
            data.sort(key=lambda item: item.pickup_deadline)
        return data
    
    @property
    def in_queue(self) -> list[Reservation]:
        data = [
            res
            for res in self.reservations
            if res.pickup_deadline is None and res.number_in_queue
        ]
        if len(data) > 0:
            data.sort(key=lambda item: item.number_in_queue)
        return data
    
    @property
    def next_in_queue(self) -> Reservation | None:
        if len(self.in_queue) > 0:
            return min(self.in_queue, key=lambda x: x.number_in_queue)
        return None


    @property
    def unique_id(self):
        uuid = f"{self.profile_info.patron_id}_library_reservations"
        return hashlib.sha1(uuid.encode("utf-8")).hexdigest()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} library reservations"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return len(self.ready_for_pickup)

    @property
    def extra_state_attributes(self) -> dict[str, int | float]:
        return {
            "type": "library_reservation",
            "next_in_queue": (
                self.next_in_queue.to_json() if self.next_in_queue else None
            ),
            "data": [res.to_json() for res in self.ready_for_pickup]
            + [res.to_json() for res in self.in_queue],
        }


class EreolenLoanSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
    
    @property
    def profile_info(self) -> ProfileInfo:
        return self.coordinator.data["profile_info"]
    
    @property
    def loans(self) -> list[EreolenLoan]:
        return self.coordinator.data["ereolen_loans"]

    @property
    def next_due_loan(self) -> EreolenLoan | None:
        if len(self.loans) > 0:
            return min(self.loans, key=lambda x: x.due_date)
        return None

    @property
    def unique_id(self):
        uuid = f"{self.profile_info.patron_id}_ereolen_loan"
        return hashlib.sha1(uuid.encode("utf-8")).hexdigest()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} ereolen loans"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return len(self.loans)

    @property
    def extra_state_attributes(self) -> dict[str, int | float]:
        return {
            "type": "ereolen_loan",
            "next_due_loan": (
                self.next_due_loan.to_json() if self.next_due_loan is not None else None
            ),
            "data": [loan.to_json() for loan in self.loans],
        }


class EreolenReservationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator

    @property
    def profile_info(self) -> ProfileInfo:
        return self.coordinator.data["profile_info"]
    
    @property
    def reservations(self) -> list[EreolenReservation]:
        return self.coordinator.data["ereolen_reservations"]

    @property
    def unique_id(self):
        uuid = f"{self.profile_info.patron_id}_ereolen_reservations"
        return hashlib.sha1(uuid.encode("utf-8")).hexdigest()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} ereolen reservations"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return 1

    @property
    def extra_state_attributes(self) -> dict[str, int | float]:
        return {
            "type": "ereolen_reservation",
            "next_in_queue": None,
            "data": [res.to_json() for res in self.reservations],
        }
