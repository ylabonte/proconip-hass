"""Tests for the DMX light platform."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from aioresponses import aioresponses
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import (
    CONF_DMX_LIGHTS,
    DMX_DEBOUNCE_SECONDS,
    DOMAIN,
)


@pytest.fixture
def dmx_lights_entry(hass: HomeAssistant) -> MockConfigEntry:
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
                    "slug": "pool_dimmer",
                    "name": "Pool dimmer",
                    "type": "dimmer",
                    "start_channel": 1,
                },
                {
                    "slug": "pool_rgb",
                    "name": "Pool RGB",
                    "type": "rgb",
                    "start_channel": 2,
                },
                {
                    "slug": "pool_rgbw",
                    "name": "Pool RGBW",
                    "type": "rgbw",
                    "start_channel": 5,
                },
            ],
        },
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)
    return entry


async def test_dmx_light_entities_created(
    hass: HomeAssistant,
    dmx_lights_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_lights_entry.entry_id)
    await hass.async_block_till_done()
    light_entities = hass.states.async_entity_ids("light")
    assert any("pool_dimmer" in eid for eid in light_entities)
    assert any("pool_rgb" in eid for eid in light_entities)
    assert any("pool_rgbw" in eid for eid in light_entities)


async def test_dimmer_turn_on_writes_channel_value(
    hass: HomeAssistant,
    dmx_lights_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_lights_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_lights_entry.entry_id]
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")

    # Seed the shadow so entities are available and assertions are unconditional.
    coordinator._dmx_shadow = await coordinator.client.async_get_dmx()

    target = next(eid for eid in hass.states.async_entity_ids("light") if "pool_dimmer" in eid)
    await hass.services.async_call(
        "light",
        SERVICE_TURN_ON,
        {"entity_id": target, "brightness": 128},
        blocking=True,
    )
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    coordinator.client.async_set_dmx.assert_called()
    assert coordinator.dmx_shadow[0].value == 128


async def test_rgb_color_round_trip(
    hass: HomeAssistant,
    dmx_lights_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_lights_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_lights_entry.entry_id]
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")

    # Seed the shadow so entities are available and assertions are unconditional.
    coordinator._dmx_shadow = await coordinator.client.async_get_dmx()

    target = next(eid for eid in hass.states.async_entity_ids("light") if "pool_rgb" in eid)
    await hass.services.async_call(
        "light",
        SERVICE_TURN_ON,
        {"entity_id": target, "rgb_color": [200, 100, 50]},
        blocking=True,
    )
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    shadow = coordinator.dmx_shadow
    assert shadow[1].value == 200
    assert shadow[2].value == 100
    assert shadow[3].value == 50


async def test_rgb_brightness_only_preserves_hue_and_targets_max_channel(
    hass: HomeAssistant,
    dmx_lights_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    """Brightness change on an on RGB light scales so max channel == brightness.

    Regression: naive ``value * brightness / 255`` would compound-dim the colour
    on every slider adjustment because the brightest channel is rarely 255.
    """
    assert await hass.config_entries.async_setup(dmx_lights_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_lights_entry.entry_id]
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")

    # Seed the shadow so entities are available and assertions are unconditional.
    coordinator._dmx_shadow = await coordinator.client.async_get_dmx()

    target = next(eid for eid in hass.states.async_entity_ids("light") if "pool_rgb" in eid)
    # First, set a colour whose max channel is 200 (not 255).
    await hass.services.async_call(
        "light",
        SERVICE_TURN_ON,
        {"entity_id": target, "rgb_color": [200, 100, 50]},
        blocking=True,
    )
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    shadow = coordinator.dmx_shadow
    assert (shadow[1].value, shadow[2].value, shadow[3].value) == (200, 100, 50)

    # Now bump brightness only. Max channel should hit the requested level (180)
    # and the colour ratio should be preserved.
    await hass.services.async_call(
        "light",
        SERVICE_TURN_ON,
        {"entity_id": target, "brightness": 180},
        blocking=True,
    )
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    r, g, b = shadow[1].value, shadow[2].value, shadow[3].value
    assert max(r, g, b) == 180
    # Ratio preserved: original 200/100/50 → 180/90/45 (rounding tolerated).
    assert (r, g, b) == (180, 90, 45)


async def test_rgbw_turn_off(
    hass: HomeAssistant,
    dmx_lights_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
    mock_dmx_endpoint: aioresponses,
) -> None:
    assert await hass.config_entries.async_setup(dmx_lights_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][dmx_lights_entry.entry_id]
    coordinator.client.async_set_dmx = AsyncMock(return_value="OK")

    # Seed the shadow so entities are available and assertions are unconditional.
    coordinator._dmx_shadow = await coordinator.client.async_get_dmx()

    shadow = coordinator.dmx_shadow
    for i in range(4, 8):
        shadow.set(i, 200)

    target = next(eid for eid in hass.states.async_entity_ids("light") if "pool_rgbw" in eid)
    await hass.services.async_call(
        "light",
        SERVICE_TURN_OFF,
        {"entity_id": target},
        blocking=True,
    )
    await asyncio.sleep(DMX_DEBOUNCE_SECONDS + 0.1)
    for i in range(4, 8):
        assert shadow[i].value == 0
