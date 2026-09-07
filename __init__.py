"""The Heatit WiFi6 Thermostat integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatitApiError, HeatitThermostatAPI
from .const import (
    ATTR_CONFIRM,
    CONF_HOST,
    CONF_NAME,
    CONFIRM_PHRASE,
    DOMAIN,
    SERVICE_FACTORY_RESET,
)
from .coordinator import HeatitCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

ATTR_DEVICE_ID = "device_id"

FACTORY_RESET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_CONFIRM): vol.In([CONFIRM_PHRASE]),
    }
)


@dataclass
class HeatitRuntimeData:
    """Everything the platforms need for one thermostat."""

    coordinator: HeatitCoordinator
    api: HeatitThermostatAPI
    name: str


type HeatitConfigEntry = ConfigEntry[HeatitRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: HeatitConfigEntry) -> bool:
    """Set up one thermostat from a config entry."""
    host = entry.data[CONF_HOST]
    name = entry.data.get(CONF_NAME) or entry.title

    api = HeatitThermostatAPI(host, async_get_clientsession(hass))
    coordinator = HeatitCoordinator(hass, api, name)

    # Raises ConfigEntryNotReady on failure, so HA retries with backoff rather
    # than the entry failing outright when several devices start at once.
    await coordinator.async_config_entry_first_refresh()

    # Backfill a missing unique ID from the device so duplicate detection works.
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=str(coordinator.data["id"])
        )

    entry.runtime_data = HeatitRuntimeData(coordinator=coordinator, api=api, name=name)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HeatitConfigEntry) -> bool:
    """Unload a config entry. The aiohttp session is shared and not ours to close."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: HeatitConfigEntry) -> None:
    """Reload when the entry is reconfigured."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_FACTORY_RESET):
        return

    async def _handle_factory_reset(call: ServiceCall) -> None:
        """Full factory reset of one thermostat.

        Deliberately a service rather than a button entity: this wipes the WiFi
        credentials, so the device drops off the network and has to be
        re-onboarded through the MyHeatit app with physical access.
        """
        device_id = call.data[ATTR_DEVICE_ID]
        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Unknown device id {device_id}")

        entry = next(
            (
                candidate
                for candidate in hass.config_entries.async_entries(DOMAIN)
                if candidate.entry_id in device.config_entries
            ),
            None,
        )
        if entry is None or not hasattr(entry, "runtime_data"):
            raise ServiceValidationError(
                f"Device {device_id} is not a loaded Heatit thermostat"
            )

        _LOGGER.warning(
            "Factory resetting %s - WiFi credentials will be erased", entry.title
        )
        try:
            await entry.runtime_data.api.reset_factory()
        except HeatitApiError as err:
            raise HomeAssistantError(f"Factory reset failed: {err}") from err

    hass.services.async_register(
        DOMAIN, SERVICE_FACTORY_RESET, _handle_factory_reset, FACTORY_RESET_SCHEMA
    )
