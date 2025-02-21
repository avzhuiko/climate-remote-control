import logging
from unittest.mock import patch

from _pytest.logging import LogCaptureFixture
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_PRESET_MODE,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
)
from homeassistant.components.climate import (
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_BOOST,
    PRESET_NONE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_DEVICE,
    ATTR_HOLD_SECS,
    ATTR_NUM_REPEATS,
    SERVICE_SEND_COMMAND,
)
from homeassistant.const import ATTR_COMMAND, ATTR_ENTITY_ID, ATTR_TEMPERATURE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.setup import async_setup_component
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.climate_remote_control.climate import RestoreAcRemote
from custom_components.climate_remote_control.const import (
    ATTR_TEMPERATURE_RANGE,
    CONF_CAN_DISABLE_ENTITY_FEATURES,
    CONF_MAX,
    CONF_MIN,
    CONF_MODE,
    CONF_TEMPERATURE,
    DOMAIN,
    TemperatureMode,
)


async def test_setup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
):
    assert await async_setup_component(hass, DOMAIN, {}) is True
    await hass.async_block_till_done()
    assert entity_registry.async_get(hass).entities["climate.name_test"]


async def test_setup_with_empty_options(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    caplog: LogCaptureFixture,
):
    hass.config_entries.async_update_entry(entry=config_entry, options={})
    assert await async_setup_component(hass, DOMAIN, {}) is True
    await hass.async_block_till_done()
    assert "climate.name_test" not in entity_registry.async_get(hass).entities
    assert "Climate remote control platform is not configured, skip." in caplog.text


