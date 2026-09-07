"""Diagnostics support for the Heatit WiFi6 Thermostat integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import HeatitConfigEntry
from .const import CONF_HOST

TO_REDACT = {"mac", "SSID", "ipAddress", CONF_HOST, "id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HeatitConfigEntry
) -> dict[str, Any]:
    """Return the raw status document plus entry metadata."""
    coordinator = entry.runtime_data.coordinator
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "unique_id_set": entry.unique_id is not None,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": (
                coordinator.update_interval.total_seconds()
                if coordinator.update_interval
                else None
            ),
        },
        "status": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
