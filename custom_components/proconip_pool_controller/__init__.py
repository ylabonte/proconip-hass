"""Custom integration to integrate ProCon.IP Pool Controller with Home Assistant.

For more details about this integration, please refer to
https://github.com/ylabonte/proconip-hass
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_URL,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    Platform,
)
from homeassistant.core import HomeAssistant

from .api import ProconipApiClient
from .const import DOMAIN, LOGGER
from .coordinator import ProconipPoolControllerDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
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
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await hass.data[DOMAIN][entry.entry_id].async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(
        entry=entry, platforms=PLATFORMS
    )
    entry.async_on_unload(func=entry.add_update_listener(listener=async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(
        entry=entry, platforms=PLATFORMS
    ):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass=hass, entry=entry)
    await async_setup_entry(hass=hass, entry=entry)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate config entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version > 2:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        if config_entry.minor_version < 2:
            newData = {**config_entry.data}
            newOptions = {**config_entry.options}
            """Seperate data and options that were accidentially mixed up."""
            newData[CONF_NAME] = (
                newData[CONF_NAME] if CONF_NAME in newData else config_entry.title
            )
            newOptions[CONF_URL] = (
                newOptions[CONF_URL] if CONF_URL in newOptions else newData[CONF_URL]
            )
            newOptions[CONF_USERNAME] = (
                newOptions[CONF_USERNAME]
                if CONF_USERNAME in newOptions
                else newData[CONF_USERNAME]
            )
            newOptions[CONF_PASSWORD] = (
                newOptions[CONF_PASSWORD]
                if CONF_PASSWORD in newOptions
                else newData[CONF_PASSWORD]
            )
            newOptions[CONF_SCAN_INTERVAL] = (
                newOptions[CONF_SCAN_INTERVAL]
                if CONF_SCAN_INTERVAL in newOptions
                else newData[CONF_SCAN_INTERVAL] if CONF_SCAN_INTERVAL in newData else 3
            )
            if CONF_URL in newData:
                del newData[CONF_URL]
            if CONF_USERNAME in newData:
                del newData[CONF_USERNAME]
            if CONF_PASSWORD in newData:
                del newData[CONF_PASSWORD]
            if CONF_SCAN_INTERVAL in newData:
                del newData[CONF_SCAN_INTERVAL]

            config_entry.version = 1
            config_entry.minor_version = 2
            hass.config_entries.async_update_entry(
                entry=config_entry, data=newData, options=newOptions
            )

    LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
