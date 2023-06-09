"""Binary sensor platform for ProCon.IP Pool Controller."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import DOMAIN
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        [
            ProconipChlorineDosageEnabledBinarySensor(coordinator),
            ProconipElectrolysisEnabledBinarySensor(coordinator),
            ProconipPhMinusDosageEnabledBinarySensor(coordinator),
            ProconipPhPlusDosageEnabledBinarySensor(coordinator),
            ProconipTcpIpBoostEnabledBinarySensor(coordinator),
            ProconipSdCardEnabledBinarySensor(coordinator),
            ProconipDmxEnabledBinarySensor(coordinator),
            ProconipAvatarEnabledBinarySensor(coordinator),
            ProconipRelayExtensionEnabledBinarySensor(coordinator),
            ProconipHighBusLoadEnabledBinarySensor(coordinator),
            ProconipFlowSensorEnabledBinarySensor(coordinator),
            ProconipRepeatedMailEnabledBinarySensor(coordinator),
            ProconipDmxExtensionEnabledBinarySensor(coordinator),
        ]
    )


class ProconipChlorineDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_chlorine_dosage_enabled()`."""

    _attr_name = "Chlorine Dosage enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_chlorine_dosage_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_chlorine_dosage_enabled()


class ProconipElectrolysisEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_electrolysis_enabled()`."""

    _attr_name = "Electrolysis enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_electrolysis_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_electrolysis_enabled()


class ProconipPhMinusDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_ph_minus_dosage_enabled()`."""

    _attr_name = "pH Minus Dosage enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_ph_minus_dosage_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_ph_minus_dosage_enabled()


class ProconipPhPlusDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_ph_plus_dosage_enabled()`."""

    _attr_name = "pH Plus Dosage enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_ph_plus_dosage_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_ph_plus_dosage_enabled()


class ProconipTcpIpBoostEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_tcpip_boost_enabled()`."""

    _attr_name = "TCP/IP Boost enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_tcpip_boost_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_tcpip_boost_enabled()


class ProconipSdCardEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_sd_card_enabled()`."""

    _attr_name = "SD Card enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_sd_card_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_sd_card_enabled()


class ProconipDmxEnabledBinarySensor(ProconipPoolControllerEntity, BinarySensorEntity):
    """ProCon.IP binary_sensor class for `GetStateData.is_dmx_enabled()`."""

    _attr_name = "DMX enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_dmx_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_dmx_enabled()


class ProconipAvatarEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_avatar_enabled()`."""

    _attr_name = "Avatar enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_avatar_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_avatar_enabled()


class ProconipRelayExtensionEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_relay_extension_enabled()`."""

    _attr_name = "Relay Extension enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_relay_extension_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_relay_extension_enabled()


class ProconipHighBusLoadEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_high_bus_load_enabled()`."""

    _attr_name = "High Bus Load enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_high_bus_load_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_high_bus_load_enabled()


class ProconipFlowSensorEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_flow_sensor_enabled()`."""

    _attr_name = "Flow Sensor enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_flow_sensor_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_flow_sensor_enabled()


class ProconipRepeatedMailEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_repeated_mails_enabled()`."""

    _attr_name = "Repeated Mails enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_repeated_mails_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_repeated_mails_enabled()


class ProconipDmxExtensionEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_dmx_extension_enabled()`."""

    _attr_name = "DMX Extension enabled"
    _attr_icon = "mdi:check-circle"
    _attr_unique_id = "is_dmx_extension_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_dmx_extension_enabled()
