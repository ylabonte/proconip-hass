"""Custom integration to integrate ProCon.IP Pool Controller with Home Assistant.

For more details about this integration, please refer to
https://github.com/ylabonte/proconip-hass
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant

from .api import ProconipApiClient
from .const import DOMAIN
from .coordinator import ProconipPoolControllerDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = ProconipPoolControllerDataUpdateCoordinator(
        hass=hass,
        client=ProconipApiClient(
            base_url=entry.options[CONF_URL],
            username=entry.options[CONF_USERNAME],
            password=entry.options[CONF_PASSWORD],
            hass=hass,
        ),
        update_interval_in_seconds=entry.options[CONF_SCAN_INTERVAL],
        config_entry_id=entry.entry_id,
        config_entry=entry,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await hass.data[DOMAIN][entry.entry_id].async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry=entry, platforms=PLATFORMS)
    entry.async_on_unload(func=entry.add_update_listener(listener=async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(
        entry=entry, platforms=PLATFORMS
    ):
        # Cancel any pending DMX flush task before dropping the coordinator
        # so a queued write can't fire after the entry is gone.
        coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
            entry.entry_id
        ]
        await coordinator.async_shutdown()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
