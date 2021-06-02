"""Constants for the Electrolux integration."""

NAME = "{{ Electrolux remote }}"
DOMAIN = "electrolux_remote"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.0.1"
ISSUE_URL = "https://github.com/Ailme/home_assistant_electrolux_remote/issues"

CONF_APPCODE = "appcode"

APPCODE_ELECTROLUX = "electrolux"
APPCODE_BALLU = "ballu"
HOST_RUSKLIMAT = "http://dongle.rusklimat.ru"
LANG = "ru"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

DEVICE_CENTURIO = "centurio"
DEVICE_CENTURIO2 = "centurio2"
DEVICE_CONVECTOR = "conv"
DEVICE_CONVECTOR24 = "convector24"
DEVICE_SMART = "smart"
DEVICE_FLOOR = "floor"
DEVICE_REGENCY = "regency"

SERVICE_FETCH_STATE = "fetch_state"

MANUFACTURER = {
    APPCODE_ELECTROLUX: 'Electrolux',
    APPCODE_BALLU: 'Ballu'
}

ICON_BOILER = "mdi:water-boiler"
ICON_CONVECTOR = "mdi:radiator"
ICON_THERMOSTAT = "mdi:thermostat"
