from homeassistant.components.climate import SWING_VERTICAL
from homeassistant.components.remote import SERVICE_SEND_COMMAND
from homeassistant.const import ATTR_ENTITY_ID, CONF_DEVICE, CONF_TARGET, Platform
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)
from pytest_mock import MockerFixture

from custom_components.climate_remote_control.button import (
    AcRemoteSwingToggle,
    async_setup_entry,
)
from custom_components.climate_remote_control.const import (
    CONF_MODE,
    CONF_MODES,
    CONF_SWING,
    DOMAIN,
    SwingMode,
)


async def test_none_mode(
    hass: HomeAssistant,
    mocker: MockerFixture,
    config_entry_unique_id: str,
):
    """Test button with none mode"""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=config_entry_unique_id,
        title="name_test",
        options={
            CONF_DEVICE: "test",
            CONF_TARGET: {ATTR_ENTITY_ID: ["remote.entity_id_test"]},
            CONF_SWING: {
                CONF_MODE: SwingMode.NONE,
            },
        },
    )

    mock_async_add_devices = mocker.stub("async_add_devices")
    await async_setup_entry(hass, config_entry, mock_async_add_devices)
    await hass.async_block_till_done()

    mock_async_add_devices.assert_called_once_with([])


async def test_toggle_mode(
    hass: HomeAssistant,
    mocker: MockerFixture,
    config_entry_unique_id: str,
):
    """Test button with toggle mode"""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=config_entry_unique_id,
        title="name_test",
        options={
            CONF_DEVICE: "test",
            CONF_TARGET: {ATTR_ENTITY_ID: ["remote.entity_id_test"]},
            CONF_SWING: {
                CONF_MODE: SwingMode.TOGGLE,
                CONF_MODES: [
                    SWING_VERTICAL,
                ],
            },
        },
    )

    mock_async_add_devices = mocker.stub("async_add_devices")
    await async_setup_entry(hass, config_entry, mock_async_add_devices)
    await hass.async_block_till_done()
    mock_async_add_devices.assert_called_once()
    devices = mock_async_add_devices.call_args_list[0].args[0]
    assert len(devices) == 1


async def test_state_mode(
    hass: HomeAssistant,
    mocker: MockerFixture,
    config_entry_unique_id: str,
):
    """Test button with state mode"""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=config_entry_unique_id,
        title="name_test",
        options={
            CONF_DEVICE: "test",
            CONF_TARGET: {ATTR_ENTITY_ID: ["remote.entity_id_test"]},
            CONF_SWING: {
                CONF_MODE: SwingMode.STATE,
            },
        },
    )

    mock_async_add_devices = mocker.stub("async_add_devices")
    await async_setup_entry(hass, config_entry, mock_async_add_devices)
    await hass.async_block_till_done()
    mock_async_add_devices.assert_called_once()
    devices = mock_async_add_devices.call_args_list[0].args[0]
    assert len(devices) == 0


async def test_press(
    hass: HomeAssistant,
    remote_entity_id: str,
    config_entry_unique_id: str,
):
    """Test press button"""
    button = AcRemoteSwingToggle(
        unique_id=config_entry_unique_id,
        name="test_name",
        target={ATTR_ENTITY_ID: [remote_entity_id]},
        device="test",
        mode=SWING_VERTICAL,
    )
    button.hass = hass
    send_command_service_calls = async_mock_service(
        hass, Platform.REMOTE, SERVICE_SEND_COMMAND
    )

    await button.async_press()
    assert len(send_command_service_calls) == 1
    service_call = send_command_service_calls[0]
    service_call_data = service_call.data
    assert service_call_data["command"] == "swing:" + SWING_VERTICAL
    assert service_call_data["device"] == "test"
    assert service_call_data[ATTR_ENTITY_ID] == [remote_entity_id]
