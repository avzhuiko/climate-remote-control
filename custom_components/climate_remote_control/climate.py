"""Platform for light integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.remote import DOMAIN as RM_DOMAIN
from homeassistant.components.remote import SERVICE_SEND_COMMAND
from homeassistant.const import (
    CONF_DEVICE,
    CONF_NAME,
    CONF_TARGET,
    CONF_TEMPERATURE_UNIT,
    UnitOfTemperature,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    ATTR_TEMPERATURE_RANGE,
    CONF_FAN_MODES,
    CONF_GROUPING_ATTRIBUTES,
    CONF_HVAC_MODES,
    CONF_MODE,
    CONF_MODES,
    CONF_SWING,
    CONF_TEMPERATURE,
    CONF_TEMPERATURE_STEP,
    DOMAIN,
    SwingMode,
    TemperatureMode,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices) -> None:
    """Set up climate device"""

    devices = []

    data = entry.data

    unique_id = entry.unique_id
    name = data[CONF_NAME]
    target = data[CONF_TARGET]
    temperature_unit = data[CONF_TEMPERATURE_UNIT]
    temperature_step = data[CONF_TEMPERATURE_STEP]
    hvac_modes = data[CONF_HVAC_MODES]
    fan_modes = data[CONF_FAN_MODES]
    swing = data[CONF_SWING]
    grouping_attributes = data[CONF_GROUPING_ATTRIBUTES]
    temperature = data[CONF_TEMPERATURE]
    device = data[CONF_DEVICE]
    devices.append(
        AcRemote(
            unique_id=unique_id,
            name=name,
            grouping_attributes=grouping_attributes,
            temperature_unit=temperature_unit,
            hvac_modes=hvac_modes,
            fan_modes=fan_modes,
            swing=swing,
            target=target,
            device=device,
            temperature=temperature,
            temperature_step=temperature_step,
        )
    )

    async_add_devices(devices)


class AcRemote(ClimateEntity):
    """Representation of climate entity"""

    _attr_has_entity_name = True
    _attr_name = None

    target: dict[str, Any] = {}
    device: str
    temperature_conf: dict[str, Any] = {}
    hvac_modes_conf: dict[str, Any] = {}
    grouping_attributes: [str] = []

    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    _attr_hvac_modes = [HVACMode.OFF]
    _attr_hvac_mode = HVACMode.OFF

    _attr_supported_features = ClimateEntityFeature(0)

    def __init__(
        self,
        unique_id,
        name,
        target,
        device: str,
        hvac_modes,
        swing,
        temperature,
        fan_modes: [str],
        grouping_attributes: [str],
        temperature_unit: UnitOfTemperature = UnitOfTemperature.CELSIUS,
        temperature_step: float = 1.0,
    ) -> None:
        """Initialize."""
        self.grouping_attributes = grouping_attributes
        self.temperature_conf = temperature
        self.hvac_modes_conf = hvac_modes
        self.device = device
        self._attr_unique_id = unique_id
        self._attr_temperature_unit = temperature_unit
        self._attr_hvac_modes = list(HVACMode(x) for x in hvac_modes.keys())
        self._attr_hvac_mode = self._attr_hvac_modes[0]

        self.fill_temperature_attributes(temperature)
        if temperature[CONF_MODE] != TemperatureMode.NONE:
            self._attr_target_temperature_step = temperature_step
        # set fan modes
        self._attr_fan_modes = fan_modes
        if len(fan_modes) > 0:
            self._attr_fan_mode = fan_modes[0]
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        else:
            self._attr_fan_mode = None

        # set swing modes
        self._attr_swing_modes = swing[CONF_MODES]
        if swing[CONF_MODE] == SwingMode.STATE:
            if len(self._attr_swing_modes) > 0:
                self._attr_swing_mode = self._attr_swing_modes[0]
                self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
        else:
            self._attr_swing_mode = None
        self.target = target
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="avzhuiko",
            name=name,
        )

    def fill_temperature_attributes(self, temperature):
        if temperature[CONF_MODE] == TemperatureMode.NONE:
            self._attr_supported_features ^= (
                self._attr_supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
            )
            return
        self._attr_min_temp = temperature["min"]
        self._attr_max_temp = temperature["max"]
        if temperature[CONF_MODE] == TemperatureMode.TARGET:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            if self._attr_target_temperature is None:
                self._attr_target_temperature = temperature["min"]
        if temperature[CONF_MODE] == TemperatureMode.RANGE:
            self._attr_supported_features |= (
                ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            if self._attr_target_temperature_low is None:
                self._attr_target_temperature_low = temperature["min"]
            if self._attr_target_temperature_high is None:
                self._attr_target_temperature_high = temperature["min"]

    def _get_attr_command(self, key: str) -> str:
        attr_key = key
        attr_value = ""
        if key == ATTR_HVAC_MODE:
            attr_key = "mode"
            attr_value = str(self._attr_hvac_mode)
        if key == ATTR_FAN_MODE:
            attr_key = "fan"
            attr_value = str(self._attr_fan_mode)
        if key == ATTR_SWING_MODE:
            attr_key = "swing"
            attr_value = str(self._attr_swing_mode)
        if key == ATTR_TEMPERATURE:
            attr_key = "temp"
            attr_value = str(self._attr_target_temperature)
        if key == ATTR_TEMPERATURE_RANGE:
            attr_key = "temprange"
            attr_value = (
                str(self._attr_target_temperature_low)
                + ":"
                + str(self._attr_target_temperature_high)
            )
        if key == ATTR_HUMIDITY:
            attr_key = "humid"
            attr_value = str(self._attr_target_humidity)
        return attr_key + (":" + str(attr_value)) if attr_value != "" else ""

    def _get_temperature_conf(self):
        temperature_conf = self.temperature_conf
        hvac_mode = self._attr_hvac_mode
        if CONF_TEMPERATURE in self.hvac_modes_conf[hvac_mode]:
            temperature_conf = self.hvac_modes_conf[hvac_mode][CONF_TEMPERATURE]
        return temperature_conf

    def _get_grouping_attributes(self) -> [str]:
        grouping_attributes = self.grouping_attributes.copy()

        supported_features = self._attr_supported_features
        if (
            not supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
            and ATTR_TEMPERATURE in grouping_attributes
        ):
            grouping_attributes.remove(ATTR_TEMPERATURE)
        if (
            not supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            and ATTR_TEMPERATURE_RANGE in grouping_attributes
        ):
            grouping_attributes.remove(ATTR_TEMPERATURE_RANGE)
        if (
            not supported_features & ClimateEntityFeature.TARGET_HUMIDITY
            and ATTR_HUMIDITY in grouping_attributes
        ):
            grouping_attributes.remove(ATTR_HUMIDITY)
        if len(self._attr_fan_modes) < 1 and ATTR_FAN_MODE in grouping_attributes:
            grouping_attributes.remove(ATTR_FAN_MODE)
        if len(self._attr_swing_modes) < 1 and ATTR_SWING_MODE in grouping_attributes:
            grouping_attributes.remove(ATTR_SWING_MODE)
        return grouping_attributes

    def _get_command(self, key: str) -> str:
        """Get code by current state and keys"""
        grouping_attributes = self._get_grouping_attributes()
        if key not in grouping_attributes:
            return self._get_attr_command(key)
        commands: [str] = []
        for grouping_key in grouping_attributes:
            commands.append(self._get_attr_command(grouping_key))
        return "_".join(str(x) for x in commands)

    def _call_remote_command(self, command: str):
        services = self.hass.services
        _LOGGER.debug(
            "Calling service %s.%s, with command=%s, device=%s, target=%s",
            RM_DOMAIN,
            SERVICE_SEND_COMMAND,
            command,
            self.device,
            self.target,
        )
        try:
            services.call(
                domain=RM_DOMAIN,
                service=SERVICE_SEND_COMMAND,
                service_data={
                    "command": command,
                    # todo: from config
                    "num_repeats": 1,
                    "delay_secs": 0,
                    "hold_secs": 0,
                    "device": self.device,
                },
                target=self.target,
                blocking=True,
            )
        except ValueError:
            """todo: send permanent notification to learn new command"""
            _LOGGER.warning(
                'Command "%s" for device "%s" not found. You should learn it.',
                command,
                self.device,
            )

    def turn_on(self):
        self._call_remote_command("on")

    def turn_off(self):
        self._call_remote_command("off")

    def set_temperature(self, **kwargs: Any) -> None:
        temperature: float | None = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._attr_target_temperature = temperature
            command = self._get_command(ATTR_TEMPERATURE)
            self._call_remote_command(command)
            return
        temperature_low: float | None = kwargs.get(ATTR_TARGET_TEMP_LOW)
        temperature_high: float | None = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if temperature_low is not None and temperature_high is not None:
            self._attr_target_temperature_low = temperature_low
            self._attr_target_temperature_high = temperature_high
            command = self._get_command(ATTR_TEMPERATURE_RANGE)
            self._call_remote_command(command)
        else:
            raise ValueError("temperature_low and temperature_high must be provided")

    def set_humidity(self, humidity: int) -> None:
        self._attr_target_humidity = humidity
        command = self._get_command(ATTR_HUMIDITY)
        self._call_remote_command(command)

    def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        old_mode = self._attr_hvac_mode
        self._attr_hvac_mode = hvac_mode
        self.fill_temperature_attributes(self._get_temperature_conf())
        if hvac_mode == HVACMode.OFF:
            self.turn_off()
            return
        if hvac_mode != HVACMode.OFF and old_mode == HVACMode.OFF:
            self.turn_on()
        command = self._get_command(ATTR_HVAC_MODE)
        self._call_remote_command(command)

    def set_swing_mode(self, swing_mode: str) -> None:
        self._attr_swing_mode = swing_mode
        command = self._get_command(ATTR_SWING_MODE)
        self._call_remote_command(command)

    def set_fan_mode(self, fan_mode: str) -> None:
        self._attr_fan_mode = fan_mode
        command = self._get_command(ATTR_FAN_MODE)
        self._call_remote_command(command)
