"""Select entities for the Heatit WiFi6 Thermostat."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .const import (
    REGULATION_MODE_OPTIONS,
    SENSOR_MODE_OPTIONS,
    SENSOR_RESISTANCE_OPTIONS,
    TEMPERATURE_DISPLAY_OPTIONS,
)
from .entity import HeatitEntity


@dataclass(frozen=True, kw_only=True)
class HeatitSelectEntityDescription(SelectEntityDescription):
    """Describes one enumerated parameter."""

    parameter: str
    # Wire value -> label. Keys are ints or bools depending on the parameter;
    # both serialise correctly in a JSON body.
    choices: dict[Any, str] = field(default_factory=dict)


SELECTS: tuple[HeatitSelectEntityDescription, ...] = (
    HeatitSelectEntityDescription(
        key="sensor_mode",
        translation_key="sensor_mode",
        parameter="sensorMode",
        choices=SENSOR_MODE_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitSelectEntityDescription(
        key="regulation_mode",
        translation_key="regulation_mode",
        parameter="regulationMode",
        choices=REGULATION_MODE_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitSelectEntityDescription(
        key="temperature_display",
        translation_key="temperature_display",
        parameter="temperatureDisplay",
        choices=TEMPERATURE_DISPLAY_OPTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitSelectEntityDescription(
        key="sensor_resistance",
        translation_key="sensor_resistance",
        parameter="sensorValue",
        choices=SENSOR_RESISTANCE_OPTIONS,
        entity_category=EntityCategory.CONFIG,
        # Commissioning setting: the NTC curve is fixed by the sensor that was
        # physically installed. A wrong value makes the device misread the floor.
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities."""
    async_add_entities(HeatitSelect(entry, description) for description in SELECTS)


class HeatitSelect(HeatitEntity, SelectEntity):
    """An enumerated parameter."""

    entity_description: HeatitSelectEntityDescription

    def __init__(
        self, entry: HeatitConfigEntry, description: HeatitSelectEntityDescription
    ) -> None:
        """Initialise the select."""
        super().__init__(entry, description.key)
        self.entity_description = description
        self._attr_options = list(description.choices.values())
        self._reverse = {label: value for value, label in description.choices.items()}

    @property
    def current_option(self) -> str | None:
        """Label for the value the device currently reports."""
        value = self._parameters.get(self.entity_description.parameter)
        return self.entity_description.choices.get(value)

    async def async_select_option(self, option: str) -> None:
        """Write the value behind the chosen label."""
        if option not in self._reverse:
            raise ServiceValidationError(
                f"{option!r} is not a valid option for {self.entity_id}"
            )
        await self.async_write_parameters(
            {self.entity_description.parameter: self._reverse[option]}
        )
