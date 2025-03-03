"""Platform for climate integration."""

import asyncio
from dataclasses import dataclass
import logging
from typing import Any, Self

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
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity

from .const import (
    ATTR_TEMPERATURE_RANGE,
    CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID,
    CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID,
    CONF_FAN_MODES,
    CONF_GROUPING_ATTRIBUTES,
    CONF_GROUPING_ATTRIBUTES_AS_SEQUENCE,
    CONF_HVAC_MODES,
    CONF_MAX,
    CONF_MIN,
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

    async_add_devices([RestoreAcRemote(config_entry)])


class AcRemote(ClimateEntity):
    """Representation of climate entity"""

    _attr_translation_key = DOMAIN
    _attr_has_entity_name = True
    _attr_name = None

    _attr_target_temperature_step = 1.0
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    _attr_hvac_modes = [HVACMode.OFF]
    _attr_hvac_mode = HVACMode.OFF

    _attr_supported_features = ClimateEntityFeature(0)

    _target: dict[str, Any]
    _device: str
    _temperature_conf: dict[str, Any]
    _hvac_modes_conf: dict[str, Any]
    _grouping_attributes: [str]
    _grouping_attributes_as_sequence: bool
    _current_temperature_sensor_entity_id: str | None
    _current_humidity_sensor_entity_id: str | None

    def __init__(
        self,
        config_entry: config_entries.ConfigEntry,
    ) -> None:
        """Initialize."""
        options = config_entry.options
        unique_id = config_entry.unique_id
        self._attr_unique_id = unique_id

        self._grouping_attributes = options.get(CONF_GROUPING_ATTRIBUTES)
        self._grouping_attributes_as_sequence = options.get(
            CONF_GROUPING_ATTRIBUTES_AS_SEQUENCE, False
        )
        self._temperature_conf = options.get(CONF_TEMPERATURE)
        self._hvac_modes_conf = options.get(CONF_HVAC_MODES)
        self._device = options.get(CONF_DEVICE)
        self._target = options.get(CONF_TARGET)
        temperature_unit = options.get(CONF_TEMPERATURE_UNIT)
        if temperature_unit == "c":
            self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        if temperature_unit == "f":
            self._attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
        self._attr_hvac_modes = list(HVACMode(x) for x in self._hvac_modes_conf.keys())
        self._attr_hvac_mode = self._attr_hvac_modes[0]

        self._fill_temperature_attributes(self._temperature_conf)
        self._attr_target_temperature_step = options.get(CONF_TEMPERATURE_STEP)

        # Configure fan modes
        self._attr_fan_mode = None
        self._attr_fan_modes = options.get(CONF_FAN_MODES)
        if len(self._attr_fan_modes) > 0:
            self._attr_fan_mode = self._attr_fan_modes[0]
            self._attr_supported_features |= ClimateEntityFeature.FAN_MODE

        # Configure preset modes
        self._attr_preset_mode = None
        self._attr_preset_modes = options.get(CONF_PRESET_MODES)
        if len(self._attr_preset_modes) > 0:
            self._attr_supported_features |= ClimateEntityFeature.PRESET_MODE

        # Configure swing modes
        swing = options[CONF_SWING]
        self._attr_swing_modes = swing[CONF_MODES]
        if swing[CONF_MODE] == SwingMode.STATE:
            if len(self._attr_swing_modes) > 0:
                self._attr_swing_mode = self._attr_swing_modes[0]
                self._attr_supported_features |= ClimateEntityFeature.SWING_MODE
        else:
            self._attr_swing_mode = None

        # Configure sensors
        self._current_temperature_sensor_entity_id = options.get(
            CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID
        )
        self._current_humidity_sensor_entity_id = options.get(
            CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID
        )

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
        self._attr_min_temp = temperature[CONF_MIN]
        self._attr_max_temp = temperature[CONF_MAX]
        if temperature[CONF_MODE] == TemperatureMode.TARGET:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            if self._attr_target_temperature is None:
                self._attr_target_temperature = temperature[CONF_MIN]
        if temperature[CONF_MODE] == TemperatureMode.RANGE:
            self._attr_supported_features |= (
                ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            if getattr(self, "_attr_target_temperature_low", None) is None:
                self._attr_target_temperature_low = temperature[CONF_MIN]
            if getattr(self, "_attr_target_temperature_high", None) is None:
                self._attr_target_temperature_high = temperature[CONF_MIN]

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

    def _get_commands(self, key: str) -> [str]:
        """Get code by current state and keys"""
        grouping_attributes = self._get_grouping_attributes()
        if key not in grouping_attributes:
            return [self._get_attr_command(key)]
        commands: [str] = []
        for grouping_key in grouping_attributes:
            commands.append(self._get_attr_command(grouping_key))
        if self._grouping_attributes_as_sequence:
            return commands
        return ["_".join(str(x) for x in commands)]

    async def _async_call_remote_command(
        self, commands: [str], should_learn: bool = True
    ):
        services = self.hass.services
        _LOGGER.debug(
            "Calling service %s.%s, with command=%s, device=%s, target=%s",
            RM_DOMAIN,
            SERVICE_SEND_COMMAND,
            commands,
            self._device,
            self._target,
        )
        try:
            await services.async_call(
                domain=RM_DOMAIN,
                service=SERVICE_SEND_COMMAND,
                service_data={
                    ATTR_COMMAND: commands,
                    ATTR_NUM_REPEATS: 1,
                    ATTR_DELAY_SECS: 1,
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
                    commands,
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

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature: float | None = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._attr_target_temperature = temperature
            commands = self._get_commands(ATTR_TEMPERATURE)
            self._reset_preset_mode()
            await self._async_call_remote_command(commands)
            return
        temperature_low: float | None = kwargs.get(ATTR_TARGET_TEMP_LOW)
        temperature_high: float | None = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        if temperature_low is not None and temperature_high is not None:
            self._attr_target_temperature_low = temperature_low
            self._attr_target_temperature_high = temperature_high
            commands = self._get_commands(ATTR_TEMPERATURE_RANGE)
            self._reset_preset_mode()
            await self._async_call_remote_command(commands)
        else:
            raise ValueError("temperature_low and temperature_high must be provided")

    async def async_set_humidity(self, humidity: int) -> None:
        self._attr_target_humidity = humidity
        commands = self._get_commands(ATTR_HUMIDITY)
        await self._async_call_remote_command(commands)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        old_mode = self._attr_hvac_mode
        self._attr_hvac_mode = hvac_mode
        self._reset_preset_mode()
        self._fill_temperature_attributes(self._get_temperature_conf())
        if hvac_mode == HVACMode.OFF:
            await self._async_call_remote_command(["off"])
            return
        if hvac_mode != HVACMode.OFF and old_mode == HVACMode.OFF:
            await self._async_call_remote_command(["on"], False)
            await asyncio.sleep(1)
        commands = self._get_commands(ATTR_HVAC_MODE)
        await self._async_call_remote_command(commands)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        self._attr_swing_mode = swing_mode
        commands = self._get_commands(ATTR_SWING_MODE)
        await self._async_call_remote_command(commands)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        self._attr_fan_mode = fan_mode
        commands = self._get_commands(ATTR_FAN_MODE)
        await self._async_call_remote_command(commands)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        self._attr_preset_mode = preset_mode
        commands = self._get_commands(ATTR_PRESET_MODE)
        await self._async_call_remote_command(commands)

    def _reset_preset_mode(self) -> None:
        if (
            self._attr_preset_modes is None
            or self._attr_preset_modes == []
            or PRESET_NONE not in self._attr_preset_modes
        ):
            return
        self._attr_preset_mode = PRESET_NONE


@dataclass
class AcRemoteExtraStoredData(ExtraStoredData):
    """Object to hold extra stored data."""

    target_temperature: float | None
    target_temperature_low: float | None
    target_temperature_high: float | None

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of additional data."""
        target_temperature: float | None = self.target_temperature
        target_temperature_low: float | None = self.target_temperature_low
        target_temperature_high: float | None = self.target_temperature_high
        return {
            ATTR_TEMPERATURE: target_temperature,
            ATTR_TARGET_TEMP_LOW: target_temperature_low,
            ATTR_TARGET_TEMP_HIGH: target_temperature_high,
        }

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> Self | None:
        """Initialize a stored state from a dict."""
        target_temperature = restored.get(ATTR_TEMPERATURE)
        target_temperature_low = restored.get(ATTR_TARGET_TEMP_LOW)
        target_temperature_high = restored.get(ATTR_TARGET_TEMP_HIGH)

        return cls(target_temperature, target_temperature_low, target_temperature_high)


class RestoreAcRemote(AcRemote, RestoreEntity):
    """Mixin class for restoring previous state."""

    @callback
    async def _async_restore_last_state(self) -> None:
        """Restore previous state."""
        last_state = await self.async_get_last_state()
        if last_state is not None:
            attributes = last_state.attributes
            self._attr_hvac_mode = last_state.state
            self._attr_fan_mode = attributes.get(ATTR_FAN_MODE, self._attr_fan_mode)
            self._attr_swing_mode = attributes.get(
                ATTR_SWING_MODE, self._attr_swing_mode
            )
            self._attr_preset_mode = attributes.get(
                ATTR_PRESET_MODE, self._attr_preset_mode
            )

        last_extra_data = await self.async_get_last_climate_data()
        if last_extra_data is not None:
            self._attr_target_temperature = last_extra_data.target_temperature
            self._attr_target_temperature_low = last_extra_data.target_temperature_low
            self._attr_target_temperature_high = last_extra_data.target_temperature_high
        self._fill_temperature_attributes(self._get_temperature_conf())

    @property
    def extra_restore_state_data(self) -> AcRemoteExtraStoredData:
        """Return specific state data to be restored."""
        return AcRemoteExtraStoredData(
            getattr(self, "_attr_target_temperature", None),
            getattr(self, "_attr_target_temperature_low", None),
            getattr(self, "_attr_target_temperature_high", None),
        )

    async def async_get_last_climate_data(self) -> AcRemoteExtraStoredData | None:
        """Restore climate data"""
        if (restored_last_extra_data := await self.async_get_last_extra_data()) is None:
            return None
        return AcRemoteExtraStoredData.from_dict(restored_last_extra_data.as_dict())

    async def async_added_to_hass(self):
        """Run when about to be added to hass."""
        await super().async_added_to_hass()

        await self._async_restore_last_state()

        """Subscribe to current temperature sensor updates"""
        if getattr(self, "_current_temperature_sensor_entity_id", None) is not None:
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
        if getattr(self, "_current_humidity_sensor_entity_id", None) is not None:
            async_track_state_change_event(
                self.hass,
                self._current_humidity_sensor_entity_id,
                self._async_update_current_humidity_changed,
            )

            current_humidity_sensor_state = self.hass.states.get(
                self._current_humidity_sensor_entity_id
            )
            self._async_update_current_humidity(current_humidity_sensor_state)
