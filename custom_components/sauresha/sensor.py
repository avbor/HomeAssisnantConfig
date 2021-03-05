# Provides a sensor for Saures.
import datetime
import logging
import re
from datetime import timedelta
from typing import List, Any, Callable

import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_EMAIL,
    CONF_PASSWORD,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval

from . import (
    CONF_FLAT_ID,
    CONF_COUNTERS_SN,
    CONF_CONTROLLERS_SN,
    CONF_SCAN_INTERVAL,
    CONF_DEBUG,
    CONF_NAME,
    CONF_COUNTERS,
    CONF_CONTROLLERS,
)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_FLAT_ID): cv.positive_int,
    vol.Optional(CONF_COUNTERS_SN): cv.ensure_list,
    vol.Optional(CONF_CONTROLLERS_SN): cv.ensure_list,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DEBUG, default=False): cv.boolean,
    vol.Optional(CONF_COUNTERS): {
        cv.string: vol.Schema({
            vol.Optional(CONF_NAME, default=''): cv.string,
        }, extra=vol.ALLOW_EXTRA),
    },
    vol.Optional(CONF_CONTROLLERS): {
        cv.string: vol.Schema({
            vol.Optional(CONF_NAME, default=''): cv.string,
        }, extra=vol.ALLOW_EXTRA),
    },
})


def setup_platform(hass, config, add_entities, discovery_info=None, scan_interval=SCAN_INTERVAL):
    """Setup the sensor platform."""

    from .sauresha import SauresHA

    flat_id = config.get(CONF_FLAT_ID)
    serial_numbers = config.get(CONF_COUNTERS_SN, [])
    sns = config.get(CONF_CONTROLLERS_SN, [])
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    is_debug: bool = config.get(CONF_DEBUG)

    if is_debug:
        _LOGGER.warning("scan_interval=" + str(scan_interval))

    controller: SauresHA = SauresHA(
        config.get('email'),
        config.get('password'),
        is_debug
    )

    if int(flat_id) == 0:
        flats = controller.get_flats()
        if len(flats) == 1:
            flat_id = str(flats[0].get('id'))
            str_house = str(flats[0].get('house'))
            _LOGGER.warning("ID flat:" + str_house + " : " + flat_id)
        else:
            for val in flats:
                _LOGGER.warning("ID flat:" + str(val.get('house')) + " : " + str(val.get('id')))

    conf_counters = config.get(CONF_COUNTERS)
    if not conf_counters:
        conf_counters = serial_numbers

    if int(flat_id) > 0:
        sensors: List[SauresSensor] = []
        for key, value in conf_counters.items():
            sensor = SauresSensor(hass, controller, flat_id, key, value[CONF_NAME], is_debug, scan_interval)
            sensors.append(sensor)

    # create_sensor: Callable[[Any], SauresSensor] = lambda serial_number: SauresSensor(hass, controller,
    #                                                                                   flat_id,
    #                                                                                   serial_number,
    #                                                                                   is_debug,
    #                                                                                   scan_interval)
    # sensors: List[SauresSensor] = list(map(create_sensor, confcounters))

    if sensors:
        add_entities(sensors, True)

    conf_controllers = config.get(CONF_CONTROLLERS)
    if not conf_controllers:
        conf_controllers = sns

    my_controllers: List[SauresControllerSensor] = []
    for key, value in conf_controllers.items():
        my_controller = SauresControllerSensor(hass, controller, flat_id, key, value[CONF_NAME], is_debug, scan_interval)
        my_controllers.append(my_controller)

    # create_my_controller: Callable[[Any], SauresControllerSensor] = lambda sn: SauresControllerSensor(hass,
    #                                                                                                   controller,
    #                                                                                                   flat_id, sn,
    #                                                                                                   is_debug,
    #                                                                                                   scan_interval)
    #
    # my_controllers: List[SauresControllerSensor] = list(map(create_my_controller, sns))

    if my_controllers:
        add_entities(my_controllers, True)


