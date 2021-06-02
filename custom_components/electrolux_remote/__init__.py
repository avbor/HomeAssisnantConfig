"""
The Electrolux remote integration.
"""

import logging
import asyncio

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    HOST_RUSKLIMAT,
    STARTUP_MESSAGE,
    CONF_APPCODE,
    SERVICE_FETCH_STATE,
    MANUFACTURER,
)
from .api import ApiInterface, Api
from .update_coordinator import Coordinator

from .devices.centurio import Centurio
from .devices.centurio2 import Centurio2
from .devices.convector import Convector
from .devices.convector2 import Convector2
from .devices.regency import Regency
from .devices.smart import Smart
from .devices.thermostat import Thermostat

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    "climate",
    "switch"
]

SUPPORTED_DEVICES = [
    Centurio,
    Centurio2,
    Convector,
    Convector2,
    Regency,
    Smart,
    Thermostat
]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Electrolux platform."""

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=config[DOMAIN],
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    client: ApiInterface = Api(
        config_entry.data.get(CONF_HOST),
        config_entry.data.get(CONF_USERNAME),
        config_entry.data.get(CONF_PASSWORD),
        config_entry.data.get(CONF_APPCODE),
        async_get_clientsession(hass)
    )

    coordinator = Coordinator(hass, client)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    device_registry = await hass.helpers.device_registry.async_get_registry()
    for deviceData in coordinator.data:
        for device in SUPPORTED_DEVICES:
            if deviceData["type"] == device.device_type():
                device_registry.async_get_or_create(
                    config_entry_id=config_entry.entry_id,
                    manufacturer=MANUFACTURER[config_entry.data.get(CONF_APPCODE)],
                    **device.device_info(deviceData)
                )

    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, platform)
        )

    async def async_update(call=None):
        """Update all data."""
        await coordinator.async_refresh()

    hass.services.async_register(DOMAIN, SERVICE_FETCH_STATE, async_update)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )
    if unload_ok:
        try:
            hass.data[DOMAIN].pop(entry.entry_id)
        except:
            pass

    return unload_ok
