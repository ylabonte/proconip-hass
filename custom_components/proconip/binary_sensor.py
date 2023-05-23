"""Binary sensor platform for ProCon.IP Pool Controller."""
from homeassistant.components.binary_sensor import BinarySensorEntity

from .const import BINARY_SENSOR
from .const import BINARY_SENSOR_DEVICE_CLASS
from .const import DEFAULT_NAME
from .const import DOMAIN
from .entity import ProconipEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([
        ProconipChlorineDosageEnabledBinarySensor(coordinator, entry),
        # ProconipElectrolysisEnabledBinarySensor(coordinator, entry),
        # ProconipPhMinusDosageEnabledBinarySensor(coordinator, entry),
        # ProconipDosageEnabledBinarySensor(coordinator, entry),
        # ProconipTcpIpBoostEnabledBinarySensor(coordinator, entry),
        # ProconipSdCardEnabledBinarySensor(coordinator, entry),
        # ProconipDmxEnabledBinarySensor(coordinator, entry),
        # ProconipAvatarEnabledBinarySensor(coordinator, entry),
        # ProconipRelayExtensionEnabledBinarySensor(coordinator, entry),
        # ProconipHighBusLoadEnabledBinarySensor(coordinator, entry),
        # ProconipRepeatedMailEnabledBinarySensor(coordinator, entry),
        # ProconipDmxExtensionEnabledBinarySensor(coordinator, entry),
    ])


class ProconipChlorineDosageEnabledBinarySensor(ProconipEntity, BinarySensorEntity):
    """proconip binary_sensor class for `GetStateData.is_chlorine_dosage_enabled()`."""

    @property
    def name(self):
        """Return the name of the binary_sensor."""
        return f"{DEFAULT_NAME}_chlorine_dosage_enabled"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return self.coordinator.data.is_chlorine_dosage_enabled()
