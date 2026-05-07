import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry

from .const import DOMAIN, LOGGER
from .coordinator import LibraryCoordinator

PLATFORMS = [
    SENSOR_DOMAIN,
]

CONFIG_SCHEMA = cv.deprecated(DOMAIN)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = LibraryCoordinator(hass, entry=entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up all platforms for this device/entry.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
        LOGGER.debug("config options were changed")
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    # Register services
    async def async_renew_loan(call):
        loan_id = call.data.get("loan_id")
        target = call.data.get("target")

        # Handle target as either string (entity_id) or dict
        if isinstance(target, str):
            entity_id = target
        elif isinstance(target, dict):
            entity_ids = target.get("entity_id", [])
            if isinstance(entity_ids, list):
                entity_id = entity_ids[0] if entity_ids else None
            else:
                entity_id = entity_ids
        else:
            entity_id = None

        if not entity_id:
            LOGGER.error("No entity selected")
            return

        # Get entry_id from the entity's registry
        ent_registry = entity_registry.async_get(hass)
        ent = ent_registry.entities.get(entity_id)

        if not ent or ent.platform != DOMAIN:
            LOGGER.error("Entity %s not found or not from this integration", entity_id)
            return

        entry_id = ent.config_entry_id
        coordinator: LibraryCoordinator = hass.data[DOMAIN][entry_id]
        loan = None

        # Find the loan in the coordinator's data
        for item in coordinator.data.get("loans", []):
            if str(item.loan_id) == loan_id:
                loan = item
                break

        if loan is None:
            LOGGER.error("Loan with ID %s not found", str(loan_id))
            raise ValueError(f"Loan {loan_id} not found")

        try:
            await coordinator.library.renew_loan([loan])
            LOGGER.info("Successfully renewed loan %s", str(loan_id))
            await coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Failed to renew loan", exc_info=True)
            raise e

    async def async_renew_all_loans(call):
        target = call.data.get("target")

        # Handle target as either string (entity_id) or dict
        if isinstance(target, str):
            entity_id = target
        elif isinstance(target, dict):
            entity_ids = target.get("entity_id", [])
            if isinstance(entity_ids, list):
                entity_id = entity_ids[0] if entity_ids else None
            else:
                entity_id = entity_ids
        else:
            entity_id = None

        if not entity_id:
            LOGGER.error("No entity selected")
            return

        # Get entry_id from the entity's registry
        ent_registry = entity_registry.async_get(hass)
        ent = ent_registry.entities.get(entity_id)

        if not ent or ent.platform != DOMAIN:
            LOGGER.error("Entity %s not found or not from this integration", entity_id)
            return

        entry_id = ent.config_entry_id
        coordinator: LibraryCoordinator = hass.data[DOMAIN][entry_id]
        loans_to_renew = [
            loan for loan in coordinator.data.get("loans", []) if loan.is_renewable
        ]

        if not loans_to_renew:
            LOGGER.info("No loans to renew")
            return

        try:
            await coordinator.library.renew_loan(loans_to_renew)
            LOGGER.info("Successfully renewed %d loans", len(loans_to_renew))
            await coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Failed to renew loans", exc_info=True)
            raise e

    renew_loan_schema = vol.Schema(
        {
            vol.Required("loan_id"): cv.string,
            vol.Optional("target"): vol.Any(
                cv.string,
                {
                    vol.Optional("entity_id"): vol.Any([cv.string], cv.string),
                },
            ),
        }
    )

    renew_all_loans_schema = vol.Schema(
        {
            vol.Optional("target"): vol.Any(
                cv.string,
                {
                    vol.Optional("entity_id"): vol.Any([cv.string], cv.string),
                },
            ),
        }
    )

    hass.services.async_register(
        DOMAIN,
        "renew_loan",
        async_renew_loan,
        renew_loan_schema,
    )

    hass.services.async_register(
        DOMAIN,
        "renew_all_loans",
        async_renew_all_loans,
        renew_all_loans_schema,
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    del hass.data[DOMAIN][entry.entry_id]

    if not hass.data[DOMAIN]:
        del hass.data[DOMAIN]

    return True
