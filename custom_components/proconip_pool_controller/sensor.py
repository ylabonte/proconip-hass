"""Sensor platform for proconip."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NTP_FAULT_BIT, PROBLEM_SEVERITY_BITS
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensor_entities = [
        ProconipRedoxSensor(coordinator=coordinator, instance_id=entry.entry_id),
        ProconipPhSensor(coordinator=coordinator, instance_id=entry.entry_id),
        ProconipFaultStateSensor(coordinator=coordinator, instance_id=entry.entry_id),
    ]
    for i in range(5):
        sensor_entities.append(
            ProconipAnalogSensor(
                coordinator=coordinator, sensor_no=i + 1, instance_id=entry.entry_id
            )
        )
    for i in range(4):
        sensor_entities.append(
            ProconipDigitalInputSensor(
                coordinator=coordinator, sensor_no=i + 1, instance_id=entry.entry_id
            )
        )
    for i in range(8):
        sensor_entities.append(
            ProconipTemperatureSensor(
                coordinator=coordinator, sensor_no=i + 1, instance_id=entry.entry_id
            )
        )
    for i in range(3):
        sensor_entities.append(
            ProconipCanisterSensor(
                coordinator=coordinator, canister_no=i + 1, instance_id=entry.entry_id
            )
        )
        sensor_entities.append(
            ProconipCanisterConsumptionSensor(
                coordinator=coordinator, canister_no=i + 1, instance_id=entry.entry_id
            )
        )
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    for i in range(number_of_relays):
        sensor_entities.append(
            ProconipRelayStateSensor(
                coordinator=coordinator, relay_no=i + 1, instance_id=entry.entry_id
            )
        )
    async_add_devices(sensor_entities)


class ProconipRedoxSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Redox Sensor class."""

    _attr_icon = "mdi:gauge"
    _attr_translation_key = "redox"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        instance_id: str,
    ) -> None:
        """Initialize new redox sensor."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"redox_electrode_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.redox_electrode.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self.coordinator.data.redox_electrode.unit


class ProconipPhSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP pH Sensor class."""

    _attr_icon = "mdi:gauge"
    _attr_translation_key = "ph"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        instance_id: str,
    ) -> None:
        """Initialize new pH sensor."""
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"ph_electrode_{instance_id}"

    @property
    def native_value(self) -> float:
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
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "temperature"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator=coordinator)
        self._sensor_no = sensor_no
        self._sensor = self.coordinator.data.temperature_objects[self._sensor_no - 1]
        self._attr_entity_registry_visible_default = self._sensor.name != "n.a."
        self._attr_translation_placeholders = {
            "sensor_no": str(sensor_no),
            "device_name": self._sensor.name,
        }
        self._attr_unique_id = f"temperature_{sensor_no}_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.temperature_objects[self._sensor_no - 1].value


class ProconipAnalogSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Analog Sensor class."""

    _attr_icon = "mdi:sine-wave"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "analog"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator=coordinator)
        self._adc_no = sensor_no
        self._adc = self.coordinator.data.analog_objects[self._adc_no - 1]
        self._attr_entity_registry_visible_default = self._adc.name != "n.a."
        self._attr_translation_placeholders = {
            "sensor_no": str(sensor_no),
            "device_name": self._adc.name,
        }
        self._attr_unique_id = f"analog_{sensor_no}_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.analog_objects[self._adc_no - 1].value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._adc.unit


class ProconipDigitalInputSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Digital Input Sensor class."""

    _attr_icon = "mdi:import"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "digital_input"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        sensor_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator=coordinator)
        self._digital_input_no = sensor_no
        self._digital_input = self.coordinator.data.digital_input_objects[
            self._digital_input_no - 1
        ]
        self._attr_entity_registry_visible_default = self._digital_input.name != "n.a."
        self._attr_translation_placeholders = {
            "sensor_no": str(sensor_no),
            "device_name": self._digital_input.name,
        }
        self._attr_unique_id = f"digital_input_{sensor_no}_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.digital_input_objects[self._digital_input_no - 1].value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._digital_input.unit


class ProconipCanisterSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Canister Sensor class."""

    _attr_icon = "mdi:bottle-tonic-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "canister"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        canister_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator=coordinator)
        self._canister_no = canister_no
        self._canister = self.coordinator.data.canister_objects[self._canister_no - 1]
        match canister_no:
            case 1:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_chlorine_dosage_enabled()
                )
            case 2:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_ph_minus_dosage_enabled()
                )
            case 3:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_ph_plus_dosage_enabled()
                )
        self._attr_translation_placeholders = {"device_name": self._canister.name}
        self._attr_unique_id = f"canister_{canister_no}_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.canister_objects[self._canister_no - 1].value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._canister.unit


class ProconipCanisterConsumptionSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Canister Consumption Sensor class."""

    _attr_icon = "mdi:bottle-tonic-plus-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "canister_consumption"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        canister_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new temperature sensor."""
        super().__init__(coordinator=coordinator)
        self._canister_no = canister_no
        self._canister = self.coordinator.data.consumption_objects[self._canister_no - 1]
        match canister_no:
            case 1:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_chlorine_dosage_enabled()
                )
            case 2:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_ph_minus_dosage_enabled()
                )
            case 3:
                self._attr_entity_registry_visible_default = (
                    self.coordinator.data.is_ph_plus_dosage_enabled()
                )
        self._attr_translation_placeholders = {"device_name": self._canister.name}
        self._attr_unique_id = f"canister_consumption_{canister_no}_{instance_id}"

    @property
    def native_value(self) -> float:
        """Return the native value of the sensor."""
        return self.coordinator.data.consumption_objects[self._canister_no - 1].value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the suggested unit of measurement."""
        return self._canister.unit


class ProconipRelayStateSensor(ProconipPoolControllerEntity, SensorEntity):
    """ProCon.IP Relay State Sensor class."""

    _attr_icon = "mdi:light-switch"
    _attr_translation_key = "relay_state"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new relay state sensor."""
        super().__init__(coordinator=coordinator)
        self._relay_id = relay_no - 1
        self._relay = self.coordinator.data.get_relay(relay_id=self._relay_id)
        self._attr_entity_registry_visible_default = not self.coordinator.data.is_dosage_relay(
            relay_id=self._relay_id
        )
        self._attr_translation_placeholders = {
            "relay_no": str(relay_no),
            "device_name": self._relay.name,
        }
        self._attr_unique_id = f"relay_state_{relay_no}_{instance_id}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.get_relay(relay_id=self._relay_id).display_value


class ProconipFaultStateSensor(ProconipPoolControllerEntity, SensorEntity):
    """Diagnostic sensor for the controller's fault state (SYSINFO[4]).

    Surfaces the proconip library's decoded label for the green/yellow/red GUI
    warning lamps (and the NTP fault bit), with the raw value and the
    individual decoded bits exposed as attributes for templates/automations.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "fault_state"
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"fault_state_{instance_id}"

    @property
    def native_value(self) -> str:
        """Return the decoded fault-state label."""
        return self.coordinator.data.get_ntp_fault_state_as_str()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw value and the individual decoded bits."""
        raw = self.coordinator.data.ntp_fault_state
        return {
            "raw": raw,
            "green": bool(raw & PROBLEM_SEVERITY_BITS["green"]),
            "yellow": bool(raw & PROBLEM_SEVERITY_BITS["yellow"]),
            "red": bool(raw & PROBLEM_SEVERITY_BITS["red"]),
            "ntp_synced": not (raw & NTP_FAULT_BIT),
        }
