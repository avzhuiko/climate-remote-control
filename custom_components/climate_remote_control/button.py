"""Platform for button integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.components.remote import SERVICE_SEND_COMMAND
from homeassistant.const import CONF_DEVICE, CONF_NAME, CONF_TARGET, Platform
from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_MODE, CONF_MODES, CONF_SWING, DOMAIN, SwingMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices) -> None:
    """Set up"""

    devices = []

    data = entry.data

    target = data[CONF_TARGET]
    device = data[CONF_DEVICE]
    swing = data[CONF_SWING]
    if swing[CONF_MODE] == SwingMode.TOGGLE:
        for mode in swing[CONF_MODES]:
            unique_id = entry.unique_id
            name = data[CONF_NAME]
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
                    # todo: from config
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
