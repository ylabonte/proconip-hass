"""Tests for DMX shadow / debounce / quiet window in the coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from aioresponses import aioresponses
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import (
    CONF_DMX_LIGHTS,
    DMX_DEBOUNCE_SECONDS,
    DMX_QUIET_WINDOW_SECONDS,
    DOMAIN,
)


@pytest.fixture
def dmx_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Pool",
        data={"name": "Test Pool"},
        options={
            CONF_URL: "http://192.0.2.10",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "admin",
            CONF_SCAN_INTERVAL: 30,
            CONF_DMX_LIGHTS: [
                {
                    "slug": "pool_main",
                    "name": "Pool main",
                    "type": "rgbw",
                    "start_channel": 1,
                }
            ],
        },
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)
    return entry


async def test_dmx_shadow_field_exists(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]
    # The fixture controller's GetState says DMX is disabled, so the shadow
    # is intentionally None. Verify the property exists and is shape-correct.
    assert hasattr(coordinator, "dmx_shadow")
    assert hasattr(coordinator, "dmx_lights_configured")
    assert coordinator.dmx_lights_configured is True


async def test_schedule_dmx_flush_calls_set_dmx_after_debounce(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    coordinator._dmx_shadow = AsyncMock()
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")
    coordinator.schedule_dmx_flush()
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    coordinator.client.async_set_dmx.assert_called_once()


async def test_rapid_writes_coalesce_into_single_flush(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    coordinator._dmx_shadow = AsyncMock()
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")

    for _ in range(5):
        coordinator.schedule_dmx_flush()
        await asyncio.sleep(0.01)

    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    assert coordinator.client.async_set_dmx.call_count == 1


async def test_quiet_window_suppresses_dmx_from_poll(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    fresh_dmx = AsyncMock(name="fresh_dmx")
    coordinator.client.async_get_dmx = AsyncMock(return_value=fresh_dmx)

    # Inside the quiet window: just-now write timestamp -> shadow stays None.
    coordinator._dmx_shadow = None
    coordinator._dmx_last_write = datetime.now(tz=UTC)
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is None

    # Outside the quiet window: shadow updates to the fetched value.
    coordinator._dmx_last_write = datetime.now(tz=UTC) - timedelta(
        seconds=DMX_QUIET_WINDOW_SECONDS + 0.5,
    )
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is fresh_dmx

    # Never written: shadow updates on first poll (last_write is None branch).
    coordinator._dmx_shadow = None
    coordinator._dmx_last_write = None
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is fresh_dmx


async def test_flush_failure_logs_and_does_not_crash(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    from proconip import ProconipApiException

    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    coordinator._dmx_shadow = AsyncMock()
    coordinator.client.async_set_dmx = AsyncMock(
        side_effect=ProconipApiException("network gone"),
    )
    coordinator.schedule_dmx_flush()
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    coordinator.client.async_set_dmx.assert_called_once()
    # No exception escaped — that's the assertion.