async def test_get_attr_command(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_hvac_mode = HVACMode.HEAT
    climate_remote_control._attr_fan_mode = FAN_MEDIUM
    climate_remote_control._attr_preset_mode = PRESET_BOOST
    climate_remote_control._attr_swing_mode = SWING_VERTICAL
    climate_remote_control._attr_target_temperature = 20.0
    climate_remote_control._attr_target_humidity = 55
    climate_remote_control._attr_target_temperature_low = 20.0
    climate_remote_control._attr_target_temperature_high = 22.0

    assert (
        climate_remote_control._get_attr_command(ATTR_HVAC_MODE)
        == "mode:" + HVACMode.HEAT
    )
    assert (
        climate_remote_control._get_attr_command(ATTR_FAN_MODE) == "fan:" + FAN_MEDIUM
    )
    assert (
        climate_remote_control._get_attr_command(ATTR_PRESET_MODE)
        == "preset:" + PRESET_BOOST
    )
    assert (
        climate_remote_control._get_attr_command(ATTR_SWING_MODE)
        == "swing:" + SWING_VERTICAL
    )
    assert climate_remote_control._get_attr_command(ATTR_TEMPERATURE) == "temp:20.0"
    assert (
        climate_remote_control._get_attr_command(ATTR_TEMPERATURE_RANGE)
        == "temprange:20.0:22.0"
    )
    assert climate_remote_control._get_attr_command(ATTR_HUMIDITY) == "humid:55"
    assert climate_remote_control._get_attr_command("dummy_command") == ""


async def test_get_temperature_conf(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._hvac_modes_conf = {
        HVACMode.OFF: {
            ATTR_TEMPERATURE: {
                CONF_MODE: TemperatureMode.NONE,
            },
        },
        HVACMode.HEAT: {
            ATTR_TEMPERATURE: {
                CONF_MODE: TemperatureMode.TARGET,
                CONF_MIN: 11.0,
                CONF_MAX: 21.0,
            }
        },
        HVACMode.COOL: {},
    }
    climate_remote_control._attr_hvac_mode = HVACMode.OFF
    temperature_conf = climate_remote_control._get_temperature_conf()
    assert temperature_conf == {CONF_MODE: TemperatureMode.NONE}

    climate_remote_control._attr_hvac_mode = HVACMode.HEAT
    temperature_conf = climate_remote_control._get_temperature_conf()
    assert temperature_conf == {
        CONF_MODE: TemperatureMode.TARGET,
        CONF_MIN: 11.0,
        CONF_MAX: 21.0,
    }

    climate_remote_control._attr_hvac_mode = HVACMode.COOL
    temperature_conf = climate_remote_control._get_temperature_conf()
    assert temperature_conf == {
        CONF_MODE: TemperatureMode.TARGET,
        CONF_MIN: 18.0,
        CONF_MAX: 28.0,
    }


async def test_get_grouping_attributes(
    climate_remote_control: RestoreAcRemote,
):
    # all attributes
    climate_remote_control._grouping_attributes = [
        ATTR_HVAC_MODE,
        ATTR_TEMPERATURE,
        ATTR_FAN_MODE,
        ATTR_HUMIDITY,
        ATTR_SWING_MODE,
    ]
    climate_remote_control._attr_swing_modes = []
    climate_remote_control._attr_supported_features = ClimateEntityFeature(0)
    climate_remote_control._attr_fan_modes = [FAN_LOW, FAN_MEDIUM]
    assert climate_remote_control._get_grouping_attributes() == [
        ATTR_HVAC_MODE,
        ATTR_FAN_MODE,
    ]

    # remove fan modes
    climate_remote_control._attr_fan_modes = []
    climate_remote_control._attr_supported_features = (
        ClimateEntityFeature(0)
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_HUMIDITY
    )
    assert climate_remote_control._get_grouping_attributes() == [
        ATTR_HVAC_MODE,
        ATTR_TEMPERATURE,
        ATTR_HUMIDITY,
    ]

    # test target temperature range
    climate_remote_control._grouping_attributes = [
        ATTR_HVAC_MODE,
        ATTR_TEMPERATURE_RANGE,
        ATTR_FAN_MODE,
        ATTR_HUMIDITY,
    ]
    climate_remote_control._attr_supported_features = ClimateEntityFeature(0)
    assert climate_remote_control._get_grouping_attributes() == [
        ATTR_HVAC_MODE,
    ]


async def test_get_command_in_grouping_attributes(
    climate_remote_control: RestoreAcRemote,
):
    with (
        patch.object(
            climate_remote_control,
            attribute="_get_grouping_attributes",
            return_value=[ATTR_HVAC_MODE, ATTR_TEMPERATURE, ATTR_FAN_MODE],
        ),
        patch.object(
            climate_remote_control,
            attribute="_get_attr_command",
            side_effect=["arg1", "arg2", "arg3"],
        ),
    ):
        result = climate_remote_control._get_command(ATTR_TEMPERATURE)
        assert "arg1_arg2_arg3" == result


async def test_get_command_not_in_grouping_attributes(
    climate_remote_control: RestoreAcRemote,
):
    with (
        patch.object(
            climate_remote_control,
            attribute="_get_grouping_attributes",
            return_value=[ATTR_HVAC_MODE, ATTR_FAN_MODE],
        ),
        patch.object(
            climate_remote_control,
            attribute="_get_attr_command",
            return_value="arg1",
        ),
    ):
        result = climate_remote_control._get_command(ATTR_TEMPERATURE)
        assert "arg1" == result


async def test_set_fan_mode(
    climate_remote_control: RestoreAcRemote,
):
    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ),
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        await climate_remote_control.async_set_fan_mode(FAN_LOW)
        mock_async_call_remote_command.assert_called_once_with("test_command")


async def test_set_swing_mode(
    climate_remote_control: RestoreAcRemote,
):
    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ),
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        await climate_remote_control.async_set_swing_mode(SWING_VERTICAL)
        mock_async_call_remote_command.assert_called_once_with("test_command")


async def test_set_target_temperature(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_preset_mode = PRESET_BOOST

    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ) as mock_get_command,
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        await climate_remote_control.async_set_temperature(**{ATTR_TEMPERATURE: 23})

        mock_get_command.assert_called_once_with(ATTR_TEMPERATURE)
        mock_async_call_remote_command.assert_called_once_with("test_command")
        assert climate_remote_control._attr_target_temperature == 23
        assert climate_remote_control._attr_preset_mode == PRESET_NONE


async def test_set_target_temperature_range(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_preset_mode = PRESET_BOOST

    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ) as mock_get_command,
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        await climate_remote_control.async_set_temperature(
            **{ATTR_TARGET_TEMP_LOW: 23, ATTR_TARGET_TEMP_HIGH: 25.5}
        )

        mock_get_command.assert_called_once_with(ATTR_TEMPERATURE_RANGE)
        mock_async_call_remote_command.assert_called_once_with("test_command")
        assert climate_remote_control._attr_target_temperature_low == 23
        assert climate_remote_control._attr_target_temperature_high == 25.5
        assert climate_remote_control._attr_preset_mode == PRESET_NONE


