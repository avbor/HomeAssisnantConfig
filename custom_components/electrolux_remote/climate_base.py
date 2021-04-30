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
            support_flags: int,
            support_modes: List[str],
            support_presets: List[str],
            device
    ):
        """
        Initialize the climate device
        """
        super().__init__(coordinator)

        self._icon = "mdi:radiator"
        self._uid = uid
        self._name = name
        self._support_flags = support_flags
        self._support_modes = support_modes
        self._support_presets = support_presets
        self._device = device

        coordinator.async_add_listener(self._update)
        self._update()

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

    def _update(self) -> None:
        """
        Update local data
        """
        for data in self.coordinator.data:
            if data["uid"] == self._uid:
                self._device.from_json(data)

    def _update_coordinator_data(self, params: dict) -> None:
        """Update data in coordinator"""
        devices = self.coordinator.data

        for index, device in enumerate(devices):
            if device["uid"] == self._uid:
                for param in params:
                    devices[index][param] = params[param]

        self.coordinator.async_set_updated_data(devices)
        self._update()
