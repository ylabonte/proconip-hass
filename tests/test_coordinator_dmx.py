"""Tests for DMX shadow / debounce / quiet window in the coordinator."""

from __future__ import annotations

import asyncio
import contextlib
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
    get_dmx_mock = AsyncMock(return_value=fresh_dmx)
    coordinator.client.async_get_dmx = get_dmx_mock

    # Inside the quiet window: just-now write timestamp -> shadow stays
    # None AND the network call is skipped entirely (avoid burning a
    # controller round-trip on a response we'd discard anyway).
    coordinator._dmx_shadow = None
    coordinator._dmx_last_write = datetime.now(tz=UTC)
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is None
    assert get_dmx_mock.call_count == 0, "async_get_dmx must not be called inside the quiet window"

    # Outside the quiet window: shadow updates to the fetched value.
    coordinator._dmx_last_write = datetime.now(tz=UTC) - timedelta(
        seconds=DMX_QUIET_WINDOW_SECONDS + 0.5,
    )
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is fresh_dmx
    assert get_dmx_mock.call_count == 1

    # Never written: shadow updates on first poll (last_write is None branch).
    coordinator._dmx_shadow = None
    coordinator._dmx_last_write = None
    await coordinator._maybe_refresh_dmx_shadow()
    assert coordinator._dmx_shadow is fresh_dmx
    assert get_dmx_mock.call_count == 2


async def test_dmx_shadow_cleared_when_controller_disables_dmx(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    """If a controller previously reported DMX enabled then disables it, the
    cached shadow must be dropped so light entities stop being available."""
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    # Pretend a previous poll seeded a shadow while DMX was still enabled.
    sentinel_shadow = AsyncMock(name="stale_shadow")
    coordinator._dmx_shadow = sentinel_shadow

    # Force one update — the fixture's GetState.csv reports DMX disabled, so
    # the coordinator should drop the shadow on this poll.
    await coordinator.async_refresh()
    assert coordinator.dmx_shadow is None


async def test_concurrent_dmx_writes_serialized_even_after_cancellation(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    """The DMX flush lock must hold across a cancellation-orphaned write.

    Pre-fix: `async with _dmx_flush_lock:` released the lock the instant
    the cancel handler returned, even though the shielded POST was still
    running. A follow-up scheduled flush could acquire the (free) lock
    and start a second POST in parallel, defeating the lock entirely
    and putting two overlapping writes on the wire.

    This test interleaves two POSTs and asserts the second one's start
    timestamp is >= the first one's end timestamp — i.e. they never
    overlap.
    """
    import time

    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    coordinator._dmx_shadow = AsyncMock()

    write_calls: list[dict[str, float]] = []

    async def tracked_slow_write(*_args: object, **_kwargs: object) -> str:
        idx = len(write_calls)
        write_calls.append({"start": time.monotonic(), "end": 0.0})
        await asyncio.sleep(0.3)
        write_calls[idx]["end"] = time.monotonic()
        return "OK"

    coordinator.client.async_set_dmx = AsyncMock(side_effect=tracked_slow_write)

    # First flush: debounces, then starts POST #1.
    coordinator.schedule_dmx_flush()
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.05)
    assert len(write_calls) == 1, "POST #1 should be in flight"

    # Second schedule mid-POST: pre-fix this would race POST #2 against
    # the still-running POST #1.
    coordinator.schedule_dmx_flush()

    # Wait for both POSTs to settle. Generous bound:
    # POST#1 (0.3s) + debounce (0.15s) + POST#2 (0.3s) + buffer.
    await asyncio.sleep(1.0)
    if coordinator._dmx_flush_task is not None:
        with contextlib.suppress(asyncio.CancelledError, TimeoutError):
            await asyncio.wait_for(coordinator._dmx_flush_task, timeout=2.0)

    assert len(write_calls) == 2, f"Expected exactly 2 POSTs, got {len(write_calls)}"
    # The crux: POST #2 must not start until POST #1 has finished.
    assert write_calls[1]["start"] >= write_calls[0]["end"], (
        f"Concurrent writes detected: POST#2 start={write_calls[1]['start']:.3f}, "
        f"POST#1 end={write_calls[0]['end']:.3f} — lock was released prematurely"
    )


async def test_in_flight_dmx_write_not_cancelled_by_subsequent_schedule(
    hass: HomeAssistant,
    dmx_config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    """A schedule_dmx_flush() during an active POST must not abort the POST.

    Without the asyncio.shield around `async_set_dmx`, a cancel would tear
    aiohttp's exchange down mid-send and the controller would see a
    half-sent payload. Simulate a slow write and confirm the original
    POST runs to completion even when a second schedule fires during it.
    """
    assert await hass.config_entries.async_setup(dmx_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_config_entry.entry_id]

    # Seed a shadow so the flush has something to send.
    coordinator._dmx_shadow = AsyncMock()

    write_completed = asyncio.Event()

    async def slow_write(*_args: object, **_kwargs: object) -> str:
        await asyncio.sleep(0.3)
        write_completed.set()
        return "OK"

    coordinator.client.async_set_dmx = AsyncMock(side_effect=slow_write)

    # Kick off the first flush — debounce, then start the slow POST.
    coordinator.schedule_dmx_flush()
    # Wait past the debounce so the POST is in flight, but not past its
    # 0.3 s simulated duration.
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.05)
    assert not write_completed.is_set(), "POST should still be in flight here"

    # Second schedule arrives mid-POST. Pre-shield, this would cancel
    # the in-flight write; post-shield, it just queues a follow-up
    # debounced flush.
    coordinator.schedule_dmx_flush()

    # The original POST must run to completion (within a generous bound).
    await asyncio.wait_for(write_completed.wait(), timeout=2.0)
    assert write_completed.is_set(), "Original POST was cancelled mid-flight"
    # And async_set_dmx was actually called (sanity check on the path).
    assert coordinator.client.async_set_dmx.call_count >= 1

    # Drain the follow-up debounced flush triggered by the second
    # schedule so pytest-homeassistant-custom-component's lingering-
    # task guard doesn't fail teardown.
    if coordinator._dmx_flush_task is not None:
        with contextlib.suppress(asyncio.CancelledError, TimeoutError):
            await asyncio.wait_for(coordinator._dmx_flush_task, timeout=2.0)


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
