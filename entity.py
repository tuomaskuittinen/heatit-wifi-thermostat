"""Shared entity base for the Heatit WiFi6 Thermostat integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HeatitApiError
from .const import CONF_HOST, DOMAIN, MANUFACTURER, MODEL
from .coordinator import HeatitCoordinator

if TYPE_CHECKING:
    from . import HeatitConfigEntry


class HeatitEntity(CoordinatorEntity[HeatitCoordinator]):
    """Base for every Heatit entity.

    Owns the device registry entry so `sw_version`, the MAC connection and the
    Visit link are defined in exactly one place.
    """

    _attr_has_entity_name = True

    def __init__(self, entry: HeatitConfigEntry, key: str) -> None:
        """Bind to the entry's coordinator and register against its device."""
        super().__init__(entry.runtime_data.coordinator)
        self._api = entry.runtime_data.api

        data = self.coordinator.data
        device_id = str(data["id"])
        self._attr_unique_id = f"{device_id}_{key}"

        network = data.get("network") or {}
        connections: set[tuple[str, str]] = set()
        if mac := network.get("mac"):
            connections.add((CONNECTION_NETWORK_MAC, format_mac(mac)))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            connections=connections,
            name=entry.runtime_data.name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=data.get("firmware"),
            serial_number=device_id,
            configuration_url=entry.data[CONF_HOST],
        )

    @property
    def _status(self) -> dict[str, Any]:
        """The whole `/api/status` document."""
        return self.coordinator.data or {}

    @property
    def _parameters(self) -> dict[str, Any]:
        """The `parameters` object from the status document."""
        parameters = self._status.get("parameters")
        return parameters if isinstance(parameters, dict) else {}

    @property
    def _owd(self) -> dict[str, Any]:
        """The `parameters.OWD` object."""
        owd = self._parameters.get("OWD")
        return owd if isinstance(owd, dict) else {}

    async def async_write_parameters(self, values: dict[str, Any]) -> None:
        """Write parameters and reflect the result immediately.

        The requested values are published before the HTTP call. The round trip
        to the thermostat takes ~650 ms, and a UI control that has already moved
        will snap back to the old value if the state does not change within its
        own optimistic window. Publishing first keeps the control steady.

        Raises HomeAssistantError on failure so the UI shows it, rather than
        letting a rejected write disappear into the log.
        """
        self.coordinator.apply_parameter_updates(values)

        try:
            applied = await self._api.set_parameters(values)
        except HeatitApiError as err:
            self.coordinator.discard_pending(values)
            await self.coordinator.async_request_refresh()
            raise HomeAssistantError(
                f"Failed to set {', '.join(values)} on {self.device_name}: {err}"
            ) from err

        # Replace the requested values with what the device says it applied, in
        # case it clamped or rounded anything.
        self.coordinator.apply_parameter_updates(applied)
        # Derived fields such as `state` only change on the next poll.
        await self.coordinator.async_request_refresh()

    @property
    def device_name(self) -> str:
        """Human-readable device name, for error messages."""
        info = self._attr_device_info or {}
        return str(info.get("name") or "thermostat")
