"""Platform for light integration."""

import asyncio
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TEMPERATURE,
    PRESET_NONE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
)
from homeassistant.components.remote import (
    SERVICE_SEND_COMMAND,
)
from homeassistant.components.remote import DOMAIN as RM_DOMAIN
from homeassistant.const import (
    ATTR_COMMAND,
    CONF_DEVICE,
    CONF_TARGET,
    CONF_TEMPERATURE_UNIT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import (
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    ATTR_TEMPERATURE_RANGE,
    CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID,
    CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID,
    CONF_FAN_MODES,
    CONF_GROUPING_ATTRIBUTES,
    CONF_HVAC_MODES,
    CONF_MODE,
    CONF_MODES,
    CONF_PRESET_MODES,
    CONF_SWING,
    CONF_TEMPERATURE,
    CONF_TEMPERATURE_STEP,
    DOMAIN,
    SwingMode,
    TemperatureMode,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up climate device"""
    if config_entry.options == {}:
        _LOGGER.debug("Climate remote control platform is not configured, skip.")
        return

    async_add_devices([AcRemote(config_entry)])


class AcRemote(ClimateEntity, RestoreEntity):
    """Representation of climate entity"""

    _attr_translation_key = DOMAIN
    _attr_has_entity_name = True
    _attr_name = None

    _attr_target_temperature_step = 1.0
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    _attr_hvac_modes = [HVACMode.OFF]
    _attr_hvac_mode = HVACMode.OFF

    _attr_supported_features = ClimateEntityFeature(0)

    _target: dict[str, Any] = {}
    _device: str
    _temperature_conf: dict[str, Any] = {}
    _hvac_modes_conf: dict[str, Any] = {}
    _grouping_attributes: [str] = []
    _current_temperature_sensor_entity_id: str | None = None

    def __init__(
        self,
        config_entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize."""
        options = config_entry.options
        unique_id = config_entry.unique_id
        self._attr_unique_id = unique_id

        self._grouping_attributes = options[CONF_GROUPING_ATTRIBUTES]
        self._temperature_conf = options[CONF_TEMPERATURE]
        self._hvac_modes_conf = options[CONF_HVAC_MODES]
        self._device = options[CONF_DEVICE]
        temperature_unit = options[CONF_TEMPERATURE_UNIT]
        if temperature_unit == "c":
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        if temperature_unit == "f":
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        self._attr_hvac_modes = list(HVACMode(x) for x in self._hvac_modes_conf.keys())
        self._attr_hvac_mode = self._attr_hvac_modes[0]

        self._fill_temperature_attributes(self._temperature_conf)
        self._attr_target_temperature_step = options[CONF_TEMPERATURE_STEP]

        # Configure fan modes
        fan_modes = options[CONF_FAN_MODES]
        self._attr_fan_modes = fan_modes
        if len(fan_modes) > 0:
            self._attr_fan_mode = fan_modes[0]
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE
        else:
            self._attr_fan_mode = None
            self._attr_fan_modes = None

        # Configure preset modes
        if CONF_PRESET_MODES in options:
            preset_modes = options[CONF_PRESET_MODES]
            self._attr_preset_modes = preset_modes
            if len(preset_modes) > 0:
                self._attr_preset_mode = preset_modes[0]
                self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE
            else:
                self._attr_preset_mode = None
        else:
            self._attr_preset_mode = None
            self._attr_preset_modes = None

        # Configure swing modes
        swing = options[CONF_SWING]
        self._attr_swing_modes = swing[CONF_MODES]
        if swing[CONF_MODE] == SwingMode.STATE:
            if len(self._attr_swing_modes) > 0:
                self._attr_swing_mode = self._attr_swing_modes[0]
                self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
        else:
            self._attr_swing_mode = None
        self._target = options[CONF_TARGET]

        # Configure sensors
        if CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID in options:
            self._current_temperature_sensor_entity_id = options[
                CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID
            ]
        if CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID in options:
            self._current_humidity_sensor_entity_id = options[
                CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID
            ]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="avzhuiko",
            name=config_entry.title,
        )

    def _fill_temperature_attributes(self, temperature):
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
        if key == ATTR_PRESET_MODE:
            attr_key = "preset"
            attr_value = str(self._attr_preset_mode)
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
        temperature_conf = self._temperature_conf
        hvac_mode = self._attr_hvac_mode
        if CONF_TEMPERATURE in self._hvac_modes_conf[hvac_mode]:
            temperature_conf = self._hvac_modes_conf[hvac_mode][CONF_TEMPERATURE]
        return temperature_conf

    def _get_grouping_attributes(self) -> [str]:
        grouping_attributes = self._grouping_attributes.copy()

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

    async def _async_call_remote_command(self, command: str, should_learn: bool = True):
        services = self.hass.services
        _LOGGER.debug(
            "Calling service %s.%s, with command=%s, device=%s, target=%s",
            RM_DOMAIN,
            SERVICE_SEND_COMMAND,
            command,
            self._device,
            self._target,
        )
        try:
            await services.async_call(
                domain=RM_DOMAIN,
                service=SERVICE_SEND_COMMAND,
                service_data={
                    ATTR_COMMAND: command,
                    ATTR_NUM_REPEATS: 1,
                    ATTR_DELAY_SECS: 0,
                    ATTR_HOLD_SECS: 0,
                    ATTR_DEVICE: self._device,
                },
                target=self._target,
                blocking=True,
            )
        except ValueError:
            """todo: send permanent notification to learn new command"""
            if should_learn:
                _LOGGER.warning(
                    'Command "%s" for device "%s" not found. You should learn it.',
                    command,
                    self._device,
                )

    async def _async_update_current_temperature_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle temperature sensor changes."""
        new_state = event.data["new_state"]
        self._async_update_current_temperature(new_state)

    async def _async_update_current_humidity_changed(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Handle humidity sensor changes."""
        new_state = event.data["new_state"]
        self._async_update_current_humidity(new_state)

    @callback
    def _async_update_current_temperature(self, new_state: State | None):
        """Update current temperature."""
        if new_state is None:
            return
        try:
            if new_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                self._attr_current_temperature = float(new_state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from temperature sensor: %s", ex)

    @callback
    def _async_update_current_humidity(self, new_state: State | None):
        """Update current humidity."""
        if new_state is None:
            return
        try:
            if new_state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                self._attr_current_humidity = int(float(new_state.state))
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)

    @callback
    def _async_restore_last_state(self, last_state: State) -> None:
        """Restore previous state."""
        attributes = last_state.attributes
        self._attr_hvac_mode = last_state.state
        if ATTR_FAN_MODE in attributes:
            self._attr_fan_mode = attributes[ATTR_FAN_MODE]
        if ATTR_PRESET_MODE in attributes:
            self._attr_preset_mode = attributes[ATTR_PRESET_MODE]
        if ATTR_SWING_MODE in attributes:
            self._attr_swing_mode = attributes[ATTR_SWING_MODE]
        if ATTR_TEMPERATURE in attributes:
            self._attr_target_temperature = attributes[ATTR_TEMPERATURE]
        if ATTR_TARGET_TEMP_LOW in attributes:
            self._attr_target_temperature_low = attributes[ATTR_TARGET_TEMP_LOW]
        if ATTR_TARGET_TEMP_HIGH in attributes:
            self._attr_target_temperature_high = attributes[ATTR_TARGET_TEMP_HIGH]
        self._fill_temperature_attributes(self._get_temperature_conf())

    async def async_added_to_hass(self):
        """Run when about to be added to hass."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if last_state is not None:
            self._async_restore_last_state(last_state)

        """Subscribe to current temperature sensor updates"""
        if self._current_temperature_sensor_entity_id:
            async_track_state_change_event(
                self.hass,
                self._current_temperature_sensor_entity_id,
                self._async_update_current_temperature_changed,
            )

            current_temperature_sensor_state = self.hass.states.get(
                self._current_temperature_sensor_entity_id
            )
            self._async_update_current_temperature(current_temperature_sensor_state)

        """Subscribe to current humidity sensor updates"""
        if (
            hasattr(self, "_current_humidity_sensor_entity_id")
            and self._current_humidity_sensor_entity_id
        ):
            async_track_state_change_event(
                self.hass,
                self._current_humidity_sensor_entity_id,
                self._async_update_current_humidity_changed,
            )

            current_humidity_sensor_state = self.hass.states.get(
                self._current_humidity_sensor_entity_id
            )
            self._async_update_current_humidity(current_humidity_sensor_state)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature: float | None = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._attr_target_temperature = temperature
            command = self._get_command(ATTR_TEMPERATURE)
            self._reset_preset_mode()
            await self._async_call_remote_command(command)
            return
        temperature_low: float | None = kwargs.get(ATTR_TARGET_TEMP_LOW)
        temperature_high: float | None = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if temperature_low is not None and temperature_high is not None:
            self._attr_target_temperature_low = temperature_low
            self._attr_target_temperature_high = temperature_high
            command = self._get_command(ATTR_TEMPERATURE_RANGE)
            self._reset_preset_mode()
            await self._async_call_remote_command(command)
        else:
            raise ValueError("temperature_low and temperature_high must be provided")

    async def async_set_humidity(self, humidity: int) -> None:
        self._attr_target_humidity = humidity
        command = self._get_command(ATTR_HUMIDITY)
        await self._async_call_remote_command(command)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        old_mode = self._attr_hvac_mode
        self._attr_hvac_mode = hvac_mode
        self._reset_preset_mode()
        self._fill_temperature_attributes(self._get_temperature_conf())
        if hvac_mode == HVACMode.OFF:
            await self._async_call_remote_command("off")
            return
        if hvac_mode != HVACMode.OFF and old_mode == HVACMode.OFF:
            await self._async_call_remote_command("on", False)
            await asyncio.sleep(1)
        command = self._get_command(ATTR_HVAC_MODE)
        await self._async_call_remote_command(command)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self._attr_swing_mode = swing_mode
        command = self._get_command(ATTR_SWING_MODE)
        await self._async_call_remote_command(command)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._attr_fan_mode = fan_mode
        command = self._get_command(ATTR_FAN_MODE)
        await self._async_call_remote_command(command)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        self._attr_preset_mode = preset_mode
        command = self._get_command(ATTR_PRESET_MODE)
        await self._async_call_remote_command(command)

    def _reset_preset_mode(self) -> None:
        if (
            self._attr_preset_modes is None
            or self._attr_preset_modes == []
            or PRESET_NONE not in self._attr_preset_modes
        ):
            return
        self._attr_preset_mode = PRESET_NONE
