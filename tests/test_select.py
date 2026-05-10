"""Tests for the select platform (relay auto/on/off dropdown)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_select_entities_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    selects = [eid for eid in hass.states.async_entity_ids("select") if "relay_no_" in eid]
    assert len(selects) in (8, 16)


async def test_select_options_are_valid(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    for eid in hass.states.async_entity_ids("select"):
        state = hass.states.get(eid)
        options = state.attributes.get("options", [])
        # Either ["auto","on","off"] for normal relays or ["auto","off"] for
        # active dosage relays.
        assert set(options).issubset({"auto", "on", "off"})
        assert "auto" in options
        assert "off" in options
