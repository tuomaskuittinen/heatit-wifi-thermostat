"""Number entities for the Heatit WiFi6 Thermostat.

Every writable numeric parameter from the WiFi6 API v7 spec, with the spec's own
minimum, maximum and step.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .const import (
    ACTION_AFTER_ERROR_MAX,
    ACTION_AFTER_ERROR_MIN_DELAY,
    BRIGHTNESS_MAX,
    BRIGHTNESS_MIN,
    CALIBRATION_MAX,
    CALIBRATION_MIN,
    CALIBRATION_STEP,
    HYSTERESIS_MAX,
    HYSTERESIS_MIN,
    HYSTERESIS_STEP,
    POWER_REGULATOR_MAX,
    POWER_REGULATOR_MIN,
    SIZE_OF_LOAD_INCREMENT,
    SIZE_OF_LOAD_MAX_WATTS,
    TEMP_MAX,
    TEMP_MIN,
    TEMP_STEP,
)
from .entity import HeatitEntity


def _clamp_action_after_error(value: float) -> float:
    """Snap the illegal 1-9 second window up to the minimum legal delay.

    The API accepts 0 (stay off and show an error) or 10-65535 seconds. A number
    entity cannot express that gap, and the UI slider is not the only way in, so
    the clamp lives here rather than in the schema.
    """
    if 0 < value < ACTION_AFTER_ERROR_MIN_DELAY:
        return float(ACTION_AFTER_ERROR_MIN_DELAY)
    return value


@dataclass(frozen=True, kw_only=True)
class HeatitNumberEntityDescription(NumberEntityDescription):
    """Describes one writable numeric parameter."""

    parameter: str
    # Displayed value = wire value * scale. Lets sizeOfLoad be shown in watts
    # and the power regulator duty cycle in percent.
    scale: float = 1.0
    coerce: Callable[[float], Any] = float
    clamp_fn: Callable[[float], float] | None = None


def _setpoint(key: str, parameter: str) -> HeatitNumberEntityDescription:
    """Build one of the three mode setpoints."""
    return HeatitNumberEntityDescription(
        key=key,
        translation_key=key,
        parameter=parameter,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=TEMP_STEP,
        entity_category=EntityCategory.CONFIG,
    )


def _limit(key: str, parameter: str, enabled: bool) -> HeatitNumberEntityDescription:
    """Build one of the six min/max temperature limits."""
    return HeatitNumberEntityDescription(
        key=key,
        translation_key=key,
        parameter=parameter,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=TEMP_STEP,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
    )


def _calibration(key: str, parameter: str, enabled: bool) -> HeatitNumberEntityDescription:
    """Build one of the three sensor calibrations."""
    return HeatitNumberEntityDescription(
        key=key,
        translation_key=key,
        parameter=parameter,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=CALIBRATION_MIN,
        native_max_value=CALIBRATION_MAX,
        native_step=CALIBRATION_STEP,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=enabled,
    )


NUMBERS: tuple[HeatitNumberEntityDescription, ...] = (
    _setpoint("heating_setpoint", "heatingSetpoint"),
    _setpoint("cooling_setpoint", "coolingSetpoint"),
    _setpoint("eco_setpoint", "ecoSetpoint"),
    _limit("internal_minimum_temperature", "internalMinimumTemperatureLimit", True),
    _limit("internal_maximum_temperature", "internalMaximumTemperatureLimit", True),
    _limit("floor_minimum_temperature", "floorMinimumTemperatureLimit", True),
    _limit("floor_maximum_temperature", "floorMaximumTemperatureLimit", True),
    _limit("external_minimum_temperature", "externalMinimumTemperatureLimit", False),
    _limit("external_maximum_temperature", "externalMaximumTemperatureLimit", False),
    _calibration("internal_calibration", "internalCalibration", True),
    _calibration("floor_calibration", "floorCalibration", True),
    _calibration("external_calibration", "externalCalibration", False),
    HeatitNumberEntityDescription(
        key="temperature_control_hysteresis",
        translation_key="temperature_control_hysteresis",
        parameter="temperatureControlHysteresis",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=HYSTERESIS_MIN,
        native_max_value=HYSTERESIS_MAX,
        native_step=HYSTERESIS_STEP,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitNumberEntityDescription(
        key="active_display_brightness",
        translation_key="active_display_brightness",
        parameter="activeDisplayBrightness",
        native_min_value=BRIGHTNESS_MIN,
        native_max_value=BRIGHTNESS_MAX,
        native_step=1,
        coerce=round,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitNumberEntityDescription(
        key="standby_display_brightness",
        translation_key="standby_display_brightness",
        parameter="standbyDisplayBrightness",
        native_min_value=BRIGHTNESS_MIN,
        native_max_value=BRIGHTNESS_MAX,
        native_step=1,
        coerce=round,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitNumberEntityDescription(
        key="size_of_load",
        translation_key="size_of_load",
        parameter="sizeOfLoad",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=SIZE_OF_LOAD_MAX_WATTS,
        native_step=SIZE_OF_LOAD_INCREMENT,
        scale=SIZE_OF_LOAD_INCREMENT,
        coerce=round,
        entity_category=EntityCategory.CONFIG,
    ),
    HeatitNumberEntityDescription(
        key="power_regulator_active_time",
        translation_key="power_regulator_active_time",
        parameter="powerRegulatorActiveTime",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=POWER_REGULATOR_MIN * (100 // POWER_REGULATOR_MAX),
        native_max_value=100,
        native_step=100 // POWER_REGULATOR_MAX,
        scale=100 // POWER_REGULATOR_MAX,
        coerce=round,
        entity_category=EntityCategory.CONFIG,
        # Commissioning setting, and inert unless sensorMode is 5 (PWER). In
        # that mode the device runs a fixed duty cycle with no temperature
        # feedback and no floor limit, so 100% means continuous heating.
        entity_registry_enabled_default=False,
    ),
    HeatitNumberEntityDescription(
        key="action_after_error",
        translation_key="action_after_error",
        parameter="actionAfterError",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_min_value=0,
        native_max_value=ACTION_AFTER_ERROR_MAX,
        native_step=1,
        mode=NumberMode.BOX,
        coerce=round,
        clamp_fn=_clamp_action_after_error,
        entity_category=EntityCategory.CONFIG,
        # Non-zero makes the device re-close the relay into an overload or
        # overheat fault on a timer, indefinitely. Off by default on purpose.
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities."""
    async_add_entities(HeatitNumber(entry, description) for description in NUMBERS)


class HeatitNumber(HeatitEntity, NumberEntity):
    """A writable numeric parameter."""

    entity_description: HeatitNumberEntityDescription

    def __init__(
        self, entry: HeatitConfigEntry, description: HeatitNumberEntityDescription
    ) -> None:
        """Initialise the number."""
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Current value, scaled into the unit this entity presents."""
        raw = self._parameters.get(self.entity_description.parameter)
        if raw is None:
            return None
        return float(raw) * self.entity_description.scale

    async def async_set_native_value(self, value: float) -> None:
        """Write a new value, clamped and scaled back to the wire format."""
        description = self.entity_description

        if description.clamp_fn is not None:
            value = description.clamp_fn(value)

        # The UI respects min/max, but a script or template call does not.
        value = min(max(value, description.native_min_value), description.native_max_value)

        wire_value = description.coerce(value / description.scale)
        await self.async_write_parameters({description.parameter: wire_value})
