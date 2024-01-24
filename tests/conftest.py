from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    FAN_DIFFUSE,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_VERTICAL,
    HVACMode,
)
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_DEVICE,
    CONF_NAME,
    CONF_TARGET,
    CONF_TEMPERATURE_UNIT,
    CONF_UNIQUE_ID,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_mock import MockerFixture

from custom_components.climate_remote_control.climate import (
    async_setup_entry as climate_async_setup_entry,
)
from custom_components.climate_remote_control.climate import AcRemote
from custom_components.climate_remote_control.const import (
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
    SwingMode,
    TemperatureMode,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def config_entry_options() -> dict[str, Any] | None:
    """Fixture to set initial config entry options."""
    return None


@pytest.fixture
def config_entry_unique_id() -> str:
    """Fixture that returns the default config entry unique id."""
    return "test"


@pytest.fixture
def remote_entity_id() -> str:
    """Fixture that returns the default remote entity id."""
    return "remote.test_entity"


@pytest.fixture
def config_entry(
    config_entry_unique_id: str,
    remote_entity_id: str,
    config_entry_options: dict[str, Any] | None,
) -> MockConfigEntry:
    """Fixture to create a config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=config_entry_unique_id,
        title="name_test",
        data={
            CONF_UNIQUE_ID: "test",
            CONF_NAME: "name_test",
            CONF_DEVICE: "test",
            CONF_TARGET: {
                ATTR_ENTITY_ID: [remote_entity_id],
                ATTR_DEVICE_ID: [],
                ATTR_AREA_ID: [],
            },
            CONF_TEMPERATURE_STEP: 1,
            CONF_TEMPERATURE_UNIT: UnitOfTemperature.CELSIUS,
            CONF_TEMPERATURE: {
                CONF_MODE: TemperatureMode.TARGET,
                CONF_MIN: 18,
                CONF_MAX: 28,
            },
            CONF_SWING: {
                CONF_MODE: SwingMode.TOGGLE,
                CONF_MODES: [
                    SWING_VERTICAL,
                ],
            },
            CONF_HVAC_MODES: {
                HVACMode.OFF: {},
                HVACMode.AUTO: {},
                HVACMode.DRY: {},
                HVACMode.COOL: {},
                HVACMode.HEAT: {},
                HVACMode.FAN_ONLY: {},
            },
            CONF_FAN_MODES: [
                FAN_LOW,
                FAN_MEDIUM,
                FAN_HIGH,
                FAN_DIFFUSE,
            ],
            CONF_GROUPING_ATTRIBUTES: [
                ATTR_HVAC_MODE,
                ATTR_FAN_MODE,
                ATTR_TEMPERATURE,
            ],
            CONF_CURRENT_TEMPERATURE_SENSOR_ENTITY_ID: "sensor.sensor_temperature",
        },
        options=config_entry_options,
    )


@pytest.fixture
async def climate_remote_control(
    hass: HomeAssistant, config_entry: MockConfigEntry, mocker: MockerFixture
) -> AcRemote:
    mock_async_add_devices = mocker.stub("async_add_devices")
    await climate_async_setup_entry(hass, config_entry, mock_async_add_devices)
    devices = mock_async_add_devices.call_args_list[0].args[0]
    climate = devices[0]
    climate.hass = hass
    return climate
