"""Centurio2 class (type=centurio2)"""

import logging

from typing import Any, Dict, List, Optional
from enum import Enum, IntEnum

from ..enums import State
from ..const import DEVICE_CENTURIO2, DOMAIN, ICON_BOILER
from ..update_coordinator import Coordinator
from ..base_switch import BaseSwitch

from homeassistant.components.climate import ClimateEntity, ENTITY_ID_FORMAT as CLIMATE_ENTITY_ID_FORMAT
from homeassistant.components.switch import SwitchEntity, ENTITY_ID_FORMAT as SWITCH_ENTITY_ID_FORMAT
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import async_generate_entity_id
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
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 35
TEMP_MAX = 75

DEFAULT_NAME = "Centurio IQ 2.0"

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_OFF = 'off'
PRESET_I = 'I'
PRESET_II = 'II'
PRESET_III = 'III'
PRESET_NO_FROST = 'NO_FROST'


SUPPORT_PRESETS = [
    PRESET_OFF,
    PRESET_I,
    PRESET_II,
    PRESET_III,
    PRESET_NO_FROST,
]

"""
Supported hvac modes:
- HVAC_MODE_HEAT: Heat to a target temperature (schedule off)
- HVAC_MODE_OFF:  The device runs in a continuous energy savings mode. If
                  configured as one of the supported hvac modes this mode
                  can be used to activate the vacation mode
"""
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


class WaterMode(IntEnum):
    OFF = 0
    I = 1
    II = 2
    III = 3
    NO_FROST = 5
    NO_CONNECTION = 6


HA_PRESET_TO_DEVICE = {
    PRESET_OFF: WaterMode.OFF.value,
    PRESET_I: WaterMode.I.value,
    PRESET_II: WaterMode.II.value,
    PRESET_III: WaterMode.III.value,
    PRESET_NO_FROST: WaterMode.NO_FROST.value,
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}

class Capacity(IntEnum):
    CAPACITY_0 = 0
    CAPACITY_30 = 30
    CAPACITY_50 = 50
    CAPACITY_80 = 80
    CAPACITY_100 = 100


class Centurio2:
    def __init__(self):
        self._online = State.OFF.value
        self._room = None  # название помещения
        self._mode = WaterMode.OFF.value  # мощность нагрева
        self._current_temp = 75  # текущая температура
        self._temp_goal = 75  # указанная температура
        self._timer = State.OFF.value
        self._timer_hours = 0
        self._timer_minutes = 0
        self._clock_hours = 0
        self._clock_minutes = 0
        self._self_clean = State.OFF.value  # bacteria stop system
        self._volume = Capacity.CAPACITY_100.value
        self._economy_morning = 0
        self._economy_evening = 0
        self._economy_pause = State.OFF.value
        self._power_per_h_1 = 0
        self._power_per_h_2 = 0
        self._power_per_h_3 = 0
        self._tariff_1 = 0
        self._tariff_2 = 0
        self._tariff_3 = 0
        self._minutes_diff = 0
        self._seconds_diff = 0
        self._timezone = 0
        self._timer_hours_store = 0
        self._timer_minutes_store = 0

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
    def volume(self) -> Capacity:
        return Capacity(int(self._volume))

    @property
    def clock_hours(self) -> int:
        return int(self._clock_hours)

    @property
    def clock_minutes(self) -> int:
        return int(self._clock_minutes)

    @property
    def mode(self) -> WaterMode:
        return WaterMode(int(self._mode))

    @property
    def self_clean(self) -> bool:
        return int(self._self_clean) == State.ON.value

    @property
    def timer(self) -> bool:
        return int(self._timer) == State.ON.value

    @property
    def temp_goal(self) -> int:
        return int(self._temp_goal)

    @property
    def timer_hours(self) -> int:
        return int(self._timer_hours)

    @property
    def timer_minutes(self) -> int:
        return int(self._timer_minutes)

    @property
    def economy_evening(self) -> int:
        return int(self._economy_evening)

    @property
    def economy_morning(self) -> int:
        return int(self._economy_morning)

    @property
    def timer_hours_store(self) -> int:
        return int(self._timer_hours_store)

    @property
    def timer_minutes_store(self) -> int:
        return int(self._timer_minutes_store)

    @property
    def economy_pause(self) -> bool:
        return int(self._economy_pause) == State.ON.value

    @property
    def economy_state(self) -> bool:
        return (int(self._economy_morning) + int(self._economy_evening)) > 0

    @property
    def current_temp(self) -> float:
        return float(self._current_temp)

    @property
    def power_per_h_1(self) -> int:
        return int(self._power_per_h_1)

    @property
    def power_per_h_2(self) -> int:
        return int(self._power_per_h_2)

    @property
    def power_per_h_3(self) -> int:
        return int(self._power_per_h_3)

    @property
    def timezone(self) -> int:
        return int(self._timezone)

    @property
    def minutes_diff(self) -> int:
        return int(self._minutes_diff)

    @property
    def seconds_diff(self) -> int:
        return int(self._seconds_diff)

    @staticmethod
    def device_type() -> str:
        return DEVICE_CENTURIO2

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
                name=f"{DEFAULT_NAME} {data['uid']} Bacteria stop system",
                icon_on="mdi:ghost",
                icon_off="mdi:ghost-off",
                device=Centurio2(),
                param_name="self_clean",
                property_name="self_clean",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            Timer(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"{DEFAULT_NAME} {data['uid']} Timer",
                device=Centurio2(),
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"{DEFAULT_NAME} {data['uid']} Economy pause",
                icon_on="mdi:pause",
                icon_off="mdi:play",
                device=Centurio2(),
                param_name="economy_pause",
                property_name="economy_pause",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),
        ]


