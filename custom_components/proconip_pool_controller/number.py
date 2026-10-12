"""Switch platform for proconip."""

from __future__ import annotations

import asyncio

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator
from .entity import ProconipPoolControllerEntity

# Manual-dosing limits, mirrored from the vendor web GUI (`topleft.htm`, fw
# 1.7.6). The GUI takes a "NN:NN" string (regex /^(\d\d):(\d\d)$/, so 00:00
# is accepted) and always sends seconds: `/Command.htm?MAN_DOSAGE=<target>,<s>`.
# - liquid channels (Cl liquid, pH-, pH+): mm:ss, max 59:59 -> 0..3599 s,
#   one-second resolution;
# - chlorine with a salt electrolysis cell (DOSAGE_CNTRL bit 4): hh:mm, max
#   23:59 -> 0..86340 s, whole minutes only.
MANUAL_DOSAGE_MIN_SECONDS = 0
MANUAL_DOSAGE_MAX_SECONDS_LIQUID = 59 * 60 + 59
MANUAL_DOSAGE_MAX_SECONDS_ELECTROLYSIS = 23 * 3600 + 59 * 60
ELECTROLYSIS_DOSAGE_STEP_SECONDS = 60


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
) -> None:
    """Set up the select platform."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    number_of_relays = 16 if coordinator.data.is_relay_extension_enabled() else 8
    relays = []
    for i in range(number_of_relays):
        if coordinator.is_active_dosage_relay(relay_id=i):
            relays.append(
                ProconipPoolControllerDosageRelayTimer(
                    coordinator=coordinator,
                    relay_no=i + 1,
                    instance_id=entry.entry_id,
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


class ProconipPoolControllerDosageRelayTimer(ProconipPoolControllerEntity, NumberEntity):
    """ProCon.IP Pool Controller relay dosage relay timer class."""

    _attr_mode = NumberMode.BOX
    _attr_native_max_value = MANUAL_DOSAGE_MAX_SECONDS_LIQUID
    _attr_native_min_value = MANUAL_DOSAGE_MIN_SECONDS
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "seconds"
    _attr_translation_key = "dosage_relay"
    _countdown_value: int = 0

    def __init__(
        self,
        coordinator: ProconipPoolControllerDataUpdateCoordinator,
        relay_no: int,
        instance_id: str,
    ) -> None:
        """Initialize the switch class."""
        super().__init__(coordinator=coordinator)
        self._relay_id = relay_no - 1
        self._relay = coordinator.data.get_relay(relay_id=self._relay_id)
        self._attr_translation_placeholders = {
            "relay_no": str(relay_no),
            "device_name": self._relay.name,
        }
        self._attr_unique_id = f"relay_dosage_{relay_no}_{instance_id}"
        # The chlorine supply type is read at setup; the coordinator reloads
        # the entry when it flips, so these limits follow the controller.
        self._is_electrolysis = (
            coordinator.data.chlorine_dosage_relay_id == self._relay_id
            and coordinator.data.is_electrolysis_enabled()
        )
        if self._is_electrolysis:
            self._attr_native_max_value = MANUAL_DOSAGE_MAX_SECONDS_ELECTROLYSIS
            self._attr_native_step = ELECTROLYSIS_DOSAGE_STEP_SECONDS

    @property
    def icon(self) -> str | None:
        """Return icon depending on current state."""
        return (
            "mdi:toggle-switch-variant"
            if self.coordinator.data.get_relay(relay_id=self._relay_id).is_on()
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
            await asyncio.sleep(delay=1)

    async def async_set_native_value(self, value: float) -> None:
        """Set dosage timer."""
        countdown_value = int(value)
        if self._is_electrolysis and countdown_value % ELECTROLYSIS_DOSAGE_STEP_SECONDS:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="electrolysis_whole_minutes",
                translation_placeholders={"seconds": str(countdown_value)},
            )
        if self.coordinator.data.chlorine_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_chlorine_dosage(
                duration_in_seconds=countdown_value
            )
        elif self.coordinator.data.ph_minus_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_ph_minus_dosage(
                duration_in_seconds=countdown_value
            )
        elif self.coordinator.data.ph_plus_dosage_relay_id == self._relay_id:
            await self.coordinator.client.async_start_ph_plus_dosage(
                duration_in_seconds=countdown_value
            )
        loop = asyncio.get_event_loop()
        loop.create_task(coro=self.countdown(value=countdown_value))
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
