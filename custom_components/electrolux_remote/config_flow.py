"""Config flow for Electrolux integration."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DOMAIN, HOST_RUSKLIMAT, APPCODE_ELECTROLUX, APPCODE_BALLU, CONF_APPCODE
from .api import RusclimatApi, TestApi

_LOGGER = logging.getLogger(__name__)


class FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            valid = await self._test_credentials(
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_APPCODE],
            )

            if valid:
                return self.async_create_entry(title=user_input[CONF_USERNAME], data=user_input)

            self._errors["base"] = "auth"

            return await self._show_config_form(user_input)
        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_HOST, default=HOST_RUSKLIMAT): str,
                vol.Optional(CONF_APPCODE, default=APPCODE_ELECTROLUX): vol.In([APPCODE_ELECTROLUX, APPCODE_BALLU]),
            }),
            errors=self._errors,
        )

    async def _test_credentials(self, host: str, username: str, password: str, appcode: str):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = RusclimatApi(
                host,
                username,
                password,
                appcode,
                session
            )
            await client.login()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False
