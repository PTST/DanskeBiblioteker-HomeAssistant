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


def _resolve_entity_ids(target) -> list[str]:
    """Normalize a service call's `target` field into a list of entity_ids."""
    if isinstance(target, str):
        return [target]
    if isinstance(target, dict):
        entity_ids = target.get("entity_id", [])
        if isinstance(entity_ids, list):
            return list(entity_ids)
        if entity_ids:
            return [entity_ids]
    return []


def _resolve_coordinators(hass: HomeAssistant, target) -> list[LibraryCoordinator]:
    """Resolve a service call's `target` field into the coordinators it refers to."""
    entity_ids = _resolve_entity_ids(target)
    if not entity_ids:
        LOGGER.error("No entity selected")
        return []

    ent_registry = entity_registry.async_get(hass)
    entry_ids: list[str] = []
    for entity_id in entity_ids:
        ent = ent_registry.entities.get(entity_id)
        if not ent or ent.platform != DOMAIN:
            LOGGER.error("Entity %s not found or not from this integration", entity_id)
            continue
        if ent.config_entry_id not in entry_ids:
            entry_ids.append(ent.config_entry_id)

    return [hass.data[DOMAIN][entry_id] for entry_id in entry_ids]


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
        coordinators = _resolve_coordinators(hass, call.data.get("target"))
        if not coordinators:
            return

        found = False
        for coordinator in coordinators:
            loan = next(
                (
                    item
                    for item in coordinator.data.get("loans", [])
                    if str(item.loan_id) == loan_id
                ),
                None,
            )
            if loan is None:
                continue
            found = True
            try:
                await coordinator.library.renew_loan([loan])
                LOGGER.info("Successfully renewed loan %s", str(loan_id))
                await coordinator.async_request_refresh()
            except Exception:
                LOGGER.error("Failed to renew loan", exc_info=True)
                raise

        if not found:
            LOGGER.error("Loan with ID %s not found", str(loan_id))
            raise ValueError(f"Loan {loan_id} not found")

    async def async_renew_all_loans(call):
        coordinators = _resolve_coordinators(hass, call.data.get("target"))
        if not coordinators:
            return

        for coordinator in coordinators:
            loans_to_renew = [
                loan for loan in coordinator.data.get("loans", []) if loan.is_renewable
            ]

            if not loans_to_renew:
                LOGGER.info("No loans to renew")
                continue

            try:
                await coordinator.library.renew_loan(loans_to_renew)
                LOGGER.info("Successfully renewed %d loans", len(loans_to_renew))
                await coordinator.async_request_refresh()
            except Exception:
                LOGGER.error("Failed to renew loans", exc_info=True)
                raise

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
