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
    for i in range(5):
        sensor_entities.append(
            ProconipAnalogSensor(coordinator=coordinator, sensor_no=i + 1)
        )
    for i in range(4):
        sensor_entities.append(
            ProconipDigitalInputSensor(coordinator=coordinator, sensor_no=i + 1)
        )
    for i in range(8):
        sensor_entities.append(
            ProconipTemperatureSensor(coordinator=coordinator, sensor_no=i + 1)
        )
    for i in range(3):
        sensor_entities.append(
            ProconipCanisterSensor(coordinator=coordinator, canister_no=i + 1)
        )
        sensor_entities.append(
            ProconipCanisterConsumptionSensor(
                coordinator=coordinator, canister_no=i + 1
            )
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
        """Initialize new temperature sensor."""
        super().__init__(coordinator)
        self._sensor_no = sensor_no
        self._sensor = self.coordinator.data.temperature_objects[self._sensor_no - 1]
        self._attr_name = f"Temperature No. {sensor_no}: {self._sensor.name}"
        self._attr_unique_id = f"temperature_{sensor_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._sensor.value


class ProconipAnalogSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Analog Sensor class."""

    _attr_icon = "mdi:sine-wave"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator)
        self._adc_no = sensor_no
        self._adc = self.coordinator.data.analog_objects[self._adc_no - 1]
        self._attr_name = f"Analog No. {sensor_no}: {self._adc.name}"
        self._attr_unique_id = f"analog_{sensor_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._adc.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._adc.unit


class ProconipDigitalInputSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Digital Input Sensor class."""

    _attr_icon = "mdi:import"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 0

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator)
        self._digital_input_no = sensor_no
        self._digital_input = self.coordinator.data.digital_input_objects[
            self._digital_input_no - 1
        ]
        self._attr_name = f"Digital Input No. {sensor_no}: {self._digital_input.name}"
        self._attr_unique_id = f"digital_input_{sensor_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._digital_input.value


class ProconipCanisterSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Canister Sensor class."""

    _attr_icon = "mdi:bottle-tonic-outline"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        canister_no: int,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator)
        self._canister_no = canister_no
        self._canister = self.coordinator.data.canister_objects[self._canister_no - 1]
        self._attr_name = f"Canister {self._canister.name}"
        self._attr_unique_id = f"canister_{canister_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._canister.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._canister.unit


class ProconipCanisterConsumptionSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Canister Consumption Sensor class."""

    _attr_icon = "mdi:bottle-tonic-plus-outline"
    _attr_state_class = "measurement"
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        canister_no: int,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator)
        self._canister_no = canister_no
        self._canister = self.coordinator.data.consumption_objects[
            self._canister_no - 1
        ]
        self._attr_name = f"Canister consumption {self._canister.name}"
        self._attr_unique_id = f"canister_consumption_{canister_no}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self._canister.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._canister.unit
