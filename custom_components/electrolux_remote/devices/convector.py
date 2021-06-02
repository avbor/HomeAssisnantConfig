"""Convector class (type=convector24)"""

import logging

from typing import Any, Dict, List, Optional
from enum import Enum, IntEnum

from ..enums import State
from ..const import DEVICE_CONVECTOR, DOMAIN, ICON_CONVECTOR
from ..update_coordinator import Coordinator
from ..base_switch import BaseSwitch

from homeassistant.components.climate import ClimateEntity, ENTITY_ID_FORMAT as CLIMATE_ENTITY_ID_FORMAT
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_OFF,
    CURRENT_HVAC_IDLE,
    PRESET_COMFORT,
    PRESET_ECO
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 5
TEMP_MAX = 35

DEFAULT_NAME = "Convector"

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
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


class WorkMode(IntEnum):
    COMFORT = 1  # Day
    ECO = 2  # Night
    NO_FROST = 3


HA_PRESET_TO_DEVICE = {
    PRESET_COMFORT: WorkMode.COMFORT.value,
    PRESET_ECO: WorkMode.ECO.value,
    PRESET_NO_FROST: WorkMode.NO_FROST.value
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}


class PowerMode(IntEnum):
    POWER_0 = 0
    POWER_1 = 1
    POWER_2 = 2
    POWER_3 = 3
    POWER_4 = 4
    POWER_5 = 5


class Convector:
    def __init__(self):
        self._state = State.OFF.value
        self._online = State.OFF.value
        self._temp_goal = 24
        self._current_temp = 0
        self._power = PowerMode.POWER_0.value   # мощность обогрева
        self._mode = WorkMode.COMFORT.value  # режим работы
        self._led = State.OFF  # подсветка 0 - вкл, 1 - выкл
        # таймер
        self._hours = 0
        self._minutes = 0
        self._timer = State.OFF.value

        self._room = None   # название помещения
        self._lock = State.OFF.value    # режим блокировки

    def from_json(self, data: dict):
        """Fill self from json data"""
        for key in data:
            setattr(self, f"_{key}", data[key])

    @property
    def current_temp(self) -> float:
        return float(self._current_temp)

    @property
    def mode(self) -> WorkMode:
        return WorkMode(int(self._mode))

    @property
    def temp_goal(self) -> float:
        return float(self._temp_goal)

    @property
    def power(self) -> int:
        return int(self._power)

    @property
    def lock(self) -> bool:
        return int(self._lock) == State.ON.value

    @property
    def room(self) -> str:
        return self._room

    @property
    def state(self) -> bool:
        return int(self._state) == State.ON.value

    @property
    def online(self) -> bool:
        return int(self._online) == State.ON.value

    @property
    def delta_eco(self) -> int:
        return 4

    @property
    def hours(self) -> int:
        return int(self._hours)

    @property
    def minutes(self) -> int:
        return int(self._minutes)

    @property
    def timer(self) -> bool:
        return int(self._timer) == State.ON.value

    @property
    def led(self) -> bool:
        return int(self._led) == State.OFF.value

    @staticmethod
    def device_type() -> str:
        return DEVICE_CONVECTOR

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
        return True

    @staticmethod
    def get_switches(data: dict, coordinator: Coordinator):
        """Create Switches"""
        return [
            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Led",
                icon_on="mdi:led-on",
                icon_off="mdi:led-off",
                device=Convector(),
                param_name="led",
                property_name="led",
                value_on=State.OFF.value,
                value_off=State.ON.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Lock",
                icon_on="mdi:lock",
                icon_off="mdi:lock-open",
                device=Convector(),
                param_name="lock",
                property_name="lock",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Timer",
                icon_on="mdi:timer",
                icon_off="mdi:timer-off",
                device=Convector(),
                param_name="timer",
                property_name="timer",
                value_on=State.ON.value,
                value_off=State.OFF.value
            )
        ]


class Climate(CoordinatorEntity, ClimateEntity):
    def __init__(self, uid: str, coordinator: Coordinator):
        """Initialize the climate device"""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._uid = uid
        self._name = f"{DEFAULT_NAME} {uid}"
        self._device = Convector()

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
        if hvac_mode == HVAC_MODE_HEAT and not self._device.state:
            params = {"state": 1}
        elif hvac_mode == HVAC_MODE_OFF and self._device.state:
            params = {"state": 0}
        else:
            return

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

        return CURRENT_HVAC_OFF

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
            "hours": self._device.hours,
            "minutes": self._device.minutes,
            "timer": self._device.timer,
            "power": self._device.power,
            "room": self._device.room,
            "lock": self._device.lock,
            "led": self._device.led,
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
        if self._device.mode is WorkMode.NO_FROST:
            return TEMP_MIN

        return self._device.temp_goal

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return TEMP_MIN

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._device.mode is WorkMode.ECO:
            return TEMP_MAX - self._device.delta_eco

        if self._device.mode is WorkMode.NO_FROST:
            return TEMP_MIN

        return TEMP_MAX

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return DEVICE_PRESET_TO_HA.get(self._device.mode.value)

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
    def preset_modes(self) -> List[str]:
        """Return a list of available preset modes."""
        return SUPPORT_PRESETS

    @property
    def icon(self) -> str:
        return ICON_CONVECTOR

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