async def test_set_target_temperature_range_without_low(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_preset_mode = PRESET_BOOST

    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ) as mock_get_command,
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        with pytest.raises(ValueError) as ex:
            await climate_remote_control.async_set_temperature(
                **{ATTR_TARGET_TEMP_HIGH: 25.5}
            )
        assert (
            ex.value.args[0] == "temperature_low and temperature_high must be provided"
        )
        mock_get_command.assert_not_called()
        mock_async_call_remote_command.assert_not_called()


async def test_set_humidity(
    hass: HomeAssistant,
    climate_remote_control: RestoreAcRemote,
    remote_entity_id: str,
):
    send_command_service_calls = async_mock_service(
        hass=hass,
        domain=Platform.REMOTE,
        service=SERVICE_SEND_COMMAND,
    )

    climate_remote_control._attr_hvac_mode = HVACMode.OFF
    climate_remote_control._attr_fan_mode = FAN_MEDIUM
    climate_remote_control._attr_target_temperature = 20

    await climate_remote_control.async_set_humidity(55)

    expected_command = "humid:55"
    assert len(send_command_service_calls) == 1
    assert send_command_service_calls[0].data[ATTR_COMMAND] == expected_command
    assert send_command_service_calls[0].data[ATTR_NUM_REPEATS] == 1
    assert send_command_service_calls[0].data[ATTR_DELAY_SECS] == 0
    assert send_command_service_calls[0].data[ATTR_HOLD_SECS] == 0
    assert send_command_service_calls[0].data[ATTR_DEVICE] is not None


async def test_set_hvac_mode(
    hass: HomeAssistant,
    climate_remote_control: RestoreAcRemote,
    remote_entity_id: str,
    caplog: LogCaptureFixture,
):
    send_command_service_calls = async_mock_service(
        hass=hass,
        domain=Platform.REMOTE,
        service=SERVICE_SEND_COMMAND,
        raise_exception=ValueError(""),
    )
    climate_remote_control._attr_hvac_mode = HVACMode.OFF
    climate_remote_control._attr_fan_mode = FAN_MEDIUM
    climate_remote_control._attr_target_temperature = 20
    climate_remote_control._attr_preset_mode = PRESET_BOOST

    expected_command = "mode:heat_fan:medium_temp:20"
    caplog.set_level(logging.WARNING)

    await climate_remote_control.async_set_hvac_mode(HVACMode.HEAT)

    assert climate_remote_control._attr_preset_mode == PRESET_NONE
    assert len(send_command_service_calls) == 2
    assert send_command_service_calls[0].data[ATTR_COMMAND] == "on"
    assert send_command_service_calls[0].data[ATTR_NUM_REPEATS] == 1
    assert send_command_service_calls[0].data[ATTR_DELAY_SECS] == 0
    assert send_command_service_calls[0].data[ATTR_HOLD_SECS] == 0
    assert send_command_service_calls[0].data[ATTR_DEVICE] is not None
    assert send_command_service_calls[0].data[ATTR_ENTITY_ID][0] == remote_entity_id
    assert send_command_service_calls[1].data[ATTR_COMMAND] == expected_command
    assert send_command_service_calls[1].data[ATTR_NUM_REPEATS] == 1
    assert send_command_service_calls[1].data[ATTR_DELAY_SECS] == 0
    assert send_command_service_calls[1].data[ATTR_HOLD_SECS] == 0
    assert send_command_service_calls[1].data[ATTR_DEVICE] is not None
    assert send_command_service_calls[1].data[ATTR_ENTITY_ID][0] == remote_entity_id
    assert (
        'Command "on' + '" for device "test" not found. You should learn it.'
        not in caplog.text
    )


