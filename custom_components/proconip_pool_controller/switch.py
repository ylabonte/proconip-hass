"""Switch platform for proconip."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from proconip import BadRelayException

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the switch platform."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays: list[ProconipPoolControllerEntity] = []
    for i in range(number_of_relays):
        relays.append(
            ProconipPoolControllerRelaySwitch(
                coordinator=coordinator,
                relay_no=i + 1,
                is_active_dosage_relay=coordinator.is_active_dosage_relay(relay_id=i),
                instance_id=entry.entry_id,
            )
        )
        relays.append(
            ProconipPoolControllerRelayMode(
                coordinator=coordinator, relay_no=i + 1, instance_id=entry.entry_id
            )
        )
    async_add_devices(relays)


class ProconipPoolControllerRelaySwitch(ProconipPoolControllerEntity, SwitchEntity):
    """ProCon.IP Pool Controller relay switch class."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "relay"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        is_active_dosage_relay: bool,
        instance_id: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator=coordinator)
        # A relay the controller uses for active dosing may only run under its
        # dosage control (auto mode or a timed manual dosing), never be switched
        # on permanently. The switch stays available so its state is visible and
        # it can still be switched off; only turning it on is refused. The
        # coordinator reloads the entry when the dosing configuration changes.
        self._is_active_dosage_relay = is_active_dosage_relay
        self._relay_no = relay_no
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(relay_id=self._relay_id)
        self._attr_entity_registry_visible_default = not self.coordinator.data.is_dosage_relay(
            relay_id=self._relay_id
        )
        self._attr_translation_placeholders = {
            "relay_no": str(relay_no),
            "device_name": self._relay.name,
        }
        self._attr_unique_id = f"relay_{relay_no}_{instance_id}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch (refused for an active dosage relay)."""
        if self._is_active_dosage_relay:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="dosage_relay_permanent_on",
                translation_placeholders={"relay_no": str(self._relay_no)},
            )
        try:
            await self.coordinator.client.async_switch_on(relay_id=self._relay_id)
        except BadRelayException as exception:
            # The library also refuses relays that only a *disabled* dosage
            # channel points at (its check ignores the enable flags).
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="relay_reserved_for_dosage",
                translation_placeholders={"relay_no": str(self._relay_no)},
            ) from exception
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        await self.coordinator.client.async_switch_off(relay_id=self._relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get_relay(relay_id=self._relay_id).is_on()


class ProconipPoolControllerRelayMode(ProconipPoolControllerEntity, SwitchEntity):
    """Proconip auto-mode switch class."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_translation_key = "relay_auto_mode"

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        instance_id: str,
    ) -> None:
        """Initialize new relay mode."""
        super().__init__(coordinator=coordinator)
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(relay_id=self._relay_id)
        self._attr_entity_registry_visible_default = not self.coordinator.data.is_dosage_relay(
            relay_id=self._relay_id
        )
        self._attr_translation_placeholders = {
            "relay_no": str(relay_no),
            "device_name": self._relay.name,
        }
        self._attr_unique_id = f"relay_{relay_no}_auto_mode_{instance_id}"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set relay to auto mode."""
        await self.coordinator.client.async_switch_to_auto(relay_id=self._relay_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Set relay to manual mode."""
        if self._relay.is_on():
            await self.coordinator.client.async_switch_on(relay_id=self._relay_id)
        else:
            await self.coordinator.client.async_switch_off(relay_id=self._relay_id)
        await self.coordinator.async_request_refresh()

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.coordinator.data.get_relay(relay_id=self._relay_id).is_auto_mode()
