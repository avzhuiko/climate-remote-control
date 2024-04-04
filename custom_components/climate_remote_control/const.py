"""AC remote control constants"""

from enum import StrEnum

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    ATTR_TEMPERATURE,
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_MIDDLE,
    FAN_OFF,
    FAN_ON,
    FAN_TOP,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_ON,
    SWING_VERTICAL,
)

DOMAIN = "climate_remote_control"

DATA_CONFIG = "config"

ATTR_TEMPERATURE_RANGE = "temperature_range"
CONF_TEMPERATURE = "temperature"
CONF_TEMPERATURE_STEP = "temperature_step"
CONF_TEMPERATURE_OFFSET = "temperature_offset"
CONF_HUMIDITY_OFFSET = "humidity_offset"
CONF_HVAC_MODES = "hvac_modes"
CONF_FAN_MODES = "fan_modes"
CONF_SWING = "swing"
CONF_MODE = "mode"
CONF_MODES = "modes"
CONF_MIN = "min"
CONF_MAX = "max"
CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID = "current_temperature_sensor_entity_id"
CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID = "current_humidity_sensor_entity_id"
CONF_GROUPING_ATTRIBUTES = "grouping_attributes"
GROUPING_ATTRIBUTES = [
    ATTR_HVAC_MODE,
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    ATTR_TEMPERATURE,
    ATTR_TEMPERATURE_RANGE,
    ATTR_HUMIDITY,
]
FAN_MODES = [
    FAN_ON,
    FAN_OFF,
    FAN_AUTO,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
    FAN_TOP,
    FAN_MIDDLE,
    FAN_FOCUS,
    FAN_DIFFUSE,
]

SWING_STATES = [
    SWING_ON,
    SWING_OFF,
    SWING_BOTH,
    SWING_VERTICAL,
    SWING_HORIZONTAL,
]


class TemperatureMode(StrEnum):
    """Temperature modes"""

    """Can't control temperature"""
    NONE = "none"

    """Can set target temperature"""
    TARGET = "target"

    """Can set a range with min and max temperatures"""
    RANGE = "range"


TEMPERATURE_MODES = [cls for cls in TemperatureMode]


class SwingMode(StrEnum):
    """Swing mode"""

    """Can't control swing"""
    NONE = "none"

    """Swing modes is stateless for remote control"""
    TOGGLE = "toggle"

    """Swing modes have the states"""
    STATE = "state"


SWING_MODES = [cls for cls in SwingMode]
