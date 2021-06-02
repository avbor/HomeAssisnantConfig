"""Convector2 class (type=convector24)"""

import logging

from typing import Any, Dict, List, Optional
from enum import Enum, IntEnum

from ..enums import State
from ..const import DEVICE_CONVECTOR24, DOMAIN, ICON_CONVECTOR
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
    HVAC_MODE_AUTO,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
    PRESET_COMFORT,
    PRESET_ECO
)

from homeassistant.const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    TEMP_CELSIUS
)

_LOGGER = logging.getLogger(__name__)

DELTA_ECO_DEFAULT = 4

TEMP_MIN = 10
TEMP_MAX = 35

TEMP_ANTIFROST_MIN = 3
TEMP_ANTIFROST_MAX = 7

DEFAULT_NAME = "Convector"


class BrightnessMode(IntEnum):
    HALF = 0
    FULL = 1


BRIGHTNESS = {
    BrightnessMode.HALF: "50%",
    BrightnessMode.FULL: "100%",
}

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
SUPPORT_MODES = [HVAC_MODE_HEAT, HVAC_MODE_AUTO, HVAC_MODE_OFF]


class WorkMode(IntEnum):
    COMFORT = 0
    ECO = 1
    NO_FROST = 2
    OFF = 3


HA_PRESET_TO_DEVICE = {
    PRESET_COMFORT: WorkMode.COMFORT.value,
    PRESET_ECO: WorkMode.ECO.value,
    PRESET_NO_FROST: WorkMode.NO_FROST.value
}
DEVICE_PRESET_TO_HA = {v: k for k, v in HA_PRESET_TO_DEVICE.items()}


class Preset(IntEnum):
    PRESET_0 = 0
    PRESET_1 = 1
    PRESET_2 = 2
    PRESET_3 = 3
    PRESET_4 = 4
    PRESET_5 = 5
    PRESET_6 = 6
    PRESET_7 = 7


class LedMode(IntEnum):
    PERMANENT = 0
    AUTO = 1


class HeatMode(IntEnum):
    AUTO = 0
    MANUAL = 1


class PowerMode(IntEnum):
    POWER_0 = 0
    POWER_1 = 1
    POWER_2 = 2
    POWER_3 = 3
    POWER_4 = 4
    POWER_5 = 5


