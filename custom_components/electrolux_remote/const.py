"""Constants for the Electrolux integration."""

NAME = "{{ Electrolux remote }}"
DOMAIN = "electrolux_remote"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.7"
ISSUE_URL = "https://github.com/Ailme/home_assistant_electrolux_remote/issues"

CONF_APPCODE = "appcode"

APPCODE_ELECTROLUX = "electrolux"
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
