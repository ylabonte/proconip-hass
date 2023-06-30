"""Switch platform for proconip."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
import asyncio

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up the select platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays = []
    for i in range(number_of_relays):
        if coordinator.data.is_dosage_relay(relay_id=i):
            relays.append(
                ProconipPoolControllerDosageRelayTimer(
                    coordinator=coordinator,
                    relay_no=i + 1,
                )
            )
        # else:
        #     relays.append(
        #         ProconipPoolControllerRelayNumberEntity(
        #             coordinator=coordinator,
        #             relay_no=i + 1,
        #         )
        #     )
    async_add_devices(relays)


class ProconipPoolControllerDosageRelayTimer(
    ProconipPoolControllerEntity, NumberEntity
):
    """ProCon.IP Pool Controller relay dosage relay timer class."""

    _attr_mode = "box"
    _attr_native_max_value = 600
    _attr_native_min_value = 5
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "seconds"
    _countdown_value: int = 0

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator)
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(self._relay_id)
        self._attr_name = f"Relay No. {relay_no} Dosage ({self._relay.name})"
        self._attr_unique_id = f"relay_dosage_{relay_no}"

    @property
    def icon(self) -> str | None:
        return (
            "mdi:toggle-switch-variant"
            if self.coordinator.data.get_relay(self._relay_id).is_on()
            else "mdi:toggle-switch-variant-off"
        )

    @property
    def native_value(self) -> float | None:
        """Return the current dosage timer countdown."""
        return self._countdown_value

    async def countdown(self, value: int | None = None) -> None:
        """Internally countdown the dosage timer."""
        if value is not None:
            self._countdown_value = value
        while self._countdown_value > 0:
            self._countdown_value -= 1
            await asyncio.sleep(1)

    async def async_set_native_value(self, value: float) -> None:
        """Set dosage timer."""
        countdown_value = int(value)
        if self.coordinator.data.chlorine_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_chlorine_dosage(countdown_value)
        elif self.coordinator.data.ph_minus_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_ph_minus_dosage(countdown_value)
        elif self.coordinator.data.ph_plus_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_ph_plus_dosage(countdown_value)
        loop = asyncio.get_event_loop()
        loop.create_task(self.countdown(countdown_value))
        return await self.coordinator.async_request_refresh()


# class ProconipPoolControllerRelayNumberEntity(
#     ProconipPoolControllerEntity, NumberEntity
# ):
#     """ProCon.IP Pool Controller relay as NumberEntity class."""

#     _attr_mode = "slider"
#     _attr_native_max_value = 2
#     _attr_native_min_value = 0
#     _attr_native_step = 1

#     def __init__(
#         self,
#         coordinator: ProconipPoolControllerDataUpdateCoordinator,
#         relay_no: int,
#     ) -> None:
#         """Initialize the switch class."""
#         super().__init__(coordinator)
#         self._relay_id = relay_no - 1
#         self._relay = coordinator.data.get_relay(self._relay_id)
#         self._attr_name = f"Relay No. {relay_no} ({self._relay.name})"
#         self._attr_unique_id = f"relay_{relay_no}"

#     @property
#     def icon(self) -> str | None:
#         return (
#             "mdi:toggle-switch-variant"
#             if self._relay.is_on()
#             else "mdi:toggle-switch-variant-off"
#         )

#     @property
#     def native_value(self) -> float | None:
#         """Return the current value."""
#         if self._relay.is_auto_mode():
#             return 2
#         if self._relay.is_off():
#             return 1
#         return 0

#     async def async_set_native_value(self, value: float) -> None:
#         """Set relay state."""
#         if value == 0:
#             await self.coordinator.client.async_switch_on(relay_id=self._relay_id)
#         if value == 1:
#             await self.coordinator.client.async_switch_off(relay_id=self._relay_id)
#         if value == 2:
#             await self.coordinator.client.async_switch_to_auto(relay_id=self._relay_id)
#         return await self.coordinator.async_request_refresh()
