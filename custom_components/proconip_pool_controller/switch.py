"""Switch platform for proconip."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays = []
    for i in range(number_of_relays):
        relays.append(
            ProconipPoolControllerRelaySwitch(
                coordinator=coordinator,
                relay_no=i + 1,
                available=not coordinator.data.is_dosage_relay(relay_id=i),
            )
        )
        relays.append(
            ProconipPoolControllerRelayMode(coordinator=coordinator, relay_no=i + 1)
        )
    async_add_devices(relays)


class ProconipPoolControllerRelaySwitch(ProconipPoolControllerEntity, SwitchEntity):
    """ProCon.IP Pool Controller relay switch class."""

    _attr_icon = "mdi:light-switch"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        available: bool,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self._attr_available = available
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(self._relay_id)
        self._attr_unique_id = f"relay_{relay_no}"
        self._attr_name = f"Relay No. {relay_no}: {self._relay.name}"

    async def async_turn_on(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Turn on the switch."""
        await self.coordinator.client.async_switch_on(self._relay_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Turn off the switch."""
        await self.coordinator.client.async_switch_off(self._relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._relay.is_on()


class ProconipPoolControllerRelayMode(ProconipPoolControllerEntity, SwitchEntity):
    """Proconip auto-mode switch class."""

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
    ) -> None:
        """Initialize new relay mode."""
        super().__init__(coordinator)
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(self._relay_id)
        self._attr_unique_id = f"relay_{relay_no}_auto"
        self._attr_name = f"Relay No. {relay_no}: {self._relay.name} Auto-Mode"

    async def async_turn_on(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Set relay to auto mode."""
        await self.coordinator.client.async_set_auto_mode(self._relay_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Set relay to manual mode."""
        if self._relay.is_on():
            await self.coordinator.client.async_switch_on(self._relay_id)
        else:
            await self.coordinator.client.async_switch_off(self._relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._relay.is_auto_mode()
