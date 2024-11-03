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
        self.profile_info: ProfileInfo = coordinator.data["profile_info"]
        self.loans: list[Loan] = coordinator.data["loans"]
        self.next_due_loan = (
            min(self.loans, key=lambda x: x.due_date) if len(self.loans) > 0 else None
        )

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
            "next_due_loan": (
                self.next_due_loan.to_json() if self.next_due_loan is not None else None
            ),
            "data": [loan.to_json() for loan in self.loans],
        }


class ReservationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.profile_info: ProfileInfo = coordinator.data["profile_info"]
        self.reservations: list[Reservation] = coordinator.data["reservations"]
        self.next_in_queue: Reservation = None
        self.ready_for_pickup = [
            res for res in self.reservations if res.pickup_deadline is not None
        ]
        if len(self.ready_for_pickup) > 0:
            self.ready_for_pickup.sort(key=lambda item: item.pickup_deadline)
        self.in_queue = [
            res
            for res in self.reservations
            if res.pickup_deadline is None and res.number_in_queue
        ]
        if len(self.in_queue) > 0:
            self.in_queue.sort(key=lambda item: item.number_in_queue)
            self.next_in_queue = min(self.in_queue, key=lambda x: x.number_in_queue)

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
        self.profile_info: ProfileInfo = coordinator.data["profile_info"]
        self.loans: list[EreolenLoan] = coordinator.data["ereolen_loans"]
        self.next_due_loan = (
            min(self.loans, key=lambda x: x.due_date) if len(self.loans) > 0 else None
        )

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
            "next_due_loan": (
                self.next_due_loan.to_json() if self.next_due_loan is not None else None
            ),
            "data": [loan.to_json() for loan in self.loans],
        }


class EreolenReservationSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator: LibraryCoordinator):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.profile_info: ProfileInfo = coordinator.data["profile_info"]
        self.reservations: list[EreolenReservation] = coordinator.data[
            "ereolen_reservations"
        ]

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
            "next_in_queue": None,
            "data": [res.to_json() for res in self.reservations],
        }
