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
    CURRENT_HVAC_OFF,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
)


_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_OFF = 'off'
PRESET_HALF = 'I'
PRESET_FULL = 'II'


SUPPORT_PRESETS = [
    PRESET_OFF,
    PRESET_HALF,
    PRESET_FULL,
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
        self.coordinator = coordinator

        super().__init__(
            coordinator=coordinator,
            uid=uid,
            name=f"{DEFAULT_NAME} {uid}",
            support_flags=SUPPORT_FLAGS,
            support_modes=SUPPORT_MODES,
            support_presets=SUPPORT_PRESETS,
            device=Centurio()
        )

    @staticmethod
    def device_type() -> str:
        return "centurio"

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self.preset_mode == PRESET_OFF:
            return HVAC_MODE_OFF
        return HVAC_MODE_HEAT

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        params = {"mode": 1 - int(self._device.mode.value > 0)}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.  Need to be one of CURRENT_HVAC_*.  """
        if self.preset_mode == PRESET_OFF:
            return CURRENT_HVAC_OFF
        return CURRENT_HVAC_HEAT

    async def async_set_preset_mode(self, preset_mode) -> None:
        """Set a new preset mode. If preset_mode is None, then revert to auto."""
        _LOGGER.debug(preset_mode)

        if self.preset_mode == preset_mode:
            return

        if preset_mode not in SUPPORT_PRESETS:
            _LOGGER.warning(
                "%s: set preset mode to '%s' is not supported. "
                "Supported preset modes are %s",
                self._name, preset_mode, SUPPORT_PRESETS)
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

        if (target_temperature < self.min_temp or
                target_temperature > self.max_temp):
            _LOGGER.warning(
                "%s: set target temperature to %s°C is not supported. "
                "The temperature can be set between %s°C and %s°C",
                self._name, str(target_temperature),
                self.min_temp, self.max_temp)
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

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if self._device.mode.value > 0:
            return

        params = {"mode": WaterMode.HALF.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if not self._device.mode.value > 0:
            return

        params = {"mode": WaterMode.OFF.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._device.online

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._device.current_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        return self._device.temp_goal

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return TEMP_MIN

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return TEMP_MAX

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return DEVICE_PRESET_TO_HA.get(self._device.mode.value)

    def _update(self) -> None:
        """
        Update local data
        """
        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                _LOGGER.debug(data)
                self._device.from_json(data)

