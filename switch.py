"""Switch entities for the Heatit WiFi6 Thermostat."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .entity import HeatitEntity


@dataclass(frozen=True, kw_only=True)
class HeatitSwitchEntityDescription(SwitchEntityDescription):
    """Describes one boolean parameter.

    These are written as real JSON booleans. They cannot be sent as query
    parameters, because yarl raises TypeError on a Python bool.
    """

    parameter: str
    # Where the current value lives in the status document, which is not always
    # alongside the parameter name used to write it.
    value_fn: Callable[[dict[str, Any], dict[str, Any]], Any]


SWITCHES: tuple[HeatitSwitchEntityDescription, ...] = (
    HeatitSwitchEntityDescription(
        key="disable_buttons",
        translation_key="disable_buttons",
        parameter="disableButtons",
        value_fn=lambda parameters, _owd: parameters.get("disableButtons"),
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitSwitchEntityDescription(
        key="open_window_detection",
        translation_key="open_window_detection",
        parameter="openWindowDetection",
        # Reported under parameters.OWD, written as a flat parameter.
        value_fn=lambda _parameters, owd: owd.get("openWindowDetection"),
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch entities."""
    async_add_entities(HeatitSwitch(entry, description) for description in SWITCHES)


class HeatitSwitch(HeatitEntity, SwitchEntity):
    """A boolean parameter."""

    entity_description: HeatitSwitchEntityDescription

    def __init__(
        self, entry: HeatitConfigEntry, description: HeatitSwitchEntityDescription
    ) -> None:
        """Initialise the switch."""
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Current value, or None if the device did not report it."""
        value = self.entity_description.value_fn(self._parameters, self._owd)
        return None if value is None else bool(value)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the parameter."""
        await self.async_write_parameters({self.entity_description.parameter: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the parameter."""
        await self.async_write_parameters({self.entity_description.parameter: False})
