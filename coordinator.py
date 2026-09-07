"""Polling coordinator for a single Heatit WiFi6 thermostat."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HeatitApiError, HeatitThermostatAPI
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

# The device acknowledges a write in ~200 ms and echoes the value it applied,
# but /api/status keeps serving the old value for a while afterwards. Measured
# on firmware 2.26: ~3.2 s for standbyDisplayBrightness, ~8.5 s for
# operatingMode. Without this hold, the refresh that follows a write reads stale
# data and clobbers the value the device just confirmed.
#
# The hold is released as soon as the device reports the value back, so a
# generous TTL costs nothing in the normal case - it only bounds how long a
# write the device silently ignored stays visible.
PENDING_WRITE_TTL = 30.0

# Parameters that are written flat but reported nested under parameters.OWD.
_OWD_PARAMETERS = frozenset({"openWindowDetection"})


class HeatitCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch `/api/status` on an interval and share it with every platform."""

    def __init__(
        self, hass: HomeAssistant, api: HeatitThermostatAPI, name: str
    ) -> None:
        """Set up the coordinator for one device."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {name}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.api = api
        # parameter -> (confirmed value, monotonic expiry)
        self._pending: dict[str, tuple[Any, float]] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the thermostat."""
        try:
            data = await self.api.get_status()
        except HeatitApiError as err:
            raise UpdateFailed(str(err)) from err

        if "id" not in data:
            raise UpdateFailed(f"Status response has no device id: {data}")

        self._reconcile_pending(data)
        return data

    @staticmethod
    def _container(parameters: dict[str, Any], key: str) -> dict[str, Any] | None:
        """Return the dict inside the status document that holds `key`."""
        if key in _OWD_PARAMETERS:
            owd = parameters.get("OWD")
            return owd if isinstance(owd, dict) else None
        return parameters

    def _reconcile_pending(self, data: dict[str, Any]) -> None:
        """Re-apply confirmed writes the device has not caught up with yet.

        A pending value is dropped as soon as the device reports it back, or
        once it expires, so a write the device silently ignored self-heals
        instead of being masked forever.
        """
        if not self._pending:
            return

        parameters = data.get("parameters")
        if not isinstance(parameters, dict):
            return

        now = time.monotonic()
        for key, (value, expiry) in list(self._pending.items()):
            container = self._container(parameters, key)
            if container is None:
                continue
            if container.get(key) == value:
                del self._pending[key]  # device agrees, nothing to hold
            elif now >= expiry:
                del self._pending[key]  # give up and accept what the device says
                _LOGGER.debug(
                    "%s: device never reported %s=%r, accepting %r",
                    self.name, key, value, container.get(key),
                )
            else:
                container[key] = value

    def discard_pending(self, keys: Any) -> None:
        """Forget held values for `keys` and restore what the device last said.

        Used when a write fails, so a value that was published ahead of the HTTP
        call is not left standing.
        """
        for key in keys:
            self._pending.pop(key, None)

    def apply_parameter_updates(self, applied: dict[str, Any]) -> None:
        """Merge values the device confirmed it applied into the cached status.

        Called straight after a successful write so entities reflect the change
        immediately instead of waiting up to a full poll interval. Only values
        the device echoed back are merged, so this is confirmation rather than
        an optimistic guess.
        """
        if not applied:
            return

        expiry = time.monotonic() + PENDING_WRITE_TTL
        for key, value in applied.items():
            self._pending[key] = (value, expiry)

        if not self.data:
            return
        parameters = self.data.get("parameters")
        if not isinstance(parameters, dict):
            return

        for key, value in applied.items():
            container = self._container(parameters, key)
            if container is not None:
                container[key] = value

        self.async_update_listeners()
