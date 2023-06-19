"""Sensor platform for proconip."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensor_entities = [
        ProconipRedoxSensor(coordinator),
        ProconipPhSensor(coordinator),
    ]
    for i in range(8):
        sensor_entities.append(
            ProconipTemperatureSensor(coordinator=coordinator, sensor_no=i + 1)
        )
    async_add_devices(sensor_entities)


class ProconipRedoxSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Redox Sensor class."""

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
    """ProCon.IP pH Sensor class."""

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


class ProconipTemperatureSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Temperature Sensor class."""

    _attr_icon = "mdi:thermometer"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
    ) -> None:
        super().__init__(coordinator)
        self._sensor_no = sensor_no
        self._sensor = self.coordinator.data.temperature_objects[self._sensor_no - 1]
        self._attr_name = f"Temperature No. {sensor_no}: {self._sensor.name}"
        self._attr_unique_id = f"temperature_{sensor_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._sensor.value
