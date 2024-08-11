import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.climate import HVAC_MODES, HVACMode
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_DEVICE,
    CONF_NAME,
    CONF_TARGET,
    CONF_TEMPERATURE_UNIT,
    CONF_UNIQUE_ID,
    Platform,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectSelectorMode
import voluptuous as vol

from .const import (
    CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID,
    CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID,
    CONF_FAN_MODES,
    CONF_GROUPING_ATTRIBUTES,
    CONF_HVAC_MODES,
    CONF_MAX,
    CONF_MIN,
    CONF_MODE,
    CONF_MODES,
    CONF_SWING,
    CONF_TEMPERATURE,
    CONF_TEMPERATURE_STEP,
    DOMAIN,
    FAN_MODES,
    GROUPING_ATTRIBUTES,
    SWING_MODES,
    SWING_STATES,
    TEMPERATURE_MODES,
    TemperatureMode,
)

TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=False,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="temperature_mode",
                options=TEMPERATURE_MODES,
            )
        ),
        vol.Optional(CONF_MIN, default=16.0): vol.Coerce(float),
        vol.Optional(CONF_MAX, default=30.0): vol.Coerce(float),
    }
)

_LOGGER = logging.getLogger(__name__)


class ACRemoteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_UNIQUE_ID): cv.string,
                        vol.Required(CONF_NAME): cv.string,
                    }
                ),
            )
        await self.async_set_unique_id(user_input[CONF_UNIQUE_ID])
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=user_input[CONF_NAME],
            data=user_input,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    result: dict[str, Any] = {}

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    def _is_previously_configured(self) -> bool:
        if self.config_entry.options is None or self.config_entry.options == {}:
            return False
        return True

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if self._is_previously_configured():
            return self.async_show_menu(
                step_id="init",
                menu_options=[
                    "device",
                    "target",
                    "temperature",
                    "swing",
                    "hvac_modes",
                    "fan_modes",
                    "grouping_attributes",
                    "sensors",
                    "finish",
                ],
            )
        else:
            return await self.async_step_device()

    async def async_step_device(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is None:
            return self.async_show_form(
                step_id="device",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_DEVICE,
                            default=self.config_entry.options.get(CONF_DEVICE),
                        ): cv.string
                    }
                ),
            )

        self.result[CONF_DEVICE] = user_input[CONF_DEVICE]
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_target()

    async def async_step_target(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            entity_ids: [str] = user_input[ATTR_ENTITY_ID]
            device_ids: [str] = user_input[ATTR_DEVICE_ID]
            area_ids: [str] = user_input[ATTR_AREA_ID]
            if len(entity_ids) == 0 and len(device_ids) == 0 and len(area_ids) == 0:
                errors["base"] = "target_is_empty"
            else:
                self.result[CONF_TARGET] = {
                    ATTR_ENTITY_ID: entity_ids,
                    ATTR_DEVICE_ID: device_ids,
                    ATTR_AREA_ID: area_ids,
                }

        default_target = self.config_entry.options.get(
            CONF_TARGET, {ATTR_ENTITY_ID: [], ATTR_DEVICE_ID: [], ATTR_AREA_ID: []}
        )
        if user_input is None or bool(errors):
            return self.async_show_form(
                step_id="target",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            ATTR_ENTITY_ID, default=default_target.get(ATTR_ENTITY_ID)
                        ): selector.EntitySelector(
                            selector.EntitySelectorConfig(
                                multiple=True, domain=Platform.REMOTE
                            )
                        ),
                        vol.Optional(
                            ATTR_DEVICE_ID, default=default_target.get(ATTR_DEVICE_ID)
                        ): selector.DeviceSelector(
                            selector.DeviceSelectorConfig(
                                multiple=True,
                                entity=selector.EntitySelectorConfig(
                                    domain=Platform.REMOTE
                                ),
                            )
                        ),
                        vol.Optional(
                            ATTR_AREA_ID, default=default_target.get(ATTR_AREA_ID)
                        ): selector.AreaSelector(
                            selector.AreaSelectorConfig(
                                multiple=True,
                                entity=selector.EntitySelectorConfig(
                                    domain=Platform.REMOTE
                                ),
                            )
                        ),
                    }
                ),
                errors=errors,
            )
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_temperature()

    async def async_step_temperature(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            default_temperature = self.config_entry.options.get(
                CONF_TEMPERATURE,
                {
                    CONF_MODE: None,
                    CONF_MIN: 16.0,
                    CONF_MAX: 30.0,
                },
            )
            return self.async_show_form(
                step_id="temperature",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_MODE, default=default_temperature.get(CONF_MODE)
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=False,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="temperature_mode",
                                options=TEMPERATURE_MODES,
                            )
                        ),
                        vol.Optional(
                            CONF_MIN, default=default_temperature.get(CONF_MIN)
                        ): vol.Coerce(float),
                        vol.Optional(
                            CONF_MAX, default=default_temperature.get(CONF_MAX)
                        ): vol.Coerce(float),
                        vol.Required(
                            CONF_TEMPERATURE_UNIT,
                            default=self.config_entry.options.get(
                                CONF_TEMPERATURE_UNIT, "c"
                            ),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=False,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="temperature_unit",
                                options=["c", "f"],
                            )
                        ),
                        vol.Required(
                            CONF_TEMPERATURE_STEP,
                            default=self.config_entry.options.get(
                                CONF_TEMPERATURE_STEP, 1.0
                            ),
                        ): vol.All(vol.Coerce(float), vol.Range(min=0, max=10)),
                    },
                ),
            )

        self.result[CONF_TEMPERATURE_UNIT] = user_input[CONF_TEMPERATURE_UNIT]
        self.result[CONF_TEMPERATURE_STEP] = user_input[CONF_TEMPERATURE_STEP]
        self.result[CONF_TEMPERATURE] = {
            CONF_MODE: user_input[CONF_MODE],
            CONF_MIN: user_input[CONF_MIN],
            CONF_MAX: user_input[CONF_MAX],
        }
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_swing()

    async def async_step_swing(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            default_swing = self.config_entry.options.get(
                CONF_SWING,
                {
                    CONF_MODE: None,
                    CONF_MODES: [],
                },
            )
            return self.async_show_form(
                step_id="swing",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_MODE, default=default_swing.get(CONF_MODE)
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=False,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="swing_mode",
                                options=SWING_MODES,
                            )
                        ),
                        vol.Optional(
                            CONF_MODES, default=default_swing.get(CONF_MODES)
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                mode=SelectSelectorMode.LIST,
                                translation_key="swing_state",
                                options=SWING_STATES,
                            )
                        ),
                    }
                ),
            )

        self.result[CONF_SWING] = {
            CONF_MODE: user_input[CONF_MODE],
            CONF_MODES: user_input[CONF_MODES],
        }
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_hvac_modes()

    async def async_step_hvac_modes(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            selected_modes = user_input[CONF_MODES]
            if len(selected_modes) == 0:
                errors[CONF_MODES] = "hvac_modes_is_empty"
            else:
                self.result[CONF_HVAC_MODES] = {}
                for mode in selected_modes:
                    self.result[CONF_HVAC_MODES][mode] = {}
                    if mode in (HVACMode.OFF, HVACMode.FAN_ONLY, HVACMode.DRY):
                        self.result[CONF_HVAC_MODES][mode][CONF_TEMPERATURE] = (
                            TEMPERATURE_SCHEMA({CONF_MODE: TemperatureMode.NONE})
                        )
        if user_input is None or bool(errors):
            default_hvac_modes = self.config_entry.options.get(CONF_HVAC_MODES, {})
            return self.async_show_form(
                step_id="hvac_modes",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_MODES,
                            default=list(x for x in default_hvac_modes.keys()),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                mode=SelectSelectorMode.LIST,
                                translation_key="hvac_mode",
                                options=HVAC_MODES,
                            )
                        ),
                    }
                ),
                errors=errors,
            )
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_fan_modes()

    async def async_step_fan_modes(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            return self.async_show_form(
                step_id="fan_modes",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_MODES,
                            default=self.config_entry.options.get(CONF_FAN_MODES, []),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                custom_value=True,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="fan_mode",
                                options=FAN_MODES,
                            )
                        ),
                    }
                ),
            )

        self.result[CONF_FAN_MODES] = user_input[CONF_MODES]
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_grouping_attributes()

    async def async_step_grouping_attributes(
        self, user_input: dict[str, Any] | None = None
    ):
        if user_input is None:
            return self.async_show_form(
                step_id="grouping_attributes",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_GROUPING_ATTRIBUTES,
                            default=self.config_entry.options.get(
                                CONF_GROUPING_ATTRIBUTES, []
                            ),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="grouping_attribute",
                                options=GROUPING_ATTRIBUTES,
                            )
                        ),
                    }
                ),
            )

        self.result[CONF_GROUPING_ATTRIBUTES] = user_input[CONF_GROUPING_ATTRIBUTES]
        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_sensors()

    async def async_step_sensors(self, user_input: dict[str, Any] | None = None):
        if user_input is None:
            return self.async_show_form(
                step_id="sensors",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID,
                            default=self.config_entry.options.get(
                                CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID
                            ),
                        ): vol.Any(
                            None,
                            selector.EntitySelector(
                                selector.EntitySelectorConfig(
                                    multiple=False,
                                    domain=Platform.SENSOR,
                                    device_class=SensorDeviceClass.TEMPERATURE,
                                )
                            ),
                        ),
                        vol.Optional(
                            CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID,
                            default=self.config_entry.options.get(
                                CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID
                            ),
                        ): vol.Any(
                            None,
                            selector.EntitySelector(
                                selector.EntitySelectorConfig(
                                    multiple=False,
                                    domain=Platform.SENSOR,
                                    device_class=SensorDeviceClass.HUMIDITY,
                                )
                            ),
                        ),
                    }
                ),
            )

        self.result[CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID] = user_input[
            CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID
        ]
        self.result[CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID] = user_input[
            CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID
        ]

        if self._is_previously_configured():
            return await self.async_step_init()
        else:
            return await self.async_step_finish()

    async def async_step_finish(self, user_input: dict[str, Any] | None = None):
        options = self.config_entry.options | {}
        return self.async_create_entry(
            title=self.config_entry.title,
            data=options | self.result,
        )
