"""Config flow for the Heatit WiFi6 Thermostat integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatitApiError, HeatitThermostatAPI
from .const import CONF_HOST, CONF_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME, default=""): str,
    }
)

# The device's own `name` is a MyHeatit app field: often blank, space-stripped
# when set, and cleared by manufacturer OTA updates. Treat it as unnamed.
_PLACEHOLDER_NAME_PREFIX = "Thermostat_"


def normalize_host(host: str) -> str:
    """Ensure the host carries an explicit scheme."""
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host


class HeatitWiFiThermostatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for a single thermostat."""

    VERSION = 1

    async def _async_probe(self, host: str) -> dict[str, Any]:
        """Contact the thermostat and return its status document."""
        api = HeatitThermostatAPI(host, async_get_clientsession(self.hass))
        return await api.get_status()

    @staticmethod
    def _suggested_name(status: dict[str, Any]) -> str:
        """Pick a fallback name when the user leaves the name field blank."""
        name = str(status.get("name") or "").strip()
        if not name or name.startswith(_PLACEHOLDER_NAME_PREFIX):
            return "Heatit Thermostat"
        return name

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a thermostat by host, with an optional friendly name."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = normalize_host(user_input[CONF_HOST])
            try:
                status = await self._async_probe(host)
            except HeatitApiError as err:
                _LOGGER.debug("Cannot connect to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surfaced to the user as "unknown"
                _LOGGER.exception("Unexpected error connecting to %s", host)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(status["id"]))
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                name = (user_input.get(CONF_NAME) or "").strip()
                if not name:
                    name = self._suggested_name(status)

                return self.async_create_entry(
                    title=name,
                    data={CONF_HOST: host, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the host or name of an existing thermostat.

        Lets a DHCP change be fixed without deleting the entry and losing every
        entity and its history.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = normalize_host(user_input[CONF_HOST])
            try:
                status = await self._async_probe(host)
            except HeatitApiError as err:
                _LOGGER.debug("Cannot connect to %s: %s", host, err)
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error connecting to %s", host)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(status["id"]))
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                name = (user_input.get(CONF_NAME) or "").strip() or entry.title
                return self.async_update_reload_and_abort(
                    entry,
                    title=name,
                    data_updates={CONF_HOST: host, CONF_NAME: name},
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA,
                user_input
                or {
                    CONF_HOST: entry.data.get(CONF_HOST, ""),
                    CONF_NAME: entry.data.get(CONF_NAME, entry.title),
                },
            ),
            errors=errors,
        )
