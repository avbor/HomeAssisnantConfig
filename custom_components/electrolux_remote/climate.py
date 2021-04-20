"""Add support Climate devices"""

import logging

from .convector2_to_climate import Convector2Climate
from .thermostat_to_climate import Thermostat2Climate
from .boiler_to_climate import Boiler2Climate

from .const import DOMAIN
from .update_coordinator import Coordinator

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices):
    """
    Setup the climate platform
    """
    coordinator: Coordinator = hass.data[DOMAIN][config_entry.entry_id]

    devices = []

    try:
        for deviceData in coordinator.data:
            _LOGGER.debug(f"device: {deviceData}")

            if deviceData["type"] == Convector2Climate.device_type():
                device = Convector2Climate(deviceData["uid"], coordinator)
                devices.append(device)

            if deviceData["type"] == Thermostat2Climate.device_type():
                device = Thermostat2Climate(deviceData["uid"], coordinator)
                devices.append(device)

            if deviceData["type"] == Boiler2Climate.device_type():
                device = Boiler2Climate(deviceData["uid"], coordinator)
                devices.append(device)
    except Exception as err:
        _LOGGER.error(err)

    if devices:
        async_add_devices(devices)
