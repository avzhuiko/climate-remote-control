from unittest.mock import call, patch

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HUMIDITY,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.climate_remote_control.climate import AcRemote
from custom_components.climate_remote_control.const import (
    ATTR_TEMPERATURE_RANGE,
    CONF_MAX,
    CONF_MIN,
    CONF_MODE,
    TemperatureMode,
)


async def test_get_attr_command(
    climate_remote_control: AcRemote,
):
    climate_remote_control._attr_hvac_mode = HVACMode.HEAT
    climate_remote_control._attr_fan_mode = FAN_MEDIUM
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
    climate_remote_control: AcRemote,
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
    climate_remote_control: AcRemote,
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
    climate_remote_control: AcRemote,
):
    with patch.object(
        climate_remote_control,
        attribute="_get_grouping_attributes",
        return_value=[ATTR_HVAC_MODE, ATTR_TEMPERATURE, ATTR_FAN_MODE],
    ), patch.object(
        climate_remote_control,
        attribute="_get_attr_command",
        side_effect=["arg1", "arg2", "arg3"],
    ):
        result = climate_remote_control._get_command(ATTR_TEMPERATURE)
        assert "arg1_arg2_arg3" == result


async def test_get_command_not_in_grouping_attributes(
    climate_remote_control: AcRemote,
):
    with patch.object(
        climate_remote_control,
        attribute="_get_grouping_attributes",
        return_value=[ATTR_HVAC_MODE, ATTR_FAN_MODE],
    ), patch.object(
        climate_remote_control,
        attribute="_get_attr_command",
        return_value="arg1",
    ):
        result = climate_remote_control._get_command(ATTR_TEMPERATURE)
        assert "arg1" == result


async def test_set_fan_mode(
    climate_remote_control: AcRemote,
):
    with patch.object(
        climate_remote_control,
        attribute="_get_command",
        return_value="test_command",
    ), patch.object(
        climate_remote_control,
        attribute="_call_remote_command",
    ) as mock_call_remote_command:
        await climate_remote_control.async_set_fan_mode(FAN_LOW)
        mock_call_remote_command.assert_called_once_with("test_command")


async def test_set_swing_mode(
    climate_remote_control: AcRemote,
):
    with patch.object(
        climate_remote_control,
        attribute="_get_command",
        return_value="test_command",
    ), patch.object(
        climate_remote_control,
        attribute="_call_remote_command",
    ) as mock_call_remote_command:
        await climate_remote_control.async_set_swing_mode(SWING_VERTICAL)
        mock_call_remote_command.assert_called_once_with("test_command")


async def test_set_humidity(
    climate_remote_control: AcRemote,
):
    with patch.object(
        climate_remote_control,
        attribute="_get_command",
        return_value="test_command",
    ), patch.object(
        climate_remote_control,
        attribute="_call_remote_command",
    ) as mock_call_remote_command:
        await climate_remote_control.async_set_humidity(55)
        mock_call_remote_command.assert_called_once_with("test_command")


async def test_set_hvac_mode_was_off(
    climate_remote_control: AcRemote,
):
    climate_remote_control._attr_hvac_mode = HVACMode.OFF

    with patch.object(
        climate_remote_control,
        attribute="_get_command",
        return_value="test_command",
    ), patch.object(
        climate_remote_control,
        attribute="_call_remote_command",
    ) as mock_call_remote_command:
        await climate_remote_control.async_set_hvac_mode(HVACMode.HEAT)
        assert mock_call_remote_command.call_count == 2
        assert mock_call_remote_command.call_args_list[0] == call("on")
        assert mock_call_remote_command.call_args_list[1] == call("test_command")


async def test_set_hvac_mode_set_off(
    climate_remote_control: AcRemote,
):
    climate_remote_control._attr_hvac_mode = HVACMode.HEAT

    with patch.object(
        climate_remote_control,
        attribute="_call_remote_command",
    ) as mock_call_remote_command:
        await climate_remote_control.async_set_hvac_mode(HVACMode.OFF)
        mock_call_remote_command.assert_called_once_with("off")
