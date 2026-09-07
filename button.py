"""Button entities for the Heatit WiFi6 Thermostat.

The full factory reset is deliberately not here. It erases the WiFi credentials,
so the device leaves the network and needs the MyHeatit app plus physical access
to come back. It is exposed as the `heatit_wifi_thermostat.factory_reset` action,
which requires a typed confirmation.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .api import HeatitApiError, HeatitThermostatAPI
from .entity import HeatitEntity


@dataclass(frozen=True, kw_only=True)
class HeatitButtonEntityDescription(ButtonEntityDescription):
    """Describes one button."""

    press_fn: Callable[[HeatitThermostatAPI], Awaitable[dict]]


BUTTONS: tuple[HeatitButtonEntityDescription, ...] = (
    HeatitButtonEntityDescription(
        key="reset_energy_meter",
        translation_key="reset_energy_meter",
        press_fn=lambda api: api.reset_kwh(),
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitButtonEntityDescription(
        key="reset_settings",
        translation_key="reset_settings",
        press_fn=lambda api: api.reset_settings(),
        entity_category=EntityCategory.CONFIG,
        # Returns every parameter to its factory default, including sensorMode.
        # Keeps WiFi credentials. Off by default so it cannot be hit by accident.
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button entities."""
    async_add_entities(HeatitButton(entry, description) for description in BUTTONS)


class HeatitButton(HeatitEntity, ButtonEntity):
    """A one-shot action on the thermostat."""

    entity_description: HeatitButtonEntityDescription

    def __init__(
        self, entry: HeatitConfigEntry, description: HeatitButtonEntityDescription
    ) -> None:
        """Initialise the button."""
        super().__init__(entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Run the action and refresh."""
        try:
            await self.entity_description.press_fn(self._api)
        except HeatitApiError as err:
            raise HomeAssistantError(
                f"{self.entity_description.key} failed on {self.device_name}: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
