from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LibraryCoordinator
from .models import Loan, ProfileInfo


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: LibraryCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors: list[Entity] = [
        LoanSensor(
            coordinator, coordinator.data["loans"], coordinator.data["profile_info"]
        )
    ]
    async_add_entities(sensors)


class LoanSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: LibraryCoordinator,
        loans: list[Loan],
        profile_info: ProfileInfo,
    ):
        super().__init__(coordinator)
        self.profile_info = profile_info
        self._attr_unique_id = f"{self.profile_info.camel_cased_name}_library_loans"
        self.loans = loans
        self.next_due_loan = min(self.loans, key=lambda x: x.loan_expire_date)

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.profile_info.name} loans"

    @property
    def native_value(self) -> int | float | None:
        """Return the state of the entity."""
        return len(self.loans)

    @property
    def extra_state_attributes(self) -> dict[str, int | float]:
        return {
            "next_due_loan": self.next_due_loan.to_json(),
            "data": [loan.to_json() for loan in self.loans],
        }
