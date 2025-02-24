from unittest.mock import patch
import uuid

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.climate import (
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    PRESET_BOOST,
    PRESET_NONE,
    HVACMode,
)
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    CONF_NAME,
    CONF_TARGET,
    CONF_TEMPERATURE_UNIT,
    CONF_UNIQUE_ID,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult, FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_remote_control.const import (
    CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID,
    CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID,
    CONF_FAN_MODES,
    CONF_GROUPING_ATTRIBUTES,
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


@pytest.fixture(autouse=True)
def bypass_setup_fixture():
    """Prevent setup."""
    with patch(
        "custom_components.climate_remote_control.async_setup_entry",
        return_value=True,
    ):
        yield


async def test_config_flow(hass: HomeAssistant):
    """Test a successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    """Configuring general info"""
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "unique_id": "unique_id_1",
            "name": "my air conditioner",
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "my air conditioner"
    assert result["context"][CONF_UNIQUE_ID] == "unique_id_1"
    assert result["result"]

    data = result["data"]
    assert data[CONF_UNIQUE_ID] == "unique_id_1"
    assert data[CONF_NAME] == "my air conditioner"


async def test_options_flow_with_new_configuration(hass: HomeAssistant):
    config_entry_id = str(uuid.uuid4())
    config_entry_unique_id = str(uuid.uuid4())
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id=config_entry_id,
        unique_id=config_entry_unique_id,
        title="name_test",
        data={CONF_UNIQUE_ID: config_entry_unique_id, CONF_NAME: "name_test"},
        options={},
    )
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(config_entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "device"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"device": "LG_dummy"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "target"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"entity_id": ["remote.broadlink_1"]}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "temperature"

    # Configuring temperature.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "mode": "target",
            "temperature_unit": "c",
            "temperature_step": 0.5,
            "min": 10.0,
            "max": 32.0,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "swing"

    # Configuring swing.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"mode": "state", "modes": ["vertical", "on", "off"]},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "hvac_modes"

    # Configuring HVAC modes.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"modes": ["off", "auto", "heat", "cool"]}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "fan_modes"

    # Configuring fan modes.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MODES: [FAN_LOW, FAN_MEDIUM, FAN_HIGH, "My favourite fan speed"]
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "grouping_attributes"

    # Configuring grouping attributes.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "grouping_attributes": [
                "hvac_mode",
                "temperature",
                "fan_mode",
            ]
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "current_temperature_sensor_entity_id": "sensor.sensor_temperature",
            "current_humidity_sensor_entity_id": "sensor.sensor_humidity",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "preset_modes"

    # Configuring grouping attributes.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"modes": [PRESET_NONE, PRESET_BOOST]},
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "name_test"
    assert result["result"]

    data = result.get("data")

    target = data[CONF_TARGET]
    assert target[ATTR_ENTITY_ID] == ["remote.broadlink_1"]
    assert target[ATTR_DEVICE_ID] == []
    assert target[ATTR_AREA_ID] == []

    assert data[CONF_TEMPERATURE_STEP] == 0.5
    assert data[CONF_TEMPERATURE_UNIT] == "c"
    temperature = data[CONF_TEMPERATURE]
    assert temperature[CONF_MODE] == TemperatureMode.TARGET
    assert temperature[CONF_MIN] == 10.0
    assert temperature[CONF_MAX] == 32.0

    swing = data[CONF_SWING]
    assert swing[CONF_MODE] == SwingMode.STATE
    assert swing[CONF_MODES] == ["vertical", "on", "off"]

    hvac_modes = data[CONF_HVAC_MODES]
    assert hvac_modes[HVACMode.OFF] == {
        CONF_TEMPERATURE: {
            CONF_MODE: TemperatureMode.NONE,
            CONF_MIN: 16.0,
            CONF_MAX: 30.0,
        },
    }
    assert hvac_modes[HVACMode.AUTO] == {}
    assert hvac_modes[HVACMode.HEAT] == {}
    assert hvac_modes[HVACMode.COOL] == {}

    assert data[CONF_FAN_MODES] == ["low", "medium", "high", "My favourite fan speed"]

    assert data[CONF_GROUPING_ATTRIBUTES] == ["hvac_mode", "temperature", "fan_mode"]

    assert (
        data[CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID] == "sensor.sensor_temperature"
    )

    assert data[CONF_CURRENT_HUMIDITY_SENSOR_ENTITY_ID] == "sensor.sensor_humidity"
    assert data[CONF_PRESET_MODES] == [PRESET_NONE, PRESET_BOOST]


async def test_options_flow_empty_target(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test target validation."""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "target")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={ATTR_ENTITY_ID: []},
    )

    assert len(result["errors"]) == 1
    errors = result["errors"]
    assert errors["base"] == "target_is_empty"


async def test_options_flow_empty_hvac_modes(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test HVAC modes validation"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "hvac_modes")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_MODES: []},
    )

    assert len(result["errors"]) == 1
    errors = result["errors"]
    assert errors[CONF_MODES] == "hvac_modes_is_empty"


async def test_previously_configured_device(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "device")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_target(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "target")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_temperature(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "temperature")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_MODE: "target",
            CONF_TEMPERATURE_UNIT: "c",
            CONF_TEMPERATURE_STEP: 1,
            CONF_MIN: 18.0,
            CONF_MAX: 30.0,
        },
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_swing(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "swing")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_hvac_modes(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "hvac_modes")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_fan_modes(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration swing"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "fan_modes")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_grouping_attributes(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration sensors"""
    result = await _go_to_specific_step(
        hass, config_entry.entry_id, "grouping_attributes"
    )

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_sensors(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration sensors"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "sensors")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def test_previously_configured_preset_modes(
    hass: HomeAssistant, config_entry: MockConfigEntry
):
    """Test showing menu after configuration sensors"""
    result = await _go_to_specific_step(hass, config_entry.entry_id, "preset_modes")

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"


async def _go_to_specific_step(
    hass: HomeAssistant, config_entry_id: str, step_id: str
) -> FlowResult:
    result = await hass.config_entries.options.async_init(
        config_entry_id, context={"source": "user"}
    )

    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step_id": step_id},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id
    return result