class Convector2:
    def __init__(self):
        self._state = State.OFF.value
        self._online = State.OFF.value
        self._child_lock = State.OFF.value
        self._sensor_fault = State.OFF.value
        self._window_open = State.OFF.value
        self._mute = State.OFF.value
        self._window_opened = State.OFF.value
        self._calendar_on = State.OFF.value
        self._brightness = BrightnessMode.FULL.value    # яркость дисплея
        self._led_off_auto = LedMode.PERMANENT.value    # автоотключение дисплея
        self._temp_comfort = TEMP_MIN                   # температура для режима комфорт
        self._delta_eco = DELTA_ECO_DEFAULT             # дельта для ночной температуры
        self._temp_antifrost = TEMP_ANTIFROST_MIN       # температура для анти-фрост
        self._mode = WorkMode.COMFORT.value             # режим работы
        # таймер
        self._hours = 0
        self._minutes = 0
        self._timer = State.OFF.value

        self._current_temp = 0
        self._heat_mode = HeatMode.AUTO.value   # режим обогрева: авто или ручной
        self._power = PowerMode.POWER_0.value   # можность обогрева
        self._lcd_on = State.ON.value
        # текущие дата и время
        self._time_seconds = 0
        self._time_minutes = 0
        self._time_hour = 0
        self._time_day = 0
        self._time_month = 0
        self._time_year = 0
        self._time_weekday = 0
        # пресеты
        self._preset_monday = Preset.PRESET_0.value
        self._preset_tuesday = Preset.PRESET_0.value
        self._preset_wednesday = Preset.PRESET_0.value
        self._preset_thursday = Preset.PRESET_0.value
        self._preset_friday = Preset.PRESET_0.value
        self._preset_saturday = Preset.PRESET_0.value
        self._preset_sunday = Preset.PRESET_0.value
        self._preset_day_1 = WorkMode.OFF.value
        self._preset_day_2 = WorkMode.OFF.value
        self._preset_day_3 = WorkMode.OFF.value
        self._preset_day_4 = WorkMode.OFF.value
        self._preset_day_5 = WorkMode.OFF.value
        self._preset_day_6 = WorkMode.OFF.value
        self._preset_day_7 = WorkMode.OFF.value
        self._preset_day_8 = WorkMode.OFF.value
        self._preset_day_9 = WorkMode.OFF.value
        self._preset_day_10 = WorkMode.OFF.value
        self._preset_day_11 = WorkMode.OFF.value
        self._preset_day_12 = WorkMode.OFF.value
        self._preset_day_13 = WorkMode.OFF.value
        self._preset_day_14 = WorkMode.OFF.value
        self._preset_day_15 = WorkMode.OFF.value
        self._preset_day_16 = WorkMode.OFF.value
        self._preset_day_17 = WorkMode.OFF.value
        self._preset_day_18 = WorkMode.OFF.value
        self._preset_day_19 = WorkMode.OFF.value
        self._preset_day_20 = WorkMode.OFF.value
        self._preset_day_21 = WorkMode.OFF.value
        self._preset_day_22 = WorkMode.OFF.value
        self._preset_day_23 = WorkMode.OFF.value
        self._preset_day_24 = WorkMode.OFF.value

        self._room = None   # название помещения
        self._lock = State.OFF.value    # режим блокировки

    def from_json(self, data: dict):
        """Fill self from json data"""
        for key in data:
            setattr(self, f"_{key}", data[key])

    @property
    def child_lock(self) -> bool:
        return int(self._child_lock) == State.ON.value

    @property
    def sensor_fault(self) -> bool:
        return int(self._sensor_fault) == State.ON.value

    @property
    def lcd_on(self) -> bool:
        return int(self._lcd_on) == State.ON.value

    @property
    def window_open(self) -> bool:
        return int(self._window_open) == State.ON.value

    @property
    def window_opened(self) -> bool:
        return int(self._window_opened) == State.ON.value

    @property
    def mute(self) -> bool:
        return int(self._mute) == State.ON.value

    @property
    def calendar_on(self) -> bool:
        return int(self._calendar_on) == State.ON.value

    @property
    def brightness(self) -> int:
        return int(self._brightness)
    @property
    def brightness_title(self) -> str:
        return BRIGHTNESS[BrightnessMode(int(self._brightness))]

    @property
    def brightness_half(self) -> bool:
        return int(self._brightness) == BrightnessMode.HALF.value

    @property
    def brightness_full(self) -> bool:
        return int(self._brightness) == BrightnessMode.FULL.value

    @property
    def led_off_auto(self) -> bool:
        return int(self._led_off_auto) == LedMode.AUTO.value

    @property
    def current_temp(self) -> float:
        return float(self._current_temp)

    @property
    def mode(self) -> WorkMode:
        return WorkMode(int(self._mode))

    @property
    def temp_comfort(self) -> float:
        return float(self._temp_comfort)

    @property
    def delta_eco(self) -> int:
        return int(self._delta_eco)

    @property
    def temp_antifrost(self) -> int:
        return int(self._temp_antifrost)

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
    def heat_mode(self) -> int:
        return int(self._heat_mode)

    @property
    def heat_mode_name(self) -> str:
        return HeatMode(int(self._heat_mode)).name.lower()

    @property
    def heat_mode_manual(self) -> bool:
        return int(self._heat_mode) == HeatMode.MANUAL.value

    @property
    def heat_mode_auto(self) -> bool:
        return int(self._heat_mode) == HeatMode.AUTO.value

    @property
    def power(self) -> int:
        return int(self._power)

    @property
    def time_seconds(self) -> int:
        return int(self._time_seconds)

    @property
    def time_minutes(self) -> int:
        return int(self._time_minutes)

    @property
    def time_hour(self) -> int:
        return int(self._time_hour)

    @property
    def time_day(self) -> int:
        return int(self._time_day)

    @property
    def time_month(self) -> int:
        return int(self._time_month)

    @property
    def time_year(self) -> int:
        return int(self._time_year)

    @property
    def time_weekday(self) -> int:
        return int(self._time_weekday)

    @property
    def preset_monday(self) -> int:
        return int(self._preset_monday)

    @property
    def preset_tuesday(self) -> int:
        return int(self._preset_tuesday)

    @property
    def preset_wednesday(self) -> int:
        return int(self._preset_wednesday)

    @property
    def preset_thursday(self) -> int:
        return int(self._preset_thursday)

    @property
    def preset_friday(self) -> int:
        return int(self._preset_friday)

    @property
    def preset_saturday(self) -> int:
        return int(self._preset_saturday)

    @property
    def preset_sunday(self) -> int:
        return int(self._preset_sunday)

    @property
    def preset_day_1(self) -> int:
        return int(self._preset_day_1)

    @property
    def preset_day_2(self) -> int:
        return int(self._preset_day_2)

    @property
    def preset_day_3(self) -> int:
        return int(self._preset_day_3)

    @property
    def preset_day_4(self) -> int:
        return int(self._preset_day_4)

    @property
    def preset_day_5(self) -> int:
        return int(self._preset_day_5)

    @property
    def preset_day_6(self) -> int:
        return int(self._preset_day_6)

    @property
    def preset_day_7(self) -> int:
        return int(self._preset_day_7)

    @property
    def preset_day_8(self) -> int:
        return int(self._preset_day_8)

    @property
    def preset_day_9(self) -> int:
        return int(self._preset_day_9)

    @property
    def preset_day_10(self) -> int:
        return int(self._preset_day_10)

    @property
    def preset_day_11(self) -> int:
        return int(self._preset_day_11)

    @property
    def preset_day_12(self) -> int:
        return int(self._preset_day_12)

    @property
    def preset_day_13(self) -> int:
        return int(self._preset_day_13)

    @property
    def preset_day_14(self) -> int:
        return int(self._preset_day_14)

    @property
    def preset_day_15(self) -> int:
        return int(self._preset_day_15)

    @property
    def preset_day_16(self) -> int:
        return int(self._preset_day_16)

    @property
    def preset_day_17(self) -> int:
        return int(self._preset_day_17)

    @property
    def preset_day_18(self) -> int:
        return int(self._preset_day_18)

    @property
    def preset_day_19(self) -> int:
        return int(self._preset_day_19)

    @property
    def preset_day_20(self) -> int:
        return int(self._preset_day_20)

    @property
    def preset_day_21(self) -> int:
        return int(self._preset_day_21)

    @property
    def preset_day_22(self) -> int:
        return int(self._preset_day_22)

    @property
    def preset_day_23(self) -> int:
        return int(self._preset_day_23)

    @property
    def preset_day_24(self) -> int:
        return int(self._preset_day_24)

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

    @staticmethod
    def device_type() -> str:
        return DEVICE_CONVECTOR24

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
                name=f"Led off auto",
                icon_on="mdi:brightness-auto",
                icon_off="mdi:brightness-auto",
                device=Convector2(),
                param_name="led_off_auto",
                property_name="led_off_auto",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Lcd",
                icon_on="mdi:led-on",
                icon_off="mdi:led-off",
                device=Convector2(),
                param_name="lcd_on",
                property_name="lcd_on",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Brightness",
                icon_on="mdi:brightness-5",
                icon_off="mdi:brightness-6",
                device=Convector2(),
                param_name="brightness",
                property_name="brightness",
                value_on=BrightnessMode.FULL.value,
                value_off=BrightnessMode.HALF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Window Open",
                icon_on="mdi:window-open",
                icon_off="mdi:window-closed",
                device=Convector2(),
                param_name="window_open",
                property_name="window_open",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Mute",
                icon_on="mdi:volume-off",
                icon_off="mdi:volume-high",
                device=Convector2(),
                param_name="mute",
                property_name="mute",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Lock",
                icon_on="mdi:lock",
                icon_off="mdi:lock-open",
                device=Convector2(),
                param_name="child_lock",
                property_name="child_lock",
                value_on=State.ON.value,
                value_off=State.OFF.value
            ),

            BaseSwitch(
                uid=data["uid"],
                coordinator=coordinator,
                name=f"Timer",
                icon_on="mdi:timer",
                icon_off="mdi:timer-off",
                device=Convector2(),
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
        self._device = Convector2()

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
        if self._device.state and self._device.heat_mode_auto:
            return HVAC_MODE_AUTO

        if self._device.state:
            return HVAC_MODE_HEAT

        return HVAC_MODE_OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        _LOGGER.debug(f"{hvac_mode}, {self._device.heat_mode_auto}")
        if hvac_mode == HVAC_MODE_AUTO and not self._device.state:
            params = {"state": State.ON.value, "heat_mode": HeatMode.AUTO.value}
        elif hvac_mode == HVAC_MODE_AUTO and self._device.state:
            params = {"heat_mode": 1 - self._device.heat_mode}
        elif hvac_mode == HVAC_MODE_HEAT and self._device.heat_mode_auto:
            params = {"state": State.ON.value, "heat_mode": HeatMode.MANUAL.value}
        elif hvac_mode == HVAC_MODE_HEAT:
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
        return PRECISION_TENTHS

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

