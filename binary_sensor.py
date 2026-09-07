"""Binary sensor entities for the Heatit WiFi6 Thermostat."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HeatitConfigEntry
from .entity import HeatitEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatitConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor entities."""
    async_add_entities([HeatitOpenWindowSensor(entry)])


class HeatitOpenWindowSensor(HeatitEntity, BinarySensorEntity):
    """Whether open window detection has currently lowered the setpoint.

    This is not a window contact sensor, so it is named for the detection
    rather than for a window. The WINDOW device class is kept for the icon and
    because it renders the state as Open/Closed - which also keeps it readable
    apart from the paired switch, whose state renders as On/Off.
    """

    _attr_translation_key = "window_detection"
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, entry: HeatitConfigEntry) -> None:
        """Initialise the sensor."""
        super().__init__(entry, "open_window")

    @property
    def is_on(self) -> bool:
        """True while the device has detected an open window."""
        return bool(self._owd.get("activeNow"))
