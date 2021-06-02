"""Thermostat class (type=floor)"""

import logging

from typing import Any, Dict, List, Optional
from enum import Enum, IntEnum

from ..enums import State
from ..const import DEVICE_FLOOR, DOMAIN, ICON_THERMOSTAT
from ..update_coordinator import Coordinator

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
    PRESET_COMFORT,
    PRESET_ECO,
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 0
TEMP_MAX = 40

DEFAULT_NAME = "Thermostat"

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

PRESET_CALENDAR = "Calendar"
PRESET_MANUAL = "Manual"
PRESET_FORSAGE = "Forsage"
PRESET_VACATION = "Vacation"

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
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_OFF]


class WorkMode(IntEnum):
    MANUAL = 0
    ECO = 1
    COMFORT = 2
    FORSAGE = 3
    VACATION = 4
    CALENDAR = 5


HA_PRESET_TO_DEVICE = {
    PRESET_CALENDAR: WorkMode.CALENDAR.value,
    PRESET_MANUAL: WorkMode.MANUAL.value,
    PRESET_COMFORT: WorkMode.COMFORT.value,
    PRESET_ECO: WorkMode.ECO.value,
    PRESET_FORSAGE: WorkMode.FORSAGE.value,
    PRESET_VACATION: WorkMode.VACATION.value,
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}


class FloorCoverType(IntEnum):
    TILE = 0
    CARPET = 1
    LAMINATE = 2
    LINOLEUM = 3
    PARQUET = 4


# датчик температуры
class FloorSensorMode(IntEnum):
    FLOOR = 0  # датчик пола
    AIR = 1  # датчик воздуха
    FLOOR_AND_AIR = 2  # датчик пола и воздуха


# сопротивление датчика пола
class FloorSensorType(IntEnum):
    CALEO_5 = 0
    TEPLOLUX_6 = 1
    ELECTROLUX_10 = 2
    RAYCHEM_13 = 3
    DEVI_15 = 4
    EBERLE_33 = 5


class Thermostat:
    def __init__(self):
        self._state = State.OFF.value
        self._online = State.OFF.value
        self._set_temp = 240  # выставленная температура
        self._room_temp = 275  # комнатная температура
        self._set_room_temp = 38
        self._floor_temp = 304  # температура пола
        self._sensor_mode = FloorSensorMode.FLOOR_AND_AIR  # датчик температуры
        self._sensor_type = FloorSensorType.CALEO_5.value  # сопротивление датчика пола
        self._floor_temp_limit = 450
        self._antifreeze_temp = 0
        self._led_light = None  # использование подсветки
        self._heating_on = None  # нагрев
        self._open_window = None    # открытое окно
        self._button_lock = State.OFF  # блокировка ручного управления
        self._pol_res_set = State.OFF  # в приложении переменная называется firstSetUp
        self._pol_type = FloorCoverType.TILE.value  # тип покрытия пола
        self._mode = WorkMode.COMFORT.value  # режим работы
        self._pol_matrix = {}
        self._power_per_h = 0   # потребление
        self._tariff_1 = 0
        self._tariff_2 = 0
        self._tariff_3 = 0
        self._timezone = 0
        self._hours = 0
        self._minutes = 0
        self._room = None  # название помещения
        self._set_temp_1 = 0
        self._set_temp_0 = 240
        self._room_temp_1 = 1
        self._room_temp_0 = 19
        self._set_room_temp_1 = 0
        self._set_room_temp_0 = 38
        self._floor_temp_1 = 1
        self._floor_temp_0 = 48
        self._floor_temp_limit_1 = 1
        self._floor_temp_limit_0 = 194
        self._antifreeze_temp_1 = 0
        self._antifreeze_temp_0 = 0

    def from_json(self, data: dict):
        """Fill self from json data"""
        for key in data:
            setattr(self, f"_{key}", data[key])

    @property
    def open_window(self) -> bool:
        return int(self._open_window) == State.ON.value

    @property
    def button_lock(self) -> bool:
        return int(self._button_lock) == State.ON.value

    @property
    def room(self) -> str:
        return self._room

    @property
    def mode(self) -> WorkMode:
        return WorkMode(int(self._mode))

    @property
    def pol_type(self) -> FloorCoverType:
        return FloorCoverType(int(self._pol_type))

    @property
    def room_temp(self) -> float:
        return float(self._room_temp) / 10

    @property
    def floor_temp(self) -> float:
        return float(self._floor_temp) / 10

    @property
    def floor_temp_0(self) -> float:
        return float(self._floor_temp_0) / 10

    @property
    def set_temp(self) -> float:
        return float(self._set_temp) / 10

    @property
    def power_per_h(self) -> float:
        return float(self._power_per_h)

    @property
    def antifreeze_temp(self) -> float:
        return float(self._antifreeze_temp)

    @property
    def tariff_1(self) -> float:
        return float(self._tariff_1)

    @property
    def tariff_2(self) -> float:
        return float(self._tariff_2)

    @property
    def tariff_3(self) -> float:
        return float(self._tariff_3)

    @property
    def sensor_mode(self) -> FloorSensorMode:
        return FloorSensorMode(int(self._sensor_mode))

    @property
    def sensor_type(self) -> FloorSensorType:
        return FloorSensorType(int(self._sensor_type))

    @property
    def heating_on(self) -> bool:
        return self._heating_on == State.ON.value

    @property
    def led_light(self) -> bool:
        return self._led_light == State.ON.value

    @property
    def state(self) -> bool:
        return int(self._state) == State.ON.value

    @property
    def online(self) -> bool:
        return int(self._online) == State.ON.value

    @staticmethod
    def device_type() -> str:
        return DEVICE_FLOOR

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
        self._device = Thermostat()

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
        return ICON_THERMOSTAT

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

