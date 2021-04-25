"""Adds Support for Rusclimat"""

import logging
import abc
import async_timeout

from aiohttp import ClientSession, ClientError
from asyncio import TimeoutError, get_event_loop
from socket import gaierror

from .const import LANG
from .exception import InvalidAuth, InvalidResponse, UserNotFound, DeviceUnavailable, EnexpectedError

_LOGGER = logging.getLogger(__name__)

# request uri
API_LOGIN = "api/userAuth"
API_CHANGE_PASSWORD = "api/userChangePassword"
API_CREATE_CALENDAR = "api/setTimeSlot"
API_DELETE_DEVICE = "api/deleteDevice"
API_DELETE_DEVICE_BY_TEMP_ID = "api/deleteDeviceByTempID"
API_PUT_DEVICE = "api/putDevice"
API_GET_DEVICE_PARAMS = "api/getDeviceParams"
API_SET_DEVICE_PARAMS = "api/setDeviceParams"
API_REGISTRATION = "api/userRegister"
API_REMIND_PASSWORD = "api/userRemindPassword"
API_SEND_CODE = "api/userRegister"
API_UPDATE_CALENDAR_SLOTS = "api/setTimeSlot"

# response code
ERROR_INCORRECT_LOGIN_OR_PASSWORD = "106"
ERROR_INCORRECT_PHONE = "112"  # Слишком короткий номер телефона
ERROR_TOKEN_NOT_FOUND = "121"  # Токен не найден
ERROR_USER_NOT_FOUND = "136"  # Пользователь не найден
ERROR_DEVICE_UNAVAILABLE = "153"  # Ошибка - устройство не в сети или неизвестный тип

HEADERS = {
    "lang": LANG,
    "Content-Type": "application/json; charset=UTF-8",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "User-Agent": "okhttp/4.3.1",
}

TIMEOUT = 10


class ApiInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def login(self) -> []:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_data(self) -> []:
        raise NotImplementedError

    @abc.abstractmethod
    async def set_device_params(self, uid: str, params: dict) -> bool:
        raise NotImplementedError


