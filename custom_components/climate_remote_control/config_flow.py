import logging
from typing import Any

from homeassistant.components.climate import HVAC_MODES, HVACMode
from homeassistant.config_entries import ConfigFlow
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
    UnitOfTemperature,
)
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.selector import SelectSelectorMode
import voluptuous as vol

from .const import (
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

TARGET_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID, default=[]): selector.EntitySelector(
            selector.EntitySelectorConfig(multiple=True, domain=Platform.REMOTE)
        ),
        vol.Optional(ATTR_DEVICE_ID, default=[]): selector.DeviceSelector(
            selector.DeviceSelectorConfig(
                multiple=True,
                entity=selector.EntitySelectorConfig(domain=Platform.REMOTE),
            )
        ),
        vol.Optional(ATTR_AREA_ID, default=[]): selector.AreaSelector(
            selector.AreaSelectorConfig(
                multiple=True,
                entity=selector.EntitySelectorConfig(domain=Platform.REMOTE),
            )
        ),
    }
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
        vol.Optional("min", default=16.0): vol.Coerce(float),
        vol.Optional("max", default=30.0): vol.Coerce(float),
    }
)

SWING_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MODE): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=False,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="swing_mode",
                options=SWING_MODES,
            )
        ),
        vol.Optional(CONF_MODES, default=[]): selector.SelectSelector(
            selector.SelectSelectorConfig(
                multiple=True,
                mode=SelectSelectorMode.LIST,
                translation_key="swing_state",
                options=SWING_STATES,
            )
        ),
    }
)

_LOGGER = logging.getLogger(__name__)


class ACRemoteConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    result: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_UNIQUE_ID): cv.string,
                        vol.Required(CONF_NAME): cv.string,
                        vol.Required(CONF_DEVICE): cv.string,
                    }
                ),
            )
        unique_id = user_input[CONF_UNIQUE_ID]
        self.result[CONF_NAME] = user_input[CONF_NAME]
        self.result[CONF_DEVICE] = user_input[CONF_DEVICE]
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return await self.async_step_target()

    async def async_step_target(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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

        if user_input is None or bool(errors):
            return self.async_show_form(
                step_id="target",
                data_schema=TARGET_SCHEMA,
                errors=errors,
            )
        return await self.async_step_temperature()

    async def async_step_temperature(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="temperature",
                data_schema=TEMPERATURE_SCHEMA.extend(
                    {
                        vol.Required(
                            CONF_TEMPERATURE_UNIT, default="c"
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=False,
                                mode=SelectSelectorMode.DROPDOWN,
                                translation_key="temperature_unit",
                                options=["c", "f"],
                            )
                        ),
                        vol.Required(CONF_TEMPERATURE_STEP, default=1.0): vol.All(
                            vol.Coerce(float), vol.Range(min=-10, max=10)
                        ),
                    }
                ),
            )

        temperature_unit = user_input[CONF_TEMPERATURE_UNIT]
        if temperature_unit == "c":
            self.result[CONF_TEMPERATURE_UNIT] = UnitOfTemperature.CELSIUS
        if temperature_unit == "f":
            self.result[CONF_TEMPERATURE_UNIT] = UnitOfTemperature.FAHRENHEIT

        self.result[CONF_TEMPERATURE_STEP] = user_input[CONF_TEMPERATURE_STEP]
        self.result[CONF_TEMPERATURE] = {
            CONF_MODE: user_input[CONF_MODE],
            CONF_MIN: user_input[CONF_MIN],
            CONF_MAX: user_input[CONF_MAX],
        }
        return await self.async_step_swing()

    async def async_step_swing(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="swing",
                data_schema=SWING_SCHEMA,
            )

        self.result[CONF_SWING] = {
            CONF_MODE: user_input[CONF_MODE],
            CONF_MODES: user_input[CONF_MODES],
        }
        return await self.async_step_hvac_modes()

    async def async_step_hvac_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="hvac_modes",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_MODES, default=[]): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                mode=SelectSelectorMode.LIST,
                                translation_key="hvac_mode",
                                options=HVAC_MODES,
                            )
                        ),
                    }
                ),
            )

        selected_modes = user_input[CONF_MODES]
        self.result[CONF_HVAC_MODES] = {}
        for mode in selected_modes:
            self.result[CONF_HVAC_MODES][mode] = {}
            if mode == HVACMode.OFF or mode == HVACMode.FAN_ONLY:
                self.result[CONF_HVAC_MODES][mode][
                    CONF_TEMPERATURE
                ] = TEMPERATURE_SCHEMA({CONF_MODE: TemperatureMode.NONE})
        return await self.async_step_fan_modes()

    async def async_step_fan_modes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="fan_modes",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_MODES, default=[]): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                multiple=True,
                                mode=SelectSelectorMode.LIST,
                                translation_key="fan_mode",
                                options=FAN_MODES,
                            )
                        ),
                    }
                ),
            )

        self.result[CONF_FAN_MODES] = user_input[CONF_MODES]
        return await self.async_step_grouping_attributes()

    async def async_step_grouping_attributes(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="grouping_attributes",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_GROUPING_ATTRIBUTES, default=[]
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
        return self.async_create_entry(
            title=self.result[CONF_NAME],
            data=self.result,
        )
