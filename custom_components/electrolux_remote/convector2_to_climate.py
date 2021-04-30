"""Convector2 to Climate class"""

import logging

from typing import Any, Dict, List, Optional

from .climate_base import ClimateBase
from .device_convector2 import (
    Convector2,
    State,
    WorkMode,
    TEMP_MIN,
    TEMP_MAX,
    TEMP_ANTIFROST_MIN,
    TEMP_ANTIFROST_MAX,
)
from .update_coordinator import Coordinator

from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    PRESET_COMFORT,
    PRESET_ECO
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_WHOLE,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_NO_FROST = "no_frost"

SUPPORT_PRESETS = [PRESET_COMFORT, PRESET_ECO, PRESET_NO_FROST]

"""
Supported hvac modes:
- HVAC_MODE_HEAT: Heat to a target temperature (schedule off)
- HVAC_MODE_AUTO: Follow the configured schedule
- HVAC_MODE_OFF:  The device runs in a continuous energy savings mode. If
                  configured as one of the supported hvac modes this mode
                  can be used to activate the vacation mode
"""
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_AUTO]

HA_PRESET_TO_DEVICE = {
    PRESET_COMFORT: WorkMode.COMFORT.value,
    PRESET_ECO: WorkMode.ECO.value,
    PRESET_NO_FROST: WorkMode.NO_FROST.value
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}

DEFAULT_NAME = "Convector"


class Convector2Climate(ClimateBase):
    """Representation of an Climate."""

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
            device=Convector2()
        )

    @staticmethod
    def device_type() -> str:
        return "convector24"

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self._device.state and self._device.heat_mode_auto:
            return HVAC_MODE_AUTO

        if self._device.state:
            return HVAC_MODE_HEAT

        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_AUTO:
            params = {}

            if not self._device.state:
                params["state"] = State.ON.value
            else:
                params["heat_mode"] = 1 - self._device.heat_mode

            result = await self.coordinator.api.set_device_params(self._uid, params)

            if result:
                self._update_coordinator_data(params)
        elif hvac_mode == HVAC_MODE_HEAT:
            params = {"state": 1 - int(self._device.state)}
            result = await self.coordinator.api.set_device_params(self._uid, params)

            if result:
                self._update_coordinator_data(params)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.  Need to be one of CURRENT_HVAC_*.  """
        if self._device.state and self._device.power == 0:
            return CURRENT_HVAC_IDLE
        elif self._device.state:
            return CURRENT_HVAC_HEAT

        return CURRENT_HVAC_IDLE

    async def async_set_preset_mode(self, preset_mode: str) -> None:
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

        params = {}
        if self.preset_mode == PRESET_NO_FROST:
            params["temp_antifrost"] = target_temperature
        elif self.preset_mode == PRESET_ECO:
            target_temperature = target_temperature + self._device.delta_eco
            params["temp_comfort"] = target_temperature
        else:
            params["temp_comfort"] = target_temperature

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def precision(self):
        return PRECISION_WHOLE

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """
        Return additional Thermostat status details
        The information will be available in Home Assistant for reporting
        or automations based on teh provided information
        """
        return {
            "child_lock": self._device.child_lock,
            "heat_mode": self._device.heat_mode_name,
            "sensor_fault": self._device.sensor_fault,
            "window_open": self._device.window_open,
            "mute": self._device.mute,
            "calendar_on": self._device.calendar_on,
            "brightness": self._device.brightness_title,
            "led_off_auto": self._device.led_off_auto,
            "temp_comfort": self._device.temp_comfort,
            "delta_eco": self._device.delta_eco,
            "temp_antifrost": self._device.temp_antifrost,
            "hours": self._device.hours,
            "minutes": self._device.minutes,
            "timer": self._device.timer,
            "power": self._device.power,
            "lcd_on": self._device.lcd_on,
            "time_seconds": self._device.time_seconds,
            "time_minutes": self._device.time_minutes,
            "time_hour": self._device.time_hour,
            "time_day": self._device.time_day,
            "time_month": self._device.time_month,
            "time_year": self._device.time_year,
            "time_weekday": self._device.time_weekday,
            "preset_monday": self._device.preset_monday,
            "preset_tuesday": self._device.preset_tuesday,
            "preset_wednesday": self._device.preset_wednesday,
            "preset_thursday": self._device.preset_thursday,
            "preset_friday": self._device.preset_friday,
            "preset_saturday": self._device.preset_saturday,
            "preset_sunday": self._device.preset_sunday,
            "preset_day_1": self._device.preset_day_1,
            "preset_day_2": self._device.preset_day_2,
            "preset_day_3": self._device.preset_day_3,
            "preset_day_4": self._device.preset_day_4,
            "preset_day_5": self._device.preset_day_5,
            "preset_day_6": self._device.preset_day_6,
            "preset_day_7": self._device.preset_day_7,
            "preset_day_8": self._device.preset_day_8,
            "preset_day_9": self._device.preset_day_9,
            "preset_day_10": self._device.preset_day_10,
            "preset_day_11": self._device.preset_day_11,
            "preset_day_12": self._device.preset_day_12,
            "preset_day_13": self._device.preset_day_13,
            "preset_day_14": self._device.preset_day_14,
            "preset_day_15": self._device.preset_day_15,
            "preset_day_16": self._device.preset_day_16,
            "preset_day_17": self._device.preset_day_17,
            "preset_day_18": self._device.preset_day_18,
            "preset_day_19": self._device.preset_day_19,
            "preset_day_20": self._device.preset_day_20,
            "preset_day_21": self._device.preset_day_21,
            "preset_day_22": self._device.preset_day_22,
            "preset_day_23": self._device.preset_day_23,
            "preset_day_24": self._device.preset_day_24,
            "room": self._device.room,
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
        return self._device.current_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        if self._device.mode is WorkMode.COMFORT:
            return self._device.temp_comfort

        if self._device.mode is WorkMode.ECO:
            return self._device.temp_comfort - self._device.delta_eco

        if self._device.mode is WorkMode.NO_FROST:
            return self._device.temp_antifrost

        return None

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self._device.mode is WorkMode.ECO:
            return TEMP_MIN - self._device.delta_eco

        if self._device.mode is WorkMode.NO_FROST:
            return TEMP_ANTIFROST_MIN

        return TEMP_MIN

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._device.mode is WorkMode.ECO:
            return TEMP_MAX - self._device.delta_eco

        if self._device.mode is WorkMode.NO_FROST:
            return TEMP_ANTIFROST_MAX

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

