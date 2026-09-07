"""Sensor entities for the Heatit WiFi6 Thermostat."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from . import HeatitConfigEntry
from .const import THERMOSTAT_STATES
from .entity import HeatitEntity


def _network(status: dict[str, Any]) -> dict[str, Any]:
    network = status.get("network")
    return network if isinstance(network, dict) else {}


def _owd(status: dict[str, Any]) -> dict[str, Any]:
    parameters = status.get("parameters")
    if not isinstance(parameters, dict):
        return {}
    owd = parameters.get("OWD")
    return owd if isinstance(owd, dict) else {}


def _parse_rssi(status: dict[str, Any]) -> StateType:
    """Turn the device's "-67dBm" string into an integer.

    The spec's own example omits the minus sign, so parse defensively rather
    than assuming a fixed format.
    """
    raw = _network(status).get("wifiSignalStrength")
    if raw is None:
        return None
    text = str(raw).strip().lower().removesuffix("dbm").strip()
    try:
        return int(float(text))
    except ValueError:
        return None


def _non_empty(value: Any) -> StateType:
    """Map the device's empty-string fields to None.

    `room` is an empty string on any unit the MyHeatit app has not written to,
    and an empty string is not a useful sensor state.
    """
    text = str(value).strip() if value is not None else ""
    return text or None


@dataclass(frozen=True, kw_only=True)
class HeatitSensorEntityDescription(SensorEntityDescription):
    """Describes one Heatit sensor."""

    value_fn: Callable[[dict[str, Any]], StateType]


SENSORS: tuple[HeatitSensorEntityDescription, ...] = (
    HeatitSensorEntityDescription(
        key="internal_temperature",
        translation_key="internal_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.get("internalTemperature"),
    ),
    HeatitSensorEntityDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.get("floorTemperature"),
    ),
    HeatitSensorEntityDescription(
        key="external_temperature",
        translation_key="external_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_registry_enabled_default=False,
        value_fn=lambda status: status.get("externalTemperature"),
    ),
    HeatitSensorEntityDescription(
        key="power_consumption",
        translation_key="power_consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda status: status.get("currentPower"),
    ),
    HeatitSensorEntityDescription(
        key="total_consumption",
        translation_key="total_consumption",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda status: status.get("totalConsumption"),
    ),
    HeatitSensorEntityDescription(
        key="thermostat_state",
        translation_key="thermostat_state",
        device_class=SensorDeviceClass.ENUM,
        options=THERMOSTAT_STATES,
        value_fn=lambda status: status.get("state"),
    ),
    HeatitSensorEntityDescription(
        key="open_window_time_remaining",
        translation_key="open_window_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        # Seconds left until detection releases the setpoint. Firmware 2.26 omits
        # the field while detection is idle, and may only send it once a window
        # is detected - so create the entity unconditionally and report nothing
        # until a value arrives. A conditional check runs while idle, and would
        # therefore never create it at all.
        entity_registry_enabled_default=False,
        value_fn=lambda status: _owd(status).get("activeTime"),
    ),
    HeatitSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: status.get("firmware"),
    ),
    HeatitSensorEntityDescription(
        key="device_name",
        translation_key="device_name",
        entity_category=EntityCategory.DIAGNOSTIC,
        # The MyHeatit app name as stored on the device. Kept because it has
        # been cleared by manufacturer OTA updates, so a change here is a useful
        # marker for a device-side settings reset. Never used for HA naming.
        value_fn=lambda status: _non_empty(status.get("name")),
    ),
    HeatitSensorEntityDescription(
        key="room",
        translation_key="room",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda status: _non_empty(status.get("room")),
    ),
    HeatitSensorEntityDescription(
        key="wifi_signal_strength",
        translation_key="wifi_signal_strength",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_parse_rssi,
    ),
    HeatitSensorEntityDescription(
        key="ssid",
        translation_key="ssid",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda status: _non_empty(_network(status).get("SSID")),
    ),
    HeatitSensorEntityDescription(
        key="ip_address",
        translation_key="ip_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda status: _non_empty(_network(status).get("ipAddress")),
    ),
    HeatitSensorEntityDescription(
        key="mac_address",
        translation_key="mac_address",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda status: _non_empty(_network(status).get("mac")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    async_add_entities(HeatitSensor(entry, description) for description in SENSORS)


class HeatitSensor(HeatitEntity, SensorEntity):
    """A read-only value from the status document."""

    entity_description: HeatitSensorEntityDescription

    def __init__(
        self, entry: HeatitConfigEntry, description: HeatitSensorEntityDescription
    ) -> None:
        """Initialise the sensor."""
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType:
        """Current value, pulled from the coordinator's status document."""
        return self.entity_description.value_fn(self._status)
