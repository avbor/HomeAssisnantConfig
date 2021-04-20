"""Thermostat class (type=floor)"""

import logging

from enum import IntEnum

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 0
TEMP_MAX = 40


class State(IntEnum):
    OFF = 0
    ON = 1


class WorkMode(IntEnum):
    MANUAL = 0
    ECO = 1
    COMFORT = 2
    FORSAGE = 3
    VACATION = 4
    CALENDAR = 5


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
        self._error = 0
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
        self._mac = None
        self._room = None  # название помещения
        self._sort = 0
        self._curr_slot = 0
        self._active_slot = 0
        self._slop = 0
        self._curr_scene = 0
        self._curr_scene_id = 0
        self._wait_slot = 0
        self._curr_slot_dropped = 0
        self._curr_scene_dropped = 0
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
