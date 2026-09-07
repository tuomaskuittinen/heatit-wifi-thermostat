"""HTTP client for the Heatit WiFi6 thermostat local API.

Deliberately free of Home Assistant imports so it can be exercised on its own.
The session is injected; this class never creates or owns one.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_TIMEOUT, CONFIRM_PHRASE

_LOGGER = logging.getLogger(__name__)


class HeatitApiError(Exception):
    """Raised when the thermostat cannot be reached or returns an error."""


class HeatitThermostatAPI:
    """Client for a single thermostat."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialise the client against `host` using an existing session."""
        self.host = host.rstrip("/")
        self._session = session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform one request and return the decoded JSON body."""
        url = f"{self.host}{path}"
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with self._session.request(
                    method, url, json=json_body, params=params
                ) as response:
                    response.raise_for_status()
                    # The device's Content-Type header is not reliable across
                    # firmware versions, so skip aiohttp's check.
                    data = await response.json(content_type=None)
        except TimeoutError as err:
            raise HeatitApiError(f"Timeout talking to {url}") from err
        except aiohttp.ClientError as err:
            raise HeatitApiError(f"Error talking to {url}: {err}") from err
        except ValueError as err:  # malformed JSON
            raise HeatitApiError(f"Invalid JSON from {url}: {err}") from err

        if not isinstance(data, dict):
            raise HeatitApiError(f"Unexpected response from {url}: {data!r}")

        _LOGGER.debug("%s %s -> %s", method, url, data)
        return data

    async def get_status(self) -> dict[str, Any]:
        """Return the full `/api/status` document."""
        return await self._request("GET", "/api/status")

    async def set_parameters(self, values: dict[str, Any]) -> dict[str, Any]:
        """Write one or more parameters.

        Sent as a JSON body. Query parameters are not usable here, because yarl
        raises TypeError on a Python bool, so every boolean setting would fail.

        Firmware 2.26 echoes the values it actually applied alongside its status,
        e.g. {"status": "Success", "temperatureDisplay": true}. Only the echoed
        keys are returned, so callers can trust them rather than assuming the
        write took effect.
        """
        if not values:
            return {}

        data = await self.set_parameters_raw(values)
        return {key: data[key] for key in values if key in data}

    async def set_parameters_raw(self, values: dict[str, Any]) -> dict[str, Any]:
        """Write parameters and return the response body unfiltered."""
        data = await self._request("POST", "/api/parameters", json_body=values)
        if str(data.get("status", "")).lower() not in ("success", ""):
            raise HeatitApiError(f"Thermostat rejected {values}: {data}")
        return data

    async def set_parameter(self, parameter: str, value: Any) -> dict[str, Any]:
        """Write a single parameter. Convenience wrapper around set_parameters."""
        return await self.set_parameters({parameter: value})

    async def _reset(self, kind: str) -> dict[str, Any]:
        """Call one of the /api/reset/* endpoints."""
        return await self._request(
            "DELETE", f"/api/reset/{kind}", params={"reset": CONFIRM_PHRASE}
        )

    async def reset_kwh(self) -> dict[str, Any]:
        """Zero the energy meter."""
        return await self._reset("kwh")

    async def reset_settings(self) -> dict[str, Any]:
        """Reset device settings to factory defaults. Keeps WiFi credentials."""
        return await self._reset("settings")

    async def reset_factory(self) -> dict[str, Any]:
        """Full factory reset. Wipes WiFi credentials; needs physical re-onboarding."""
        return await self._reset("factory")
