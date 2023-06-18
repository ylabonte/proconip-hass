"""Sensor platform for proconip."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity

from .const import DOMAIN
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            ProconipRedoxSensor(coordinator),
            ProconipPhSensor(coordinator),
        ]
    )


class ProconipRedoxSensor(ProconipPoolControllerEntity, SensorEntity):
    """Proconip Redox Sensor class."""

    _attr_icon = "mdi:gauge"
    _attr_name = "Redox sensor"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 1
    _attr_unique_id = "redox_electrode"
    suggested_display_precision = 1

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.redox_electrode.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self.coordinator.data.redox_electrode.unit


class ProconipPhSensor(ProconipPoolControllerEntity, SensorEntity):
    """Proconip pH Sensor class."""

    _attr_icon = "mdi:gauge"
    _attr_name = "pH sensor"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 2
    _attr_unique_id = "ph_electrode"
    suggested_display_precision = 2

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.ph_electrode.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self.coordinator.data.ph_electrode.unit
