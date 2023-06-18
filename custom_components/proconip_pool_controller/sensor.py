"""Sensor platform for proconip."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
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

    _attr_unique_id = "redox_sensor"
    _attr_name = "Redox sensor"
    _attr_icon = "mdi:gauge"
    _attr_suggested_display_precision = 1
    _attr_device_class = SensorDeviceClass.VOLTAGE

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
    ) -> None:
        """Initialize sensor class."""
        super().__init__(coordinator)
        self._attr_suggested_unit_of_measurement = coordinator.data.redox_electrode.unit

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.redox_electrode.value


class ProconipPhSensor(ProconipPoolControllerEntity, SensorEntity):
    """Proconip pH Sensor class."""

    _attr_unique_id = "ph_sensor"
    _attr_name = "pH sensor"
    _attr_icon = "mdi:gauge"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
    ) -> None:
        """Initialize sensor class."""
        super().__init__(coordinator)
        self._attr_suggested_unit_of_measurement = "pH"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.ph_electrode.value
