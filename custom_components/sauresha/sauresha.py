import datetime
import logging
import functools
import sys
import time
from logging import Logger

import requests

_LOGGER: Logger = logging.getLogger(__name__)


class SauresHA:
    _sid: str
    _debug: bool
    _last_login_time: time
    _last_getMeters_time: time
    _sensors: list

    def __init__(self, email, password, is_debug):
        self.__session = requests.Session()
        self._email = email
        self._password = password
        self._debug = is_debug
        self._last_login_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._last_getMeters_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._last_getControllers_time = datetime.datetime(2000, 1, 1, 1, 1, 1)
        self._sensors = list()

    @property
    def sid(self):
        return self._sid

    @property
    def re_auth(self):
        bln_return = False
        try:
            now = datetime.datetime.now()
            period = now - self._last_login_time
            if (period.total_seconds() / 60) > 5:
                self._last_login_time = datetime.datetime.now()
                auth_data = self.__session.post('https://api.saures.ru/login', data={
                    'email': self._email,
                    'password': self._password
                }).json()
                if not auth_data:
                    raise Exception('Invalid credentials')
                self._sid = auth_data['data']['sid']
                bln_return = auth_data['status'] != 'bad'

            else:
                if self._sid == "":
                    bln_return = False
                else:
                    bln_return = True

        except Exception as e:  # catch *all* exceptions
            if self._debug:
                _LOGGER.warning(str(e))

        return bln_return

    def get_flats(self):
        flats = ""
        if self.re_auth:
            flats = self.__session.get(f'https://api.saures.ru/1.0/user/objects', params={
                'sid': self._sid
            }).json()['data']['objects']

        return flats

    def get_meters(self, flat_id):
        now = datetime.datetime.now()
        period = now - self._last_getMeters_time
        date_time = now.strftime("%Y-%m-%dT%H:%M:%S")
        if (period.total_seconds() / 60) > 5:
            self._last_getMeters_time = datetime.datetime.now()
            try:
                sensors = self.__session.get(f'https://api.saures.ru/1.0/object/meters', params={
                    'id': flat_id,
                    'sid': self._sid,
                    'date': date_time
                }).json()['data']['sensors']
                self._sensors = sensors
            except Exception as e:  # catch *all* exceptions
                if self._debug:
                    _LOGGER.warning(str(e))

        return functools.reduce(list.__add__, map(lambda sensor: sensor['meters'], self._sensors))

    def get_controllers(self, flat_id):
        now = datetime.datetime.now()
        period = now - self._last_getControllers_time
        if (period.total_seconds() / 60) > 5:
            self._last_getControllers_time = datetime.datetime.now()
            try:
                controllers = self.__session.get(f'https://api.saures.ru/1.0/object/meters', params={
                    'id': flat_id,
                    'sid': self._sid
                }).json()['data']['sensors']
            except Exception as e:
                if self._debug:
                    _LOGGER.warning(str(e))

            self._sensors = controllers
        return functools.reduce(list.__add__, map(lambda sensor: self._sensors, self._sensors))

    def get_meter(self, flat_id, serial_number):
        meters = self.get_meters(flat_id)
        return next((Meter(METER) for METER in meters if METER['sn'] == serial_number), Meter(dict()))

    def get_controller(self, flat_id, sn):
        controllers = self.get_controllers(flat_id)
        return next((Controller(controller) for controller in controllers if controller['sn'] == sn),
                    Controller(dict()))


class Meter:
    def __init__(self, data):
        self.data = data
        self.name = data.get('meter_name')
        self.type_number = data.get('type', {}).get('number')
        self.type = data.get('type', {}).get('name')
        self.state = data.get('state', {}).get('name')
        self.sn = data.get('sn')
        self.value = data.get('value')
        self.id = data.get('meter_id')
        self.input = data.get('input')
        self.approve_dt = data.get('approve_dt')

        self.values = data.get('vals', [])

        if len(self.values) == 2:
            self.value = '{0}/{1}'.format(self.values[0], self.values[1])
            self.t1 = self.values[0]
            self.t2 = self.values[1]
            self.t3 = '-'
            self.t4 = '-'
        elif len(self.values) == 3:
            self.value = '{0}/{1}/{2}'.format(self.values[0], self.values[1], self.values[2])
            self.t1 = self.values[0]
            self.t2 = self.values[1]
            self.t3 = self.values[2]
            self.t4 = '-'
        elif len(self.values) == 4:
            self.value = '{0}/{1}/{2}/{3}'.format(self.values[0], self.values[1], self.values[2], self.values[3])
            self.t1 = self.values[0]
            self.t2 = self.values[1]
            self.t3 = self.values[2]
            self.t4 = self.values[3]
        elif len(self.values) == 1:
            self.value = self.values[0]
            self.t1 = self.values[0]
            self.t2 = '-'
            self.t3 = '-'
            self.t4 = '-'


class Controller:
    def __init__(self, data):
        self.data = data
        self.name = data.get('sn')
        self.sn = data.get('sn')
        self.battery = data.get('bat')
        self.ssid = data.get('ssid')
        self.local_ip = data.get('local_ip')
        self.firmware = data.get('firmware')
        self.readout_dt = data.get('readout_dt')
        self.request_dt = data.get('request_dt')
        self.last_connection = data.get('last_connection')
        self.state = "OK"
        self.rssi = data.get('rssi')
        self.hardware = data.get('hardware')
        self.new_firmware = data.get('new_firmware')
        self.last_connection = data.get('last_connection')
        self.last_connection_warning = data.get('last_connection_warning')
        self.check_hours = data.get('check_hours')
        self.check_period_display = data.get('check_period_display')
        self.requests = data.get('requests')
        self.log = data.get('log')
        self.cap_state = bool(data.get('cap_state'))
        self.power_supply = bool(data.get('power_supply'))

# if __name__ == "__main__":
# s = SauresHA('demo@saures.ru', 'demo')
# meter = s.get_flats()
# meter = s.get_meter(358, '136661693')
# print(meter.data)
# controller = s.get_controller(4731, '155100360017')
# print(controller.data)
