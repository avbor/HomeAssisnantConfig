"""Thermostat to Climate class"""

import logging

from typing import Any, Dict, List, Optional

from .climate_base import ClimateBase
from .device_thermostat import (
    Thermostat,
    WorkMode,
    State,
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
    PRESET_COMFORT,
    PRESET_ECO,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
)


_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_CALENDAR = "calendar"
PRESET_MANUAL = "manual"
PRESET_FORSAGE = "forsage"
PRESET_VACATION = "vacation"

SUPPORT_PRESETS = [
    PRESET_CALENDAR,
    PRESET_MANUAL,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_FORSAGE,
    PRESET_VACATION,
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
    PRESET_CALENDAR: WorkMode.CALENDAR.value,
    PRESET_MANUAL: WorkMode.MANUAL.value,
    PRESET_COMFORT: WorkMode.COMFORT.value,
    PRESET_ECO: WorkMode.ECO.value,
    PRESET_FORSAGE: WorkMode.FORSAGE.value,
    PRESET_VACATION: WorkMode.VACATION.value,
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}

DEFAULT_NAME = "Thermostat"


class Thermostat2Climate(ClimateBase):
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
            device=Thermostat()
        )

    @staticmethod
    def device_type() -> str:
        return "floor"

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self._device.state:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        params = {"state": 1 - int(self._device.state)}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.  Need to be one of CURRENT_HVAC_*.  """
        if self._device.state:
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_IDLE

    async def async_set_preset_mode(self, preset_mode) -> None:
        """Set a new preset mode. If preset_mode is None, then revert to auto."""

        if self.preset_mode == preset_mode:
            return

        if not preset_mode.lower() in SUPPORT_PRESETS:
            _LOGGER.warning(
                "%s: set preset mode to '%s' is not supported. "
                "Supported preset modes are %s",
                self._name, str(preset_mode.lower()), SUPPORT_PRESETS)
            return None

        params = {"mode": HA_PRESET_TO_DEVICE.get(preset_mode, PRESET_COMFORT)}
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

        params = {"set_temp": target_temperature * 10}
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
            "room_temp": self._device.room_temp,
            "floor_temp": self._device.floor_temp,
            "open_window": self._device.open_window,
            "sensor_mode": self._device.sensor_mode.name.lower(),
            "sensor_type": self._device.sensor_type.name.lower(),
            "button_lock": self._device.button_lock,
            "floor_cover_type": self._device.pol_type.name.lower(),
            "heating": self._device.heating_on,
            "led_light": self._device.led_light,
            "power_per_h": self._device.power_per_h,
            "antifreeze_temp": self._device.antifreeze_temp,
            "antifreeze_mode": self._device.antifreeze_temp > 0,
        }

    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        if self._device.state:
            return

        params = {"state": State.ON.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if not self._device.state:
            return

        params = {"state": State.OFF.value}

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
        return self._device.floor_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        return self._device.set_temp

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
                self._device.from_json(data)
