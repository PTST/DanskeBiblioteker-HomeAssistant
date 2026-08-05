# pylint: disable=line-too-long

import hashlib
from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GET_EREOLEN, CONF_GET_RESERVATIONS, DOMAIN, LOGGER
from .coordinator import LibraryCoordinator
from .models import EreolenLoan, EreolenReservation, Loan, ProfileInfo, Reservation


def _async_remove_stale_sensor(
    ent_reg: er.EntityRegistry, patron_id: str, unique_id_suffix: str
) -> None:
    """Remove a previously-registered sensor whose data source is now disabled."""
    uuid = f"{patron_id}_{unique_id_suffix}"
    unique_id = hashlib.sha1(uuid.encode("utf-8")).hexdigest()
    entity_id = ent_reg.async_get_entity_id(SENSOR_DOMAIN, DOMAIN, unique_id)
    if entity_id:
        LOGGER.debug("Removing disabled entity %s", entity_id)
        ent_reg.async_remove(entity_id)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LibraryCoordinator = hass.data[DOMAIN][entry.entry_id]
    patron_id = coordinator.data["profile_info"].patron_id
    ent_reg = er.async_get(hass)

    sensors: list[Entity] = [
        LoanSensor(coordinator),
        CanBeRenewedSensor(coordinator),
    ]

    if entry.data[CONF_GET_RESERVATIONS]:
        sensors.append(ReservationSensor(coordinator))
    else:
        _async_remove_stale_sensor(ent_reg, patron_id, "library_reservations")

    if entry.data[CONF_GET_EREOLEN]:
        sensors.append(EreolenLoanSensor(coordinator))
    else:
        _async_remove_stale_sensor(ent_reg, patron_id, "ereolen_loan")

    if entry.data[CONF_GET_EREOLEN] and entry.data[CONF_GET_RESERVATIONS]:
        sensors.append(EreolenReservationSensor(coordinator))
    else:
        _async_remove_stale_sensor(ent_reg, patron_id, "ereolen_reservations")

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
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "type": "library_loan",
            "next_due_loan": (
                self.next_due_loan.to_json() if self.next_due_loan is not None else None
            ),
            "data": [loan.to_json() for loan in self.loans],
        }


class CanBeRenewedSensor(LoanSensor):
    @property
    def unique_id(self):
        uuid = f"{self.profile_info.patron_id}_library_loans_can_be_renewed"
        return hashlib.sha1(uuid.encode("utf-8")).hexdigest()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} library loans that can be renewed"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return len([loan for loan in self.loans if loan.is_renewable])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "type": "library_loan_renewable",
            "data": [loan.to_json() for loan in self.loans if loan.is_renewable],
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
        data = [res for res in self.reservations if res.pickup_deadline is not None]
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
    def next_expected_available(self) -> EreolenReservation | None:
        dated = [
            res for res in self.reservations if res.expected_availble_date is not None
        ]
        if len(dated) > 0:
            return min(dated, key=lambda res: res.expected_availble_date)
        return None

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
        return len(self.reservations)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "type": "ereolen_reservation",
            "next_expected_available": (
                self.next_expected_available.to_json()
                if self.next_expected_available is not None
                else None
            ),
            "data": [res.to_json() for res in self.reservations],
        }
