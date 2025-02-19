"""Platform for button integration."""

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity
from homeassistant.components.remote import SERVICE_SEND_COMMAND
from homeassistant.const import CONF_DEVICE, CONF_TARGET, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_MODE, CONF_MODES, CONF_SWING, DOMAIN, SwingMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up buttons"""
    if config_entry.options == {}:
        _LOGGER.debug("Climate remote control platform is not configured, skip.")
        return
    devices = []

    options = config_entry.options

    unique_id = config_entry.unique_id
    name = config_entry.title

    target = options[CONF_TARGET]
    device = options[CONF_DEVICE]
    swing = options[CONF_SWING]
    if swing[CONF_MODE] == SwingMode.TOGGLE:
        for mode in swing[CONF_MODES]:
            devices.append(
                AcRemoteSwingToggle(
                    unique_id=unique_id,
                    name=name,
                    target=target,
                    device=device,
                    mode=mode,
                )
            )

    async_add_devices(devices)


class AcRemoteSwingToggle(ButtonEntity):
    """Representation of swing toggle button for one mode"""

    _attr_translation_key = DOMAIN
    _attr_has_entity_name = True

    target: dict[str, Any] = {}
    device: str
    mode: str

    def __init__(
        self,
        unique_id,
        name,
        target,
        device,
        mode,
    ) -> None:
        """Initialize."""
        self.device = device
        self._attr_unique_id = unique_id

        self.target = target
        self.mode = mode

        self._attr_name = "swing " + mode
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            manufacturer="avzhuiko",
            name=name,
        )

    def press(self) -> None:
        services = self.hass.services
        command = "swing:" + self.mode
        _LOGGER.debug(
            "Calling service %s.%s, with command=%s, target=%s",
            Platform.REMOTE,
            SERVICE_SEND_COMMAND,
            command,
            self.target,
        )
        try:
            services.call(
                domain=Platform.REMOTE,
                service=SERVICE_SEND_COMMAND,
                service_data={
                    "command": command,
                    "device": self.device,
                    "num_repeats": 1,
                    "delay_secs": 0,
                    "hold_secs": 0,
                },
                target=self.target,
                blocking=True,
            )
        except ValueError:
            """todo: send permanent notification to learn new command"""
            _LOGGER.warning(
                'Command "%s" for device "%s" not found. You should learn it.',
                command,
                self.device,
            )
