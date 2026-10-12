"""Switch platform for proconip."""

from __future__ import annotations

import asyncio

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from proconip import DosageTarget, GetStateData

from .const import DOMAIN, LOGGER
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


def resolve_dosage_channel(data: GetStateData, relay_id: int) -> DosageTarget | None:
    """Return the dosage channel the controller routes a relay to.

    Mirrors the vendor web GUI (`topleft.htm` `RButton`, L660-682): a dosage
    relay belongs to the first *enabled* channel whose relay matches, checked
    in the order chlorine, pH-, pH+. Channels may share a relay, so matching
    on the relay id alone would pick a disabled channel.
    """
    for target, channel_relay_id, enabled in (
        (DosageTarget.CHLORINE, data.chlorine_dosage_relay_id, data.is_chlorine_dosage_enabled()),
        (DosageTarget.PH_MINUS, data.ph_minus_dosage_relay_id, data.is_ph_minus_dosage_enabled()),
        (DosageTarget.PH_PLUS, data.ph_plus_dosage_relay_id, data.is_ph_plus_dosage_enabled()),
    ):
        if enabled and channel_relay_id == relay_id:
            return target
    return None


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
    _countdown_task: asyncio.Task[None] | None = None

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
        # Channel routing and the chlorine supply type are read at setup; the
        # coordinator reloads the entry when the supply type flips, so the
        # limits follow the controller.
        self._channel = resolve_dosage_channel(data=coordinator.data, relay_id=self._relay_id)
        self._is_electrolysis = (
            self._channel is DosageTarget.CHLORINE and coordinator.data.is_electrolysis_enabled()
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
        if self._channel is DosageTarget.CHLORINE:
            await self.coordinator.client.async_start_chlorine_dosage(
                duration_in_seconds=countdown_value
            )
        elif self._channel is DosageTarget.PH_MINUS:
            await self.coordinator.client.async_start_ph_minus_dosage(
                duration_in_seconds=countdown_value
            )
        elif self._channel is DosageTarget.PH_PLUS:
            await self.coordinator.client.async_start_ph_plus_dosage(
                duration_in_seconds=countdown_value
            )
        else:
            LOGGER.warning(
                "Relay %s is no longer routed to an enabled dosage channel; not dosing.",
                self._relay_id + 1,
            )
            return None
        self._start_countdown(seconds=countdown_value)
        return await self.coordinator.async_request_refresh()

    def _start_countdown(self, seconds: int) -> None:
        """(Re)start the local UI countdown, replacing any running one.

        Runs as a config-entry background task, so it is cancelled with the
        entry (e.g. on the mode-flip reload) instead of outliving it; a new
        value cancels the previous countdown so only one loop ticks.
        """
        self._cancel_countdown()
        self._countdown_task = self.coordinator.config_entry.async_create_background_task(
            hass=self.hass,
            target=self.countdown(value=seconds),
            name=f"proconip dosage countdown relay {self._relay_id + 1}",
        )

    def _cancel_countdown(self) -> None:
        """Cancel the running countdown task, if any."""
        if self._countdown_task is not None and not self._countdown_task.done():
            self._countdown_task.cancel()
        self._countdown_task = None

    async def async_will_remove_from_hass(self) -> None:
        """Stop the countdown when the entity goes away."""
        self._cancel_countdown()
        await super().async_will_remove_from_hass()


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
