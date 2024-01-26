from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.climate_remote_control.const import DOMAIN


async def test_setup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
):
    assert await async_setup_component(hass, DOMAIN, {}) is True
    await hass.async_block_till_done()
    assert entity_registry.async_get(hass).entities["climate.name_test"]
    assert entity_registry.async_get(hass).entities["button.name_test_swing_vertical"]
