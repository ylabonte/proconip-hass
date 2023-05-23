"""Sensor platform for ProCon.IP Pool Controller."""
from .const import DEFAULT_NAME
from .const import DOMAIN
from .const import ICON
from .const import SENSOR
from .entity import ProconipEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([ProconipRedoxSensor(coordinator, entry)])


class ProconipRedoxSensor(ProconipEntity):
    """proconip Redox Sensor class."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DEFAULT_NAME}_redox"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data.redox_electrode.value

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ICON

    @property
    def device_class(self):
        """Return device class of the sensor."""
        return "proconip__custom_device_class"

    @property
    def suggested_unit_of_measurement(self):
        """Return measurement unit"""
        return self.coordinator.data.redox_electrode.unit
