"""Switch platform for ProCon.IP Pool Controller."""
from homeassistant.components.switch import SwitchEntity

from .const import DEFAULT_NAME
from .const import DOMAIN
from .const import ICON
from .const import SWITCH
from .entity import ProconipEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices([ProconipRelay1Switch(coordinator, entry)])


class ProconipRelay1Switch(ProconipEntity, SwitchEntity):
    """proconip switch class."""

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Turn on the switch."""
        await self.coordinator.api.async_switch_on(0)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Turn off the switch."""
        await self.coordinator.api.async_switch_off(0)
        await self.coordinator.async_request_refresh()

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{DEFAULT_NAME}_relay_1"

    @property
    def icon(self):
        """Return the icon of this switch."""
        return ICON

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data.get_relay(0).is_on()
