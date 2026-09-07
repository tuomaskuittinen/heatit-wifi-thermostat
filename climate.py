"""Climate entity for the Heatit WiFi6 Thermostat."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    PRESET_ECO,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .const import (
    LIMIT_PREFIX_BY_SENSOR_MODE,
    OPERATING_MODE_COOL,
    OPERATING_MODE_ECO,
    OPERATING_MODE_HEAT,
    OPERATING_MODE_OFF,
    SENSOR_MODE_INTERNAL,
    SETPOINT_BY_OPERATING_MODE,
    TEMP_MAX,
    TEMP_MIN,
    TEMP_STEP,
    TEMPERATURE_KEY_BY_SENSOR_MODE,
)
from .entity import HeatitEntity

# ECO is a fourth operating mode on the device, not a fourth HVAC mode, so it is
# exposed as a preset over HEAT. Mapping it onto an unrelated HVACMode would
# mislead the UI and voice assistants.
HVAC_MODE_TO_OPERATING_MODE: dict[HVACMode, int] = {
    HVACMode.OFF: OPERATING_MODE_OFF,
    HVACMode.HEAT: OPERATING_MODE_HEAT,
    HVACMode.COOL: OPERATING_MODE_COOL,
}
OPERATING_MODE_TO_HVAC_MODE: dict[int, HVACMode] = {
    OPERATING_MODE_OFF: HVACMode.OFF,
    OPERATING_MODE_HEAT: HVACMode.HEAT,
    OPERATING_MODE_COOL: HVACMode.COOL,
    OPERATING_MODE_ECO: HVACMode.HEAT,
}

STATE_TO_HVAC_ACTION: dict[str, HVACAction] = {
    "Idle": HVACAction.IDLE,
    "Heating": HVACAction.HEATING,
    "Cooling": HVACAction.COOLING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entity."""
    async_add_entities([HeatitThermostat(entry)])


class HeatitThermostat(HeatitEntity, ClimateEntity):
    """The thermostat itself."""

    _attr_name = None  # takes the device name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TEMP_STEP
    _attr_precision = 0.1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL]
    _attr_preset_modes = [PRESET_NONE, PRESET_ECO]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, entry: HeatitConfigEntry) -> None:
        """Initialise the climate entity."""
        super().__init__(entry, "climate")

    @property
    def _operating_mode(self) -> int:
        return int(self._parameters.get("operatingMode", OPERATING_MODE_HEAT))

    @property
    def _sensor_mode(self) -> int:
        return int(self._parameters.get("sensorMode", SENSOR_MODE_INTERNAL))

    @property
    def hvac_mode(self) -> HVACMode:
        """Current HVAC mode. ECO reports as HEAT with the eco preset set."""
        return OPERATING_MODE_TO_HVAC_MODE.get(self._operating_mode, HVACMode.HEAT)

    @property
    def hvac_action(self) -> HVACAction | None:
        """Whether the relay is currently closed, from the device's own state."""
        if self._operating_mode == OPERATING_MODE_OFF:
            return HVACAction.OFF
        return STATE_TO_HVAC_ACTION.get(str(self._status.get("state")))

    @property
    def preset_mode(self) -> str:
        """ECO preset, which is operatingMode 3 on the device."""
        return PRESET_ECO if self._operating_mode == OPERATING_MODE_ECO else PRESET_NONE

    @property
    def current_temperature(self) -> float | None:
        """Temperature from whichever sensor the current sensor mode regulates on."""
        key = TEMPERATURE_KEY_BY_SENSOR_MODE.get(
            self._sensor_mode, "internalTemperature"
        )
        return self._status.get(key)

    @property
    def target_temperature(self) -> float | None:
        """Setpoint for the current operating mode. None when the device is off."""
        parameter = SETPOINT_BY_OPERATING_MODE.get(self._operating_mode)
        if parameter is None:
            return None
        return self._parameters.get(parameter)

    def _limit(self, bound: str, fallback: float) -> float:
        """Read the min/max limit that applies to the current sensor mode.

        The spec scopes each limit pair to specific sensor modes: internal* to
        mode A, floor* to AF/F/A2F, external* to A2. Power regulator mode has no
        temperature limit at all, so the full API range applies there.
        """
        prefix = LIMIT_PREFIX_BY_SENSOR_MODE.get(self._sensor_mode, "internal")
        if prefix is None:
            return fallback
        value = self._parameters.get(f"{prefix}{bound}TemperatureLimit")
        return float(value) if value is not None else fallback

    @property
    def min_temp(self) -> float:
        """Lowest setpoint the thermostat will accept in this sensor mode."""
        return self._limit("Minimum", TEMP_MIN)

    @property
    def max_temp(self) -> float:
        """Highest setpoint the thermostat will accept in this sensor mode."""
        return self._limit("Maximum", TEMP_MAX)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Write the setpoint belonging to the current operating mode."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        parameter = SETPOINT_BY_OPERATING_MODE.get(self._operating_mode)
        if parameter is None:
            # Off has no setpoint. Set the heating setpoint so the value is not
            # silently dropped when the user turns the thermostat back on.
            parameter = SETPOINT_BY_OPERATING_MODE[OPERATING_MODE_HEAT]

        await self.async_write_parameters({parameter: float(temperature)})

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Switch between off, heating and cooling."""
        if (mode := HVAC_MODE_TO_OPERATING_MODE.get(hvac_mode)) is None:
            return
        await self.async_write_parameters({"operatingMode": mode})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Enter or leave ECO mode."""
        if preset_mode == PRESET_ECO:
            mode = OPERATING_MODE_ECO
        elif self._operating_mode == OPERATING_MODE_ECO:
            mode = OPERATING_MODE_HEAT
        else:
            return
        await self.async_write_parameters({"operatingMode": mode})