async def test_set_hvac_mode_set_off(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_hvac_mode = HVACMode.HEAT

    with patch.object(
        climate_remote_control,
        attribute="_async_call_remote_command",
    ) as mock_async_call_remote_command:
        await climate_remote_control.async_set_hvac_mode(HVACMode.OFF)
        mock_async_call_remote_command.assert_called_once_with("off")


async def test_filling_temperature_attributes_without_temperature(
    hass: HomeAssistant,
    climate_remote_control: RestoreAcRemote,
):
    async_mock_service(
        hass=hass,
        domain=Platform.REMOTE,
        service=SERVICE_SEND_COMMAND,
    )
    climate_remote_control._attr_hvac_mode = HVACMode.COOL
    climate_remote_control._hvac_modes_conf[HVACMode.HEAT][CONF_TEMPERATURE] = {
        CONF_MODE: TemperatureMode.NONE,
    }

    await climate_remote_control.async_set_hvac_mode(HVACMode.HEAT)

    assert (
        climate_remote_control._attr_supported_features
        & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        == 0
    )


async def test_filling_temperature_attributes_with_temperature_range(
    hass: HomeAssistant,
    climate_remote_control: RestoreAcRemote,
):
    async_mock_service(
        hass=hass,
        domain=Platform.REMOTE,
        service=SERVICE_SEND_COMMAND,
    )
    climate_remote_control._attr_hvac_mode = HVACMode.COOL
    climate_remote_control._hvac_modes_conf[HVACMode.HEAT][CONF_TEMPERATURE] = {
        CONF_MODE: TemperatureMode.RANGE,
        CONF_MIN: 20,
        CONF_MAX: 30,
    }

    await climate_remote_control.async_set_hvac_mode(HVACMode.HEAT)

    assert (
        climate_remote_control._attr_supported_features
        & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        == ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
    )
    assert climate_remote_control._attr_target_temperature_low == 20
    assert climate_remote_control._attr_target_temperature_high == 20


async def test_set_preset_mode(
    climate_remote_control: RestoreAcRemote,
):
    with (
        patch.object(
            climate_remote_control,
            attribute="_get_command",
            return_value="test_command",
        ) as mock_get_command,
        patch.object(
            climate_remote_control,
            attribute="_async_call_remote_command",
        ) as mock_async_call_remote_command,
    ):
        await climate_remote_control.async_set_preset_mode(PRESET_BOOST)
        mock_get_command.assert_called_once_with(ATTR_PRESET_MODE)
        mock_async_call_remote_command.assert_called_once_with("test_command")


async def test_reset_preset_mode_without_preset_modes(
    climate_remote_control: RestoreAcRemote,
):
    climate_remote_control._attr_preset_mode = None
    climate_remote_control._attr_preset_modes = None

    climate_remote_control._reset_preset_mode()

    assert climate_remote_control._attr_preset_mode is None


async def test_restoring_temperature_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    climate_remote_control: RestoreAcRemote,
):
    async_mock_service(
        hass=hass,
        domain=Platform.REMOTE,
        service=SERVICE_SEND_COMMAND,
    )
    assert await async_setup_component(hass, DOMAIN, {}) is True
    hass.config_entries.async_update_entry(
        entry=config_entry,
        options=config_entry.options | {CONF_CAN_DISABLE_ENTITY_FEATURES: True},
    )
    await hass.async_block_till_done()
    await hass.services.async_call(
        domain=CLIMATE_DOMAIN,
        service=SERVICE_SET_TEMPERATURE,
        service_data={ATTR_TEMPERATURE: 20},
        target={ATTR_ENTITY_ID: "climate.name_test"},
        blocking=True,
    )
    await hass.services.async_call(
        domain=CLIMATE_DOMAIN,
        service=SERVICE_SET_HVAC_MODE,
        service_data={ATTR_HVAC_MODE: HVACMode.HEAT},
        target={ATTR_ENTITY_ID: "climate.name_test"},
        blocking=True,
    )
    await hass.services.async_call(
        domain=CLIMATE_DOMAIN,
        service=SERVICE_SET_HVAC_MODE,
        service_data={ATTR_HVAC_MODE: HVACMode.OFF},
        target={ATTR_ENTITY_ID: "climate.name_test"},
        blocking=True,
    )

    await hass.config_entries.async_reload(config_entry.entry_id)

    assert hass.states.get("climate.name_test").attributes.get(CONF_TEMPERATURE) == 20
