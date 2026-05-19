"""DataUpdateCoordinator for ProCon.IP Pool Controller."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from proconip import (
    BadCredentialsException,
    BadStatusCodeException,
    GetDmxData,
    GetStateData,
    ProconipApiException,
    TimeoutException,
)

from .api import ProconipApiClient
from .const import (
    CONF_DMX_LIGHTS,
    DMX_DEBOUNCE_SECONDS,
    DMX_QUIET_WINDOW_SECONDS,
    DOMAIN,
    LOGGER,
)


class ProconipPoolControllerDataUpdateCoordinator(DataUpdateCoordinator[GetStateData]):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry
    config_entry_id: str
    data: GetStateData

    def __init__(
        self,
        hass: HomeAssistant,
        client: ProconipApiClient,
        update_interval_in_seconds: float,
        config_entry_id: str,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.client = client
        self.config_entry_id = config_entry_id
        self._active_dosage_relays: dict[int, bool] = {}

        # DMX state
        self._dmx_shadow: GetDmxData | None = None
        self._dmx_last_write: datetime | None = None
        self._dmx_flush_task: asyncio.Task[None] | None = None
        self._dmx_flush_lock = asyncio.Lock()

        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=update_interval_in_seconds),
            update_method=self.proconip_update_method,
        )

    @property
    def dmx_lights_configured(self) -> bool:
        """True if the user has declared at least one DMX light in the entry options."""
        return bool(self.config_entry.options.get(CONF_DMX_LIGHTS))

    @property
    def dmx_shadow(self) -> GetDmxData | None:
        """Current DMX shadow (None until first poll seeds it)."""
        return self._dmx_shadow

    async def proconip_update_method(self) -> GetStateData:
        """Update data via library."""
        try:
            data = await self.client.async_get_data()
        except BadCredentialsException as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except (
            BadStatusCodeException,
            ProconipApiException,
            TimeoutException,
        ) as exception:
            raise UpdateFailed(exception) from exception

        self._active_dosage_relays = {
            data.chlorine_dosage_relay_id: data.is_chlorine_dosage_enabled(),
            data.ph_minus_dosage_relay_id: data.is_ph_minus_dosage_enabled(),
            data.ph_plus_dosage_relay_id: data.is_ph_plus_dosage_enabled(),
        }

        if data.is_dmx_enabled() and self.dmx_lights_configured:
            await self._maybe_refresh_dmx_shadow()
        elif self._dmx_shadow is not None:
            # DMX flipped off on the controller (or got disabled while the
            # integration was running). Drop the shadow so light entities
            # report `available = False` rather than keeping writes flowing
            # against a DMX-disabled controller.
            LOGGER.info("Controller reports DMX as disabled; clearing local DMX shadow.")
            self._dmx_shadow = None

        return data

    async def _maybe_refresh_dmx_shadow(self) -> None:
        """Fetch DMX from controller; apply only if outside the quiet window."""
        try:
            fresh = await self.client.async_get_dmx()
        except (
            BadStatusCodeException,
            ProconipApiException,
            TimeoutException,
        ) as exception:
            LOGGER.warning("DMX poll failed: %s", exception)
            return

        if self._dmx_last_write is None or self._dmx_quiet_window_elapsed():
            self._dmx_shadow = fresh

    def _dmx_quiet_window_elapsed(self) -> bool:
        if self._dmx_last_write is None:
            return True
        elapsed = (datetime.now(tz=UTC) - self._dmx_last_write).total_seconds()
        return elapsed > DMX_QUIET_WINDOW_SECONDS

    def schedule_dmx_flush(self) -> None:
        """Mutate-then-flush trigger called by light entities after shadow updates."""
        self._dmx_last_write = datetime.now(tz=UTC)
        if self._dmx_flush_task is not None and not self._dmx_flush_task.done():
            self._dmx_flush_task.cancel()
        self._dmx_flush_task = self.hass.async_create_task(self._flush_dmx())

    async def _flush_dmx(self) -> None:
        try:
            await asyncio.sleep(DMX_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            return
        if self._dmx_shadow is None:
            return
        async with self._dmx_flush_lock:
            try:
                await self.client.async_set_dmx(self._dmx_shadow)
            except (
                BadStatusCodeException,
                ProconipApiException,
                TimeoutException,
            ) as exception:
                LOGGER.warning("DMX flush failed: %s", exception)
                return
            self._dmx_last_write = datetime.now(tz=UTC)

    async def async_shutdown(self) -> None:
        """Cancel pending DMX flush on entry unload."""
        if self._dmx_flush_task is not None and not self._dmx_flush_task.done():
            self._dmx_flush_task.cancel()
        await super().async_shutdown()

    def is_active_dosage_relay(self, relay_id: int) -> bool:
        """Return True if the given relay_id refers to an active dosage relay."""
        return self._active_dosage_relays.get(relay_id, False)
