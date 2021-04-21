"""Centurio class (type=centurio)"""

import logging

from enum import Enum, IntEnum

_LOGGER = logging.getLogger(__name__)

TEMP_MIN = 30
TEMP_MAX = 75


class State(IntEnum):
    OFF = 0
    ON = 1


class WaterSelfCleanState(Enum):
    OFF = 'off'
    WAIT = 'wait'
    WAIT_ONLINE = 'wait_online'
    HEAT = 'heat'
    HEAT_ONLINE = 'heat_online'
    HOLD = 'hold'
    HOLD_ONLINE = 'hold_online'
    PASSED = 'passed'
    DISABLED = 'disabled'


class Capacity(IntEnum):
    CAPACITY_30 = 30
    CAPACITY_50 = 50
    CAPACITY_80 = 80
    CAPACITY_100 = 100


class WaterMode(IntEnum):
    OFF = 0
    HALF = 1
    FULL = 2
    NO_CONNECTION = 3


class Centurio:
    def __init__(self):
        self._online = State.OFF.value
        self._room = None  # название помещения
        self._mode = WaterMode.OFF.value  # мощность нагрева
        self._current_temp = 75
        self._temp_goal = 75
        self._timer = State.OFF.value
        self._timer_hours = 0
        self._timer_minutes = 0
        self._clock_hours = 0
        self._clock_minutes = 0
        self._self_clean = State.OFF.value  # bacteria stop system
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
        self._sort = 0
        self._curr_slot = 0
        self._active_slot = 0
        self._slop = 0
        self._curr_scene = 0
        self._curr_scene_id = 0
        self._wait_slot = 0
        self._curr_slot_dropped = 0
        self._curr_scene_dropped = 0

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
    def economy_state(self) -> bool:
        return (int(self._economy_morning) + int(self._economy_evening)) > 0

    @property
    def current_temp(self) -> float:
        return float(self._current_temp)

    @property
    def self_clean_state(self) -> WaterSelfCleanState:
        return WaterSelfCleanState(self._self_clean_state)

    @property
    def power_per_h_1(self) -> int:
        return int(self._power_per_h_1)

    @property
    def power_per_h_2(self) -> int:
        return int(self._power_per_h_2)

    @property
    def timezone(self) -> int:
        return int(self._timezone)
