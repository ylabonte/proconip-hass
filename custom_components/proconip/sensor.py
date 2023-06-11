"""Sensor platform for ProCon.IP Pool Controller."""

from .const import DEFAULT_NAME
from .const import DOMAIN
from .const import ELECTRODE_ICON
from .entity import ProconipEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([
        ProconipRedoxSensor(coordinator, entry),
        ProconipPhSensor(coordinator, entry)])


class ProconipRedoxSensor(ProconipEntity):
    """proconip Redox Sensor class."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DEFAULT_NAME}_redox"

    @property
    def state(self):
        """Return the state of the sensor."""
        return "%.1f" % round(self.coordinator.data.redox_electrode.value, 1)

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ELECTRODE_ICON

    @property
    def device_class(self):
        """Return device class of the sensor."""
        return "proconip__custom_device_class"

    @property
    def suggested_unit_of_measurement(self):
        """Return measurement unit."""
        return self.coordinator.data.redox_electrode.unit


class ProconipPhSensor(ProconipEntity):
    """proconip pH Sensor class."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{DEFAULT_NAME}_ph"

    @property
    def state(self):
        """Return the state of the sensor."""
        return "%.2f" % round(self.coordinator.data.ph_electrode.value, 2)

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return ELECTRODE_ICON

    @property
    def device_class(self):
        """Return device class of the sensor."""
        return "proconip__custom_device_class"

    @property
    def suggested_unit_of_measurement(self):
        """Return measurement unit."""
        return self.coordinator.data.ph_electrode.unit
