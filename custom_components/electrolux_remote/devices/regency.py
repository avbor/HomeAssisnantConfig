"""Regency class (type=regency)"""

import logging

from typing import Any, Dict, List, Optional

from ..enums import State
from ..const import DEVICE_REGENCY, DOMAIN, ICON_BOILER
from ..update_coordinator import Coordinator

from homeassistant.components.climate import ClimateEntity, ENTITY_ID_FORMAT as CLIMATE_ENTITY_ID_FORMAT
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 35
TEMP_MAX = 75

DEFAULT_NAME = "Regency"

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE

"""
Supported hvac modes:
- HVAC_MODE_HEAT: Heat to a target temperature (schedule off)
- HVAC_MODE_OFF:  The device runs in a continuous energy savings mode. If
                  configured as one of the supported hvac modes this mode
                  can be used to activate the vacation mode
"""
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


class Regency:
    def __init__(self):
        self._state = State.OFF.value
        self._online = State.OFF.value
        self._room = None  # название помещения
        self._current_temp = 75
        self._temp_goal = 75
        self._clock_hours = 0
        self._clock_minutes = 0

    def from_json(self, data: dict):
        """Fill self from json data"""
        for key in data:
            setattr(self, f"_{key}", data[key])

    @property
    def room(self) -> str:
        return self._room

    @property
    def online(self) -> bool:
        return int(self._online) == State.ON.value

    @property
    def clock_hours(self) -> int:
        return int(self._clock_hours)

    @property
    def clock_minutes(self) -> int:
        return int(self._clock_minutes)

    @property
    def temp_goal(self) -> int:
        return int(self._temp_goal)

    @property
    def current_temp(self) -> float:
        return float(self._current_temp)

    @property
    def state(self) -> bool:
        return int(self._state) != State.OFF.value

    @staticmethod
    def device_type() -> str:
        return DEVICE_REGENCY

    @staticmethod
    def device_info(data: dict) -> Dict[str, Any]:
        """Device information for entities."""
        return {
            "identifiers": {(DOMAIN, data["uid"])},
            "name": DEFAULT_NAME,
            "suggested_area": data["room"],
            "model": data["type"],
        }

    @staticmethod
    def get_climat_entity(data: dict, coordinator: Coordinator):
        """Create Climat device"""
        return Climate(data["uid"], coordinator)

    @staticmethod
    def support_switches() -> bool:
        return False

    @staticmethod
    def get_switches(data: dict, coordinator: Coordinator):
        """Create Switches"""
        return []


class Climate(CoordinatorEntity, ClimateEntity):
    def __init__(self, uid: str, coordinator: Coordinator):
        """Initialize the climate device"""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._uid = uid
        self._name = f"{DEFAULT_NAME} {uid}"
        self._device = Regency()

        self.entity_id = async_generate_entity_id(
            f"{CLIMATE_ENTITY_ID_FORMAT}", self._name, current_ids=[uid]
        )

        coordinator.async_add_listener(self._update)
        self._update()

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return self.entity_id

    @property
    def name(self) -> str:
        """Return the name of the climate device."""
        return self._name

    @property
    def hvac_mode(self):
        """Return hvac operation """
        if self._device.state:
            return HVAC_MODE_HEAT
        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""

        if hvac_mode == HVAC_MODE_HEAT:
            params = {"state": State.ON.value}
        elif hvac_mode == HVAC_MODE_OFF:
            params = {"state": State.OFF.value}
        else:
            return

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    @property
    def hvac_action(self) -> Optional[str]:
        """Return the current running hvac operation if supported.  Need to be one of CURRENT_HVAC_*.  """
        if self._device.state:
            return CURRENT_HVAC_HEAT
        return CURRENT_HVAC_OFF

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
            "clock_hours": self._device.clock_hours,
            "clock_minutes": self._device.clock_minutes,
            "room": self._device.room,
        }

    @property
    def device_info(self) -> Dict[str, Any]:
        """Device information for entities."""
        return {
            "identifiers": {(DOMAIN, self._uid)},
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
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes. Need to be a subset of HVAC_MODES. """
        return SUPPORT_MODES

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def icon(self) -> str:
        return ICON_BOILER

    def _update_coordinator_data(self, params: dict) -> None:
        """Update data in coordinator"""
        devices = self.coordinator.data

        for index, device in enumerate(devices):
            if device["uid"] == self._uid:
                for param in params:
                    devices[index][param] = params[param]

        self.coordinator.async_set_updated_data(devices)
        self._update()

    def _update(self) -> None:
        """
        Update local data
        """
        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                self._device.from_json(data)