class SauresSensor(Entity):
    """Representation of a Sensor."""
    _state: str

    def __init__(self, hass, controller, flat_id, sn, counter_name, is_debug, scan_interval):
        """Initialize the sensor."""

        self.controller = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = counter_name
        self.isStart = True
        self.isDebug = is_debug
        self._attributes = dict()
        self._state = ""
        self.scan_interval = scan_interval

        self.set_scan_interval(hass, scan_interval)

    def set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        def refresh(event_time):
            """Get the latest data from Transmission."""
            self.update()

        if self.isDebug:
            _LOGGER.warning("scan_interval=" + str(scan_interval))

        track_time_interval(
            hass, refresh, scan_interval
        )

    @property
    def current_meter(self):
        return self.controller.get_meter(self.flat_id, self.serial_number)

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        if len(self.counter_name) > 0:
            final_name = f'{self.counter_name}'
        else:
            final_name = f'{self.flat_id}_{self.serial_number}'
        sn = final_name.replace('-', '_')
        reg = re.compile('[^a-zA-Z0-9_]')
        sn = reg.sub('', sn).lower()
        return f'sensor.sauresha_{sn}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return 'mdi:counter'

    @property
    def device_state_attributes(self):
        return self._attributes

    def fetch_state(self):
        """Retrieve latest state."""
        str_return_value = "Unknown"

        if self.isDebug:
            _LOGGER.warning("Update Start")

        if self.controller.re_auth:
            meter = self.current_meter
            str_return_value = meter.value
            if meter.type_number == 8:
                self._attributes.update({
                    'friendly_name': meter.name,
                    'condition': meter.state,
                    'sn': meter.sn,
                    'type': meter.type,
                    'meter_id': meter.id,
                    'input': meter.input,
                    'approve_dt': meter.approve_dt,
                    't1': meter.t1,
                    't2': meter.t2,
                    't3': meter.t3,
                    't4': meter.t4
                })
            else:
                self._attributes.update({
                    'friendly_name': meter.name,
                    'condition': meter.state,
                    'sn': meter.sn,
                    'type': meter.type,
                    'meter_id': meter.id,
                    'input': meter.input,
                    'approve_dt': meter.approve_dt,
                })
            if self.isStart:
                if meter.type_number == 1 or meter.type_number == 2 or meter.type_number == 3:
                    self._attributes.update({
                        'unit_of_measurement': 'м³'})
                elif meter.type_number == 5:
                    self._attributes.update({
                        'unit_of_measurement': '°C'})
                elif meter.type_number == 8:
                    self._attributes.update({
                        'unit_of_measurement': 'кВт·ч'})

                self.isStart = False

        self._attributes.update({
            'last_update_time': datetime.datetime.now()})

        self._attributes.update({
            'next_update_time': datetime.datetime.now() + self.scan_interval})

        return str_return_value

    def update(self):
        self._state = self.fetch_state()


class SauresControllerSensor(Entity):
    """Representation of a Sensor."""
    _state: str

    def __init__(self, hass, controller, flat_id, sn, counter_name, is_debug, scan_interval=SCAN_INTERVAL):
        """Initialize the sensor."""
        self.controller = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = str(counter_name)
        self._state = ""
        self.isDebug = is_debug
        self._attributes = dict()
        self.scan_interval = scan_interval

        self.set_scan_interval(hass, scan_interval)

    @property
    def current_controller_info(self):
        return self.controller.get_controller(self.flat_id, self.serial_number)

    @property
    def entity_id(self):
        """Return the entity_id of the sensor."""
        if len(self.counter_name) > 0:
            final_name = f'{self.counter_name}'
        else:
            final_name = f'{self.serial_number}'
        sn = final_name.replace('-', '_')
        reg = re.compile('[^a-zA-Z0-9_]')
        sn = reg.sub('', sn).lower()
        return f'sensor.sauresha_contr_{sn}'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def icon(self):
        return 'mdi:xbox-controller-view'

    @property
    def device_state_attributes(self):
        return self._attributes

    def set_scan_interval(self, hass: object, scan_interval: timedelta):
        """Update scan interval."""

        def refresh(event_time):
            """Get the latest data from Transmission."""
            self.update()

        if self.isDebug:
            _LOGGER.warning("scan_interval=" + str(scan_interval))

        track_time_interval(
            hass, refresh, scan_interval
        )

    def fetch_state(self):
        """Retrieve latest state."""
        str_return_value = "Unknown"

        if self.controller.re_auth:
            my_controller = self.current_controller_info
            str_return_value = my_controller.state
            self._attributes.update({
                'battery_level': my_controller.battery,
                'condition': my_controller.state,
                'sn': my_controller.sn,
                'local_ip': my_controller.local_ip,
                'firmware': my_controller.firmware,
                'ssid': my_controller.ssid,
                'readout_dt': my_controller.readout_dt,
                'request_dt': my_controller.request_dt,
                'rssi': my_controller.rssi,
                'hardware': my_controller.hardware,
                'new_firmware': my_controller.new_firmware,
                'last_connection': my_controller.last_connection,
                'last_connection_warning': my_controller.last_connection_warning,
                'check_hours': my_controller.check_hours,
                'check_period_display': my_controller.check_period_display,
                'requests': my_controller.requests,
                'log': my_controller.log,
                'cap_state': my_controller.cap_state,
                'power_supply': my_controller.power_supply,
            })
        self._attributes.update({
            'last_update_time': datetime.datetime.now()})

        self._attributes.update({
            'next_update_time': datetime.datetime.now() + self.scan_interval})

        return str_return_value

    def update(self):
        self._state = self.fetch_state()
