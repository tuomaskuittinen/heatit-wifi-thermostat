"""Constants for the Heatit WiFi6 Thermostat integration.

Ranges and enumerations come from the Heatit "WiFi 6" OpenAPI spec v7.0.0.
Where firmware 2.26 disagrees with the spec it is noted inline.
"""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "heatit_wifi_thermostat"

CONF_HOST: Final = "host"
CONF_NAME: Final = "name"

SCAN_INTERVAL_SECONDS: Final = 60
API_TIMEOUT: Final = 10

MANUFACTURER: Final = "Heatit"
MODEL: Final = "WiFi6 Thermostat"

OPERATING_MODE_OFF: Final = 0
OPERATING_MODE_HEAT: Final = 1
OPERATING_MODE_COOL: Final = 2
OPERATING_MODE_ECO: Final = 3

# Which setpoint parameter the device regulates against, per operating mode.
SETPOINT_BY_OPERATING_MODE: Final[dict[int, str]] = {
    OPERATING_MODE_HEAT: "heatingSetpoint",
    OPERATING_MODE_COOL: "coolingSetpoint",
    OPERATING_MODE_ECO: "ecoSetpoint",
}

SENSOR_MODE_FLOOR: Final = 0  # F
SENSOR_MODE_INTERNAL: Final = 1  # A   (device default)
SENSOR_MODE_INTERNAL_FLOOR: Final = 2  # AF
SENSOR_MODE_EXTERNAL: Final = 3  # A2
SENSOR_MODE_EXTERNAL_FLOOR: Final = 4  # A2F
SENSOR_MODE_POWER_REGULATOR: Final = 5  # PWER

SENSOR_MODE_OPTIONS: Final[dict[int, str]] = {
    SENSOR_MODE_FLOOR: "Floor sensor",
    SENSOR_MODE_INTERNAL: "Internal sensor",
    SENSOR_MODE_INTERNAL_FLOOR: "Internal with floor limitation",
    SENSOR_MODE_EXTERNAL: "External sensor",
    SENSOR_MODE_EXTERNAL_FLOOR: "External with floor limitation",
    SENSOR_MODE_POWER_REGULATOR: "Power regulator mode",
}

# Which status field holds the temperature the thermostat regulates against.
TEMPERATURE_KEY_BY_SENSOR_MODE: Final[dict[int, str]] = {
    SENSOR_MODE_FLOOR: "floorTemperature",
    SENSOR_MODE_INTERNAL: "internalTemperature",
    SENSOR_MODE_INTERNAL_FLOOR: "internalTemperature",
    SENSOR_MODE_EXTERNAL: "externalTemperature",
    SENSOR_MODE_EXTERNAL_FLOOR: "externalTemperature",
    # PWER runs a fixed duty cycle and reads no sensor at all. The internal
    # reading is the only meaningful thing left to display.
    SENSOR_MODE_POWER_REGULATOR: "internalTemperature",
}

# Which min/max limit pair is active, per sensor mode. Straight from the spec:
# internal* applies to "sensor mode A", floor* to "sensor mode AF, F, A2F",
# external* to "sensor mode A2". PWER has no temperature limit of any kind.
LIMIT_PREFIX_BY_SENSOR_MODE: Final[dict[int, str | None]] = {
    SENSOR_MODE_FLOOR: "floor",
    SENSOR_MODE_INTERNAL: "internal",
    SENSOR_MODE_INTERNAL_FLOOR: "floor",
    SENSOR_MODE_EXTERNAL: "external",
    SENSOR_MODE_EXTERNAL_FLOOR: "floor",
    SENSOR_MODE_POWER_REGULATOR: None,
}

SENSOR_RESISTANCE_OPTIONS: Final[dict[int, str]] = {
    0: "10 kOhm",
    1: "12 kOhm",
    2: "15 kOhm",
    3: "22 kOhm",
    4: "33 kOhm",
    5: "47 kOhm",
    6: "6.8 kOhm",
    7: "100 kOhm",
}

REGULATION_MODE_OPTIONS: Final[dict[bool, str]] = {
    False: "Hysteresis",
    True: "PWM",
}

TEMPERATURE_DISPLAY_OPTIONS: Final[dict[bool, str]] = {
    False: "Setpoint",
    True: "Measured temperature",
}

THERMOSTAT_STATES: Final[list[str]] = ["Idle", "Heating", "Cooling"]

TEMP_MIN: Final = 5.0
TEMP_MAX: Final = 40.0
TEMP_STEP: Final = 0.5

CALIBRATION_MIN: Final = -6.0
CALIBRATION_MAX: Final = 6.0
CALIBRATION_STEP: Final = 0.1

HYSTERESIS_MIN: Final = 0.3
HYSTERESIS_MAX: Final = 3.0
HYSTERESIS_STEP: Final = 0.1

BRIGHTNESS_MIN: Final = 1
BRIGHTNESS_MAX: Final = 10

# actionAfterError accepts 0, or 10-65535 seconds. 1-9 are illegal and get
# clamped up to this floor before being sent.
ACTION_AFTER_ERROR_MAX: Final = 65535
ACTION_AFTER_ERROR_MIN_DELAY: Final = 10

# sizeOfLoad is sent in 100 W increments (0-99). Entities work in watts.
SIZE_OF_LOAD_INCREMENT: Final = 100
SIZE_OF_LOAD_MAX_WATTS: Final = 9900

# powerRegulatorActiveTime is 1-10, meaning 10%-100% of a 30 minute duty cycle.
POWER_REGULATOR_MIN: Final = 1
POWER_REGULATOR_MAX: Final = 10

SERVICE_FACTORY_RESET: Final = "factory_reset"
ATTR_CONFIRM: Final = "confirm"
CONFIRM_PHRASE: Final = "reset"
