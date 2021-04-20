"""Boiler class (type=floor)"""

import logging

from enum import IntEnum

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 0
TEMP_MAX = 40


class State(IntEnum):
    OFF = 0
    ON = 1


class WaterSelfCleanState(IntEnum):
    OFF = 0
    WAIT = 1
    WAIT_ONLINE = 2
    HEAT = 3
    HEAT_ONLINE = 4
    HOLD = 5
    HOLD_ONLINE = 6
    PASSED = 7
    DISABLED = 8


class Capacity(IntEnum):
    CAPACITY_30 = 0
    CAPACITY_50 = 1
    CAPACITY_80 = 2
    CAPACITY_100 = 3


class WaterMode(IntEnum):
    OFF = 0
    HALF = 1
    FULL = 2
    NO_CONNECTION = 3


class Boiler:
    def __init__(self):
        self._state = State.OFF.value
        self._online = State.OFF.value
        self._room = None  # название помещения
        self._mode = None  # режим работы
        self._current_temp = 75
        self._temp_goal = 75
        self._timer = State.OFF.value
        self._timer_hours = 0
        self._timer_minutes = 0
        self._clock_hours = 0
        self._clock_minutes = 0
        self._self_clean = State.OFF.value
        self._volume = Capacity.CAPACITY_100.value
        self._error = 0
        self._code = 0
        self._self_clean_state = WaterSelfCleanState.OFF.value
        self._economy_morning = 0
        self._economy_evening = 0
        self._economy_pause = State.OFF.value
        self._power_per_h_1 = 0
        self._power_per_h_2 = 0
        self._tariff_1 = 0
        self._tariff_2 = 0
        self._tariff_3 = 0
        self._minutes_diff = 0
        self._timezone = 0
        self._timer_hours_store = 0
        self._timer_minutes_store = 0
        self._seconds_diff = 0
        self._mac = None
        self._sort = 0
        self._curr_slot = 0
        self._active_slot = 0
        self._curr_scene = 0
        self._curr_scene_id = 0
        self._wait_slot = 0
        self._curr_slot_dropped = 0
        self._curr_scene_dropped = 0
        self._undefined1 = 0
        self._undefined2 = 0
        self._undefined3 = 0
        self._undefined4 = 0
        self._uv = 0
        self._ion = 0
        self._timer_off = 0
        self._timer_on = 0
        self._co2_sensor_connect = 0
        self._lock = State.OFF.value
        self._indoor = State.OFF.value
        self._timer_inf = State.OFF.value
        self._timer_auto = State.OFF.value
        self._timer_sleep = State.OFF.value
        self._error_code = 0
        self._filter_s = 0
        self._timer_on_hours = 0
        self._timer_on_minutes = 0
        self._timer_off_hours = 0
        self._timer_off_minutes = 0
        self._hours = 0
        self._minutes = 0
        self._pm2_5_index = 0
        self._co2date1 = 0
        self._co2date2 = 0
        self._speed = 0
        self._windows_temp = 0
        self._ptc_heat = 0
        self._slop = 0

    def from_json(self, data: dict):
        """Fill self from json data"""
        for key in data:
            setattr(self, f"_{key}", data[key])

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
        return int(self._temp_goal)

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
    def current_temp(self) -> float:
        return float(self._current_temp)
