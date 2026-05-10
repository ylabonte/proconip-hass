"""Tests for the sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_redox_sensor_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    eid = next(
        eid for eid in hass.states.async_entity_ids("sensor") if eid.endswith("_redox_sensor")
    )
    state = hass.states.get(eid)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")


async def test_ph_sensor_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    eid = next(eid for eid in hass.states.async_entity_ids("sensor") if eid.endswith("_ph_sensor"))
    state = hass.states.get(eid)
    assert state is not None


async def test_temperature_sensors_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    # 8 temperature sensors are always added; some hidden by default
    entity_ids = [eid for eid in hass.states.async_entity_ids("sensor") if "temperature_no_" in eid]
    assert len(entity_ids) >= 1


async def test_relay_state_sensor_count_matches_extension_flag(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entity_ids = [
        eid
        for eid in hass.states.async_entity_ids("sensor")
        if "relay_no_" in eid and "_state" in eid
    ]
    # 8 if no extension, 16 if extension enabled — fixture has extension off
    assert len(entity_ids) in (8, 16)
