"""Base to Climate class"""

import logging

from abc import abstractmethod
from typing import Any, Dict, List, Optional
from homeassistant.components.climate import ClimateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.const import (
    TEMP_CELSIUS,
)
from .update_coordinator import Coordinator

_LOGGER = logging.getLogger(__name__)


class ClimateBase(CoordinatorEntity, ClimateEntity):
    """
    Representation of a climate device
    """

    def __init__(
            self,
            coordinator: Coordinator,
            uid: str,
            name: str,
            temp_min: float,
            temp_max: float,
            support_flags: int,
            support_modes: List[str],
            support_presets: List[str],
    ):
        """
        Initialize the climate device
        """
        super().__init__(coordinator)

        self._icon = "mdi:radiator"
        self._uid = uid
        self._name = name
        self._min_temp = temp_min
        self._max_temp = temp_max
        self._support_flags = support_flags
        self._support_modes = support_modes
        self._support_presets = support_presets

        self._current_temp = None
        self._preset = None
        self._target_temperature = None
        self._available = False

    @staticmethod
    @abstractmethod
    def device_type() -> str:
        """
        Return device type
        """
        raise NotImplementedError()

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes. Need to be a subset of HVAC_MODES. """
        return self._support_modes

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the binary sensor."""
        return self._uid

    @property
    def current_temperature(self) -> Optional[float]:
        """Return the current temperature."""
        return self._current_temp

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        if self._min_temp:
            return self._min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        if self._max_temp:
            return self._max_temp

    @property
    def target_temperature(self) -> Optional[float]:
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return self._preset

    @property
    def name(self) -> str:
        """Return the name of the climate device."""
        return self._name

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return self._support_flags

    @property
    def preset_modes(self) -> List[str]:
        """Return a list of available preset modes."""
        return self._support_presets

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._available
