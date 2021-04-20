"""Exceptions collection"""

from homeassistant import exceptions


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class UserNotFound(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid auth."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid auth."""


class InvalidHost(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid host."""


class InvalidResponse(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid response."""


class DeviceUnavailable(exceptions.HomeAssistantError):
    """Error to indicate there is an device unavailable."""


class EnexpectedError(exceptions.HomeAssistantError):
    """Error to indicate there is an unexpected error."""