class Climate(CoordinatorEntity, ClimateEntity):
    def __init__(self, uid: str, coordinator: Coordinator):
        """Initialize the climate device"""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._uid = uid
        self._name = f"{DEFAULT_NAME} {uid}"
        self._device = Centurio2()

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
        if self.preset_mode == PRESET_OFF and not self._device.timer:
            return HVAC_MODE_OFF
        return HVAC_MODE_HEAT

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_HEAT:
            params = {"mode": self._prev_mode if self._prev_mode > 0 else WaterMode.I.value}
        elif hvac_mode == HVAC_MODE_OFF:
            self._prev_mode = self._device.mode

            params = {"mode": WaterMode.OFF.value, "timer": State.OFF.value}
        else:
            return

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
            "timer_hours": self._device.timer_hours,
            "timer_minutes": self._device.timer_minutes,
            "clock_hours": self._device.clock_hours,
            "clock_minutes": self._device.clock_minutes,
            "self_clean": self._device.self_clean,
            "volume": self._device.volume.value,
            "economy_state": self._device.economy_state,
            "economy_morning": self._device.economy_morning,
            "economy_evening": self._device.economy_evening,
            "economy_pause": self._device.economy_pause,
            "power_per_h_1": self._device.power_per_h_1,
            "power_per_h_2": self._device.power_per_h_2,
            "power_per_h_3": self._device.power_per_h_3,
            "timezone": self._device.timezone,
            "timer_hours_store": self._device.timer_hours_store,
            "timer_minutes_store": self._device.timer_minutes_store,
            "minutes_diff": self._device.minutes_diff,
            "seconds_diff": self._device.seconds_diff,
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


class Timer(CoordinatorEntity, SwitchEntity):
    def __init__(
        self,
        uid: str,
        name: str,
        coordinator: Coordinator,
        device
    ):
        """
        Initialize
        """
        self.coordinator = coordinator

        super().__init__(coordinator)

        self._uid = uid
        self._name = name
        self._icon_on = "mdi:timer"
        self._icon_off = "mdi:timer-off"
        self._device = device

        self.entity_id = async_generate_entity_id(
            f"{SWITCH_ENTITY_ID_FORMAT}", self._name, current_ids=[uid]
        )

        coordinator.async_add_listener(self._update)
        self._update()

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return self.entity_id

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def device_info(self) -> Dict[str, Any]:
        """Device information for entities."""
        return {
            "identifiers": {(DOMAIN, self._uid)},
        }

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return self._icon_on if self.is_on else self._icon_off

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self._device.timer

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        if self._device.timer:
            return

        params = {"timer": State.ON.value, "mode": WaterMode.OFF.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        if not self._device.timer:
            return

        params = {"timer": State.OFF.value, "mode": WaterMode.I.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    async def async_toggle(self) -> None:
        """Turn the entity off."""
        if self._device.timer:
            params = {"timer": State.OFF.value, "mode": WaterMode.I.value}
        else:
            params = {"timer": State.ON.value, "mode": WaterMode.OFF.value}

        result = await self.coordinator.api.set_device_params(self._uid, params)

        if result:
            self._update_coordinator_data(params)

    def _update(self) -> None:
        """
        Update local data
        """
        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                self._device.from_json(data)

    def _update_coordinator_data(self, params: dict) -> None:
        """Update data in coordinator"""
        devices = self.coordinator.data

        for index, device in enumerate(devices):
            if device["uid"] == self._uid:
                for param in params:
                    devices[index][param] = params[param]

        self.coordinator.async_set_updated_data(devices)
        self._update()
