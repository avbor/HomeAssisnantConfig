import logging
from typing import List, Any, Callable
import homeassistant.components.binary_sensor
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity import Entity
import voluptuous as vol
import datetime
import re
import time
from datetime import timedelta

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_EMAIL
)

from . import (
    CONF_FLAT_ID,
    CONF_COUNTERS_SN,
    CONF_DEBUG,
    CONF_SCAN_INTERVAL,
    CONF_NAME,
    CONF_COUNTERS,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=1)

PLATFORM_SCHEMA = homeassistant.components.binary_sensor.PLATFORM_SCHEMA.extend({
    vol.Required(CONF_EMAIL): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_FLAT_ID): cv.positive_int,
    vol.Optional(CONF_COUNTERS_SN): cv.ensure_list,
    vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL):
        vol.All(cv.time_period, cv.positive_timedelta),
    vol.Optional(CONF_DEBUG, default=False): cv.boolean,
    vol.Optional(CONF_COUNTERS): {
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
    _hass = hass
    _discovery_info = discovery_info
    scan_interval = config.get(CONF_SCAN_INTERVAL)
    is_debug = config.get(CONF_DEBUG)

    if is_debug:
        _LOGGER.warning("scan_interval=" + str(scan_interval))

    controller = SauresHA(
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
        sensors: List[SauresBinarySensor] = []
        for key, value in conf_counters.items():
            sensor = SauresBinarySensor(hass, controller, flat_id, key, value[CONF_NAME], is_debug, scan_interval)
            sensors.append(sensor)

        # create_sensor: Callable[[Any], SauresBinarySensor] = lambda serial_number: SauresBinarySensor(hass,
        #                                                                                               controller,
        #                                                                                               flat_id,
        #                                                                                               serial_number,
        #                                                                                               is_debug,
        #                                                                                               scan_interval)
        # sensors: List[SauresBinarySensor] = list(map(create_sensor, serial_numbers))

        if sensors:
            add_entities(sensors, True)


class SauresBinarySensor(Entity):
    """Representation of a BinarySensor."""

    def __init__(self, hass, controller, flat_id, sn, counter_name, is_debug, scan_interval):
        """Initialize the sensor."""

        self.controller = controller
        self.flat_id = flat_id
        self.serial_number = str(sn)
        self.counter_name = counter_name
        self._attributes = dict()
        self.isDebug = is_debug
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
        return f'binary_sensor.sauresha_{sn}'

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return bool(int(self._state))

    @property
    def state(self):
        """Return the state of the sensor."""
        return bool(int(self._state))

    @property
    def available(self):
        """Return true if the binary sensor is available."""
        return self._state is not None

    @property
    def icon(self):
        return 'mdi:alarm-check'

    @property
    def device_state_attributes(self):
        return self._attributes

    def fetch_state(self):
        """Retrieve latest state."""
        return_value = False
        if self.controller.re_auth:
            meter = self.current_meter
            return_value = meter.value
            self._attributes.update({
                'friendly_name': meter.name,
                'condition': meter.state,
                'sn': meter.sn,
                'type': meter.type,
                'meter_id': meter.id,
                'input': meter.input
            })
            if meter.state is not None:
                if meter.state.upper() == "ОБРЫВ":
                    return_value = True
        else:
            _LOGGER.error("API ERROR during Auth process")

        self._attributes.update({
            'last_update_time': datetime.datetime.now()})

        self._attributes.update({
            'next_update_time': datetime.datetime.now() + self.scan_interval})

        return return_value

    def update(self):
        self._state = self.fetch_state()

