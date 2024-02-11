"""Switch platform for proconip."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays = []
    for i in range(number_of_relays):
        relays.append(
            ProconipPoolControllerRelaySelect(
                coordinator=coordinator,
                relay_no=i + 1,
                available=not coordinator.data.is_dosage_relay(relay_id=i),
                instance_id=entry.entry_id,
            )
        )
    async_add_devices(relays)


class ProconipPoolControllerRelaySelect(ProconipPoolControllerEntity, SelectEntity):
    """ProCon.IP Pool Controller relay select class."""

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        available: bool,
        instance_id: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator=coordinator)
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(relay_id=self._relay_id)
        self._attr_available = available
        self._attr_entity_registry_visible_default = (
            not self.coordinator.data.is_dosage_relay(relay_id=self._relay_id)
        )
        self._attr_name = f"Relay No. {relay_no}: {self._relay.name}"
        self._attr_options = (
            ["auto", "off"]
            if self.coordinator.is_active_dosage_relay(relay_id=self._relay_id)
            else [
                "auto",
                "on",
                "off",
            ]
        )
        self._attr_unique_id = f"relay_select_{relay_no}_{instance_id}"

    @property
    def icon(self) -> str | None:
        """Return icon depending on current option/state."""
        return (
            "mdi:toggle-switch-variant"
            if self.coordinator.data.get_relay(relay_id=self._relay_id).is_on()
            else "mdi:toggle-switch-variant-off"
        )

    @property
    def current_option(self) -> str | None:
        """Return currently selected option."""
        relay = self.coordinator.data.get_relay(relay_id=self._relay_id)
        if relay.is_auto_mode():
            return "auto"
        if relay.is_on():
            return "on"
        return "off"

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if option == "auto":
            await self.coordinator.client.async_switch_to_auto(relay_id=self._relay_id)
        elif option == "on":
            await self.coordinator.client.async_switch_on(relay_id=self._relay_id)
        else:
            await self.coordinator.client.async_switch_off(relay_id=self._relay_id)
        await self.coordinator.async_request_refresh()
