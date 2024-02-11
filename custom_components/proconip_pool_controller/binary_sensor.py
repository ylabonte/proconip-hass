"""Binary sensor platform for ProCon.IP Pool Controller."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_devices(
        [
            ProconipChlorineDosageEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipElectrolysisEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipPhMinusDosageEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipPhPlusDosageEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipTcpIpBoostEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipSdCardEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipDmxEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipAvatarEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipRelayExtensionEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipHighBusLoadEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipFlowSensorEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipRepeatedMailEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
            ProconipDmxExtensionEnabledBinarySensor(
                coordinator=coordinator, instance_id=entry.entry_id
            ),
        ]
    )


class ProconipChlorineDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_chlorine_dosage_enabled()`."""

    _attr_name = "Chlorine Dosage enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_chlorine_dosage_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_chlorine_dosage_enabled()


class ProconipElectrolysisEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_electrolysis_enabled()`."""

    _attr_name = "Electrolysis enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_electrolysis_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_electrolysis_enabled()


class ProconipPhMinusDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_ph_minus_dosage_enabled()`."""

    _attr_name = "pH Minus Dosage enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_ph_minus_dosage_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_ph_minus_dosage_enabled()


class ProconipPhPlusDosageEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_ph_plus_dosage_enabled()`."""

    _attr_name = "pH Plus Dosage enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_ph_plus_dosage_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_ph_plus_dosage_enabled()


class ProconipTcpIpBoostEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_tcpip_boost_enabled()`."""

    _attr_name = "TCP/IP Boost enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_tcpip_boost_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_tcpip_boost_enabled()


class ProconipSdCardEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_sd_card_enabled()`."""

    _attr_name = "SD Card enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_sd_card_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_sd_card_enabled()


class ProconipDmxEnabledBinarySensor(ProconipPoolControllerEntity, BinarySensorEntity):
    """ProCon.IP binary_sensor class for `GetStateData.is_dmx_enabled()`."""

    _attr_name = "DMX enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_dmx_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_dmx_enabled()


class ProconipAvatarEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_avatar_enabled()`."""

    _attr_name = "Avatar enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_avatar_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_avatar_enabled()


class ProconipRelayExtensionEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_relay_extension_enabled()`."""

    _attr_name = "Relay Extension enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_relay_extension_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_relay_extension_enabled()


class ProconipHighBusLoadEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_high_bus_load_enabled()`."""

    _attr_name = "High Bus Load enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_high_bus_load_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_high_bus_load_enabled()


class ProconipFlowSensorEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_flow_sensor_enabled()`."""

    _attr_name = "Flow Sensor enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_flow_sensor_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_flow_sensor_enabled()


class ProconipRepeatedMailEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_repeated_mails_enabled()`."""

    _attr_name = "Repeated Mails enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_repeated_mails_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_repeated_mails_enabled()


class ProconipDmxExtensionEnabledBinarySensor(
    ProconipPoolControllerEntity, BinarySensorEntity
):
    """ProCon.IP binary_sensor class for `GetStateData.is_dmx_extension_enabled()`."""

    _attr_name = "DMX Extension enabled"
    _attr_icon = "mdi:check-circle"

    def __init__(
        self, coordinator: ProconipPoolControllerDataUpdateCoordinator, instance_id: str
    ) -> None:
        super().__init__(coordinator=coordinator)
        self._attr_unique_id = f"is_dmx_extension_enabled_{instance_id}"

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_dmx_extension_enabled()
