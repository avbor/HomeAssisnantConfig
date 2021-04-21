"""Centurio to Climate class"""

import logging

from typing import Any, Dict, List, Optional

from .climate_base import ClimateBase
from .device_centurio import (
    Centurio,
    WaterMode,
    TEMP_MIN,
    TEMP_MAX,
)
from .update_coordinator import Coordinator

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
)


_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_OFF = 'off'
PRESET_HALF = 'half'
PRESET_FULL = 'full'
PRESET_NO_CONNECTION = 'no_connection'


SUPPORT_PRESETS = [
    PRESET_OFF,
    PRESET_HALF,
    PRESET_FULL,
    PRESET_NO_CONNECTION,
]

"""
Supported hvac modes:
- HVAC_MODE_HEAT: Heat to a target temperature (schedule off)
- HVAC_MODE_OFF:  The device runs in a continuous energy savings mode. If
                  configured as one of the supported hvac modes this mode
                  can be used to activate the vacation mode
"""
SUPPORT_MODES = [HVAC_MODE_HEAT]

HA_PRESET_TO_DEVICE = {
    PRESET_OFF: WaterMode.OFF.value,
    PRESET_HALF: WaterMode.HALF.value,
    PRESET_FULL: WaterMode.FULL.value,
    PRESET_NO_CONNECTION: WaterMode.NO_CONNECTION.value,
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}

DEFAULT_NAME = "Centurio IQ"


class Centurio2Climate(ClimateBase):
    """
    Representation of a climate device
    """

    def __init__(self, uid: str, coordinator: Coordinator):
        """
        Initialize the climate device
        """
        super().__init__(
            coordinator=coordinator,
            uid=uid,
            name=f"{DEFAULT_NAME} {uid}",
            temp_min=TEMP_MIN,
            temp_max=TEMP_MAX,
            support_flags=SUPPORT_FLAGS,
            support_modes=SUPPORT_MODES,
            support_presets=SUPPORT_PRESETS,
        )

        self.coordinator = coordinator
        coordinator.async_add_listener(self._update)

        self._device = Centurio()
        self._heating = False

        self._update()

    @staticmethod
    def device_type() -> str:
        return "centurio"

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self._heating:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        params = {"mode": 1 - int(self._heating)}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.  Need to be one of CURRENT_HVAC_*.  """
        if self._heating:
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE

    async def async_set_preset_mode(self, preset_mode) -> None:
        """Set a new preset mode. If preset_mode is None, then revert to auto."""

        if self._preset == preset_mode:
            return

        if not preset_mode.lower() in SUPPORT_PRESETS:
            _LOGGER.warning(
                "%s: set preset mode to '%s' is not supported. "
                "Supported preset modes are %s",
                self._name, str(preset_mode.lower()), SUPPORT_PRESETS)
            return None

        params = {"mode": HA_PRESET_TO_DEVICE.get(preset_mode, PRESET_OFF)}
        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""

        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if target_temperature is None:
            return

        if (target_temperature < self._min_temp or
                target_temperature > self._max_temp):
            _LOGGER.warning(
                "%s: set target temperature to %s°C is not supported. "
                "The temperature can be set between %s°C and %s°C",
                self._name, str(target_temperature),
                self._min_temp, self._max_temp)
            return

        params = {"temp_goal": target_temperature}
        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def precision(self):
        return PRECISION_TENTHS

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """
        Return additional Thermostat status details
        The information will be available in Home Assistant for reporting
        or automations based on teh provided information
        """
        return {
            "timer": self._device.timer,
            "hours": self._device.timer_hours,
            "minutes": self._device.timer_minutes,
            "clock_hours": self._device.clock_hours,
            "clock_minutes": self._device.clock_minutes,
            "self_clean": self._device.self_clean,
            "volume": self._device.volume.value,
            "self_clean_state": self._device.self_clean_state.value,
            "economy_state": self._device.economy_state,
            "economy_morning": self._device.economy_morning,
            "economy_evening": self._device.economy_evening,
            "economy_pause": self._device.economy_pause,
            "power_per_h_1": self._device.power_per_h_1,
            "power_per_h_2": self._device.power_per_h_2,
            "timezone": self._device.timezone,
            "timer_hours_store": self._device.timer_hours_store,
            "timer_minutes_store": self._device.timer_minutes_store,
            "room": self._device.room,
        }

    def _update(self):
        """
        Update local data
        """
        _LOGGER.debug("Centurio2Climate.update")

        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                _LOGGER.debug(data)
                self._device.from_json(data)

        self._current_temp = self._device.current_temp
        self._heating = self._device.mode.value > 0
        self._preset = DEVICE_PRESET_TO_HA.get(self._device.mode.value)
        self._available = self._device.online
        self._target_temperature = self._device.temp_goal

    def _update_coordinator_data(self, params: dict) -> None:
        """Update data in coordinator"""
        devices = self.coordinator.data

        for index, device in enumerate(devices):
            if device["uid"] == self._uid:
                for param in params:
                    devices[index][param] = params[param]

        self.coordinator.async_set_updated_data(devices)
        self._update()
