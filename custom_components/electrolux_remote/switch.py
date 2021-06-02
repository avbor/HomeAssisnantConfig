"""Binary sensor."""

import logging

from . import SUPPORTED_DEVICES
from .const import DOMAIN
from .update_coordinator import Coordinator

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices):
    """Setup switch platform."""
    coordinator: Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    try:
        for deviceData in coordinator.data:
            for device in SUPPORTED_DEVICES:
                if deviceData["type"] == device.device_type() and device.support_switches():
                    async_add_devices(device.get_switches(deviceData, coordinator))

    except Exception as err:
        _LOGGER.error(err)
