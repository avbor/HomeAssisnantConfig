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

        self._device = Thermostat()
        self._heating = False

        self._update()

    @staticmethod
    def device_type() -> str:
        return "floor"

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self._heating:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        params = {"state": 1 - int(self._heating)}

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

        params = {"mode": HA_PRESET_TO_DEVICE.get(preset_mode, PRESET_COMFORT)}
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
            "tariff_1": self._device.tariff_1,
            "tariff_2": self._device.tariff_2,
            "tariff_3": self._device.tariff_3,
        }

    def _update(self):
        """
        Update local data
        """
        _LOGGER.debug("Thermostat2Climate.update")

        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                self._device.from_json(data)

        self._current_temp = self._device.floor_temp
        self._heating = self._device.state
        self._preset = DEVICE_PRESET_TO_HA.get(self._device.mode.value)
        self._available = self._device.online
        self._target_temperature = self._device.set_temp

    def _update_coordinator_data(self, params: dict) -> None:
        """Update data in coordinator"""
        devices = self.coordinator.data

        for index, device in enumerate(devices):
            if device["uid"] == self._uid:
                for param in params:
                    devices[index][param] = params[param]

        self.coordinator.async_set_updated_data(devices)
        self._update()