class RusclimatApi(ApiInterface):
    """ Wrapper class to the Rusclimat API """

    def __init__(self, host: str, username: str, password: str, appcode: str, session: ClientSession):
        self._host = host
        self._username = username
        self._password = password
        self._appcode = appcode
        self._token = None
        self._session = session

    async def login(self) -> []:
        """Auth on server"""

        payload = {
            "login": self._username,
            "password": self._password,
            "appcode": self._appcode
        }

        json = await self._request(API_LOGIN, payload)

        if json["error_code"] == ERROR_USER_NOT_FOUND:
            raise UserNotFound(json["error_message"])
        elif json["error_code"] == ERROR_INCORRECT_LOGIN_OR_PASSWORD:
            raise InvalidAuth(json["error_message"])
        elif json["error_code"] != "0":
            _LOGGER.exception(f"message: '{json['error_message']}'; code: {json['error_code']}")
            raise InvalidAuth(json["error_message"])

        self._token = json["result"]["token"]

        return json

    async def get_data(self) -> []:
        if self._token is None:
            await self.login()

        payload = {
            "token": self._token,
            "uid": []
        }

        json = await self._request(API_GET_DEVICE_PARAMS, payload)

        if json["error_code"] == ERROR_DEVICE_UNAVAILABLE:
            raise DeviceUnavailable(json["error_message"])

        self._check_response_code(json)

        return json["result"]["device"]

    async def set_device_params(self, uid: str, params: dict) -> bool:
        """Update params"""
        _LOGGER.debug(f"Update params: {params}")

        if not params:
            return False

        payload = {
            "uid": uid,
            "params": params
        }

        json = await self._update_device_params(payload)

        return self._check_result(json)

    async def _request(self, url: str, payload: dict) -> dict:
        _LOGGER.debug(f"request: {url}")
        _LOGGER.debug(f"payload: {payload}")

        try:
            async with async_timeout.timeout(TIMEOUT, loop=get_event_loop()):
                response = await self._session.post(f"{self._host}/{url}", json=payload, headers=HEADERS)
                json = await response.json()

                _LOGGER.debug(f"response: {json}")

                if json is None:
                    raise InvalidResponse(f"Response error: json is None")

                return json
        except TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )

        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s - %s",
                url,
                exception,
            )
        except (ClientError, gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happened! - %s", exception)

    async def _update_device_params(self, params: dict) -> dict:
        if self._token is None:
            await self.login()

        payload = {
            "token": self._token,
            "device": [params]
        }

        json = await self._request(API_SET_DEVICE_PARAMS, payload)

        if json["error_code"] == ERROR_DEVICE_UNAVAILABLE:
            raise DeviceUnavailable(json["error_message"])

        self._check_response_code(json)

        return json

    @staticmethod
    def _check_response_code(json):
        if json["error_code"] != "0":
            _LOGGER.exception(f"message: '{json['error_message']}'; code: {json['error_code']}")
            raise EnexpectedError(json["error_message"])

    @staticmethod
    def _check_result(json) -> bool:
        return json["result"] == "1"


class TestApi(ApiInterface):
    """ Wrapper class to the Rusclimat API """

    def __init__(self, host: str, username: str, password: str, appcode: str, session: ClientSession):
        floor_1 = {
            "tempid": "181304",
            "state": "1",
            "error": "0",
            "set_temp": "240",
            "room_temp": "292",
            "set_room_temp": "38",
            "floor_temp": "304",
            "sensor_mode": "0",
            "sensor_type": "2",
            "floor_temp_limit": "450",
            "antifreeze_temp": "0",
            "led_light": "30",
            "heating_on": "0",
            "open_window": "1",
            "button_lock": "1",
            "pol_res_set": "1",
            "pol_type": "1",
            "mode": "1",
            "pol_matrix": {
                "1": {
                    "1": "240",
                    "2": "210",
                    "3": "210",
                    "4": "210",
                    "5": "210"
                },
                "2": {
                    "1": "270",
                    "2": "250",
                    "3": "250",
                    "4": "250",
                    "5": "250"
                },
                "3": {
                    "1": "320",
                    "2": "280",
                    "3": "270",
                    "4": "270",
                    "5": "280"
                },
                "4": {
                    "1": "50",
                    "2": "50",
                    "3": "50",
                    "4": "50",
                    "5": "50"
                },
                "5": {
                    "1": "50",
                    "2": "50",
                    "3": "50",
                    "4": "50",
                    "5": "50"
                }
            },
            "power_per_h": "0",
            "tariff_1": "0",
            "tariff_2": "0",
            "tariff_3": "0",
            "type": "floor",
            "timezone": "3",
            "hours": "22",
            "minutes": "59",
            "uid": "181304",
            "mac": "set",
            "room": "Ванная",
            "sort": "0",
            "curr_slot": "0",
            "active_slot": "0",
            "slop": "0",
            "curr_scene": "0",
            "curr_scene_id": "0",
            "wait_slot": "0",
            "curr_slot_dropped": "0",
            "curr_scene_dropped": "0",
            "online": "1",
            "set_temp_1": "0",
            "set_temp_0": "240",
            "room_temp_1": "1",
            "room_temp_0": "36",
            "set_room_temp_1": "0",
            "set_room_temp_0": "38",
            "floor_temp_1": "1",
            "floor_temp_0": "48",
            "floor_temp_limit_1": "1",
            "floor_temp_limit_0": "194",
            "antifreeze_temp_1": "0",
            "antifreeze_temp_0": "0"
        }
        floor_2 = {
            "tempid": "181305",
            "state": "0",
            "error": "0",
            "set_temp": "350",
            "room_temp": "258",
            "set_room_temp": "0",
            "floor_temp": "226",
            "sensor_mode": "0",
            "sensor_type": "2",
            "floor_temp_limit": "450",
            "antifreeze_temp": "0",
            "led_light": "30",
            "heating_on": "0",
            "open_window": "1",
            "button_lock": "1",
            "pol_res_set": "1",
            "pol_type": "1",
            "mode": "3",
            "pol_matrix": {
                "1": {
                    "1": "250",
                    "2": "210",
                    "3": "210",
                    "4": "210",
                    "5": "210"
                },
                "2": {
                    "1": "270",
                    "2": "250",
                    "3": "250",
                    "4": "250",
                    "5": "250"
                },
                "3": {
                    "1": "350",
                    "2": "280",
                    "3": "270",
                    "4": "270",
                    "5": "280"
                },
                "4": {
                    "1": "50",
                    "2": "50",
                    "3": "50",
                    "4": "50",
                    "5": "50"
                },
                "5": {
                    "1": "50",
                    "2": "50",
                    "3": "50",
                    "4": "50",
                    "5": "50"
                }
            },
            "power_per_h": "0",
            "tariff_1": "0",
            "tariff_2": "0",
            "tariff_3": "0",
            "type": "floor",
            "timezone": "3",
            "hours": "22",
            "minutes": "59",
            "uid": "181305",
            "mac": "set",
            "room": "Балкон",
            "sort": "0",
            "curr_slot": "0",
            "active_slot": "0",
            "slop": "0",
            "curr_scene": "0",
            "curr_scene_id": "0",
            "wait_slot": "0",
            "curr_slot_dropped": "0",
            "curr_scene_dropped": "0",
            "set_temp_1": "1",
            "set_temp_0": "94",
            "room_temp_1": "1",
            "room_temp_0": "2",
            "set_room_temp_1": "0",
            "set_room_temp_0": "0",
            "floor_temp_1": "0",
            "floor_temp_0": "226",
            "floor_temp_limit_1": "1",
            "floor_temp_limit_0": "194",
            "antifreeze_temp_1": "0",
            "antifreeze_temp_0": "0",
            "online": "1"
        }
        convector2 = {
            'state': '0',
            'child_lock': '0',
            'sensor_fault': '0',
            'window_open': '0',
            'mute': '0',
            'window_opened': '0',
            'calendar_on': '0',
            'brightness': '1',
            'led_off_auto': '0',
            'temp_comfort': '10',
            'delta_eco': '4',
            'temp_antifrost': '7',
            'mode': '1',
            'mode_temp_1': '0',
            'mode_temp_2': '0',
            'mode_temp_3': '0',
            'hours': '12',
            'minutes': '0',
            'timer': '0',
            'current_temp': '8',
            'heat_mode': '1',
            'power': '1',
            'code': '0',
            'lcd_on': '1',
            'time_seconds': '4',
            'time_minutes': '55',
            'time_hour': '0',
            'time_day': '1',
            'time_month': '4',
            'time_year': '21',
            'time_weekday': '4',
            'preset_monday': '0',
            'preset_tuesday': '0',
            'preset_wednesday': '0',
            'preset_thursday': '0',
            'preset_friday': '0',
            'preset_saturday': '0',
            'preset_sunday': '0',
            'preset_day_1': '0',
            'preset_day_2': '0',
            'preset_day_3': '0',
            'preset_day_4': '0',
            'preset_day_5': '0',
            'preset_day_6': '0',
            'preset_day_7': '0',
            'preset_day_8': '2',
            'preset_day_9': '2',
            'preset_day_10': '2',
            'preset_day_11': '2',
            'preset_day_12': '2',
            'preset_day_13': '2',
            'preset_day_14': '2',
            'preset_day_15': '2',
            'preset_day_16': '2',
            'preset_day_17': '2',
            'preset_day_18': '2',
            'preset_day_19': '2',
            'preset_day_20': '2',
            'preset_day_21': '2',
            'preset_day_22': '2',
            'preset_day_23': '2',
            'preset_day_24': '0',
            'tempid': '188577',
            'uid': '188577',
            'mac': 'set',
            'room': 'баня',
            'sort': '0',
            'type': 'convector24',
            'curr_slot': '0',
            'active_slot': '0',
            'slop': '0',
            'curr_scene': '0',
            'curr_scene_id': '0',
            'wait_slot': '0',
            'curr_slot_dropped': '0',
            'curr_scene_dropped': '0',
            'online': '1',
            'lock': '0'
        }
        centurio = {
            "tempid": "194341",
            "mode": "1",
            "current_temp": "54",
            "temp_goal": "55",
            "timer": "0",
            "timer_hours": "0",
            "timer_minutes": "0",
            "clock_hours": "7",
            "clock_minutes": "44",
            "self_clean": "0",
            "volume": "100",
            "error": "0",
            "type": "centurio",
            "code": "0",
            "self_clean_state": "disabled",
            "economy_morning": "0",
            "economy_evening": "0",
            "economy_pause": "0",
            "power_per_h_1": "1300",
            "power_per_h_2": "2000",
            "tariff_1": "0",
            "tariff_2": "0",
            "tariff_3": "0",
            "minutes_diff": "-2",
            "timezone": "0",
            "timer_hours_store": "0",
            "timer_minutes_store": "6",
            "seconds_diff": "46680",
            "uid": "194340",
            "mac": "set",
            "room": "Туалет",
            "sort": "0",
            "curr_slot": "0",
            "active_slot": "0",
            "slop": "0",
            "curr_scene": "0",
            "curr_scene_id": "0",
            "wait_slot": "0",
            "curr_slot_dropped": "0",
            "curr_scene_dropped": "0",
            "online": "1"
        }

        self.devices = [
            floor_1,
            floor_2,
            convector2,
            centurio
        ]

    async def login(self) -> []:
        json = {
            'result': {
                'token': '123456',
                'device': self.devices
            },
            'error_code': '0',
            'error_message': ''
        }

        return json["result"]["device"]

    async def get_data(self) -> []:
        return self.devices

    async def set_device_params(self, uid: str, params: dict) -> bool:
        for i, device in enumerate(self.devices):
            if device["uid"] == uid:
                for param in params:
                    self.devices[i][param] = params[param]

        return True
