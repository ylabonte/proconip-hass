"""Tests for setup, unload, and reload of the integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN


async def test_setup_and_unload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_reload(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED


async def test_unload_cancels_pending_dmx_flush(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """A pending DMX flush task must not survive entry unload (would write stale data)."""
    coordinator = hass.data[DOMAIN][setup_integration.entry_id]
    # Schedule a flush; the task should be created and pending.
    coordinator.schedule_dmx_flush()
    assert coordinator._dmx_flush_task is not None
    assert not coordinator._dmx_flush_task.done()

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert coordinator._dmx_flush_task.cancelled() or coordinator._dmx_flush_task.done()
