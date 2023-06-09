"""Switch platform for ProCon.IP Pool Controller."""
from homeassistant.components.switch import SwitchEntity

from .const import DEFAULT_NAME
from .const import DOMAIN
from .const import RELAY_ICON
from .const import RELAY_MODE_ICON
from .entity import ProconipEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays = []
    for i in range(number_of_relays):
        relays.append(ProconipRelaySwitch(coordinator, entry, i))
        relays.append(ProconipRelayMode(coordinator, entry, i))
    async_add_devices(relays)


class ProconipRelaySwitch(ProconipEntity, SwitchEntity):
    """proconip switch class."""

    def __init__(self, coordinator, config_entry, relay_id):
        super().__init__(coordinator, config_entry)
        self.relay_id = relay_id

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Turn on the switch."""
        await self.coordinator.api.async_switch_on(self.relay_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Turn off the switch."""
        await self.coordinator.api.async_switch_off(self.relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{DEFAULT_NAME}_relay_{self.relay_id + 1}"

    @property
    def icon(self):
        """Return the icon of this switch."""
        return RELAY_ICON

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data.get_relay(self.relay_id).is_on()


class ProconipRelayMode(ProconipEntity, SwitchEntity):
    """proconip switch class."""

    def __int__(self, coordinator, config_entry, relay_id):
        super().__int__(coordinator, config_entry)
        self.relay_id = relay_id

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Set relay to auto mode."""
        await self.coordinator.api.async_set_auto_mode(self.relay_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Set relay to manual mode."""
        if self.coordinator.data.get_relay(self.relay_id).is_on():
            await self.coordinator.api.async_switch_on(self.relay_id)
        else:
            await self.coordinator.api.async_switch_off(self.relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{DEFAULT_NAME}_relay_{self.relay_id + 1}_mode"

    @property
    def icon(self):
        """Return the icon of this switch."""
        return RELAY_MODE_ICON

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self.coordinator.data.get_relay(self.relay_id).is_auto_mode()
