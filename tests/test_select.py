"""Tests for the select platform (relay auto/on/off dropdown)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN


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
        if "relay_no_" not in eid:
            continue  # skip the problem-severity-threshold select
        state = hass.states.get(eid)
        options = state.attributes.get("options", [])
        # Either ["auto","on","off"] for normal relays or ["auto","off"] for
        # active dosage relays.
        assert set(options).issubset({"auto", "on", "off"})
        assert "auto" in options
        assert "off" in options


async def test_problem_severity_threshold_select(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The threshold select drives whether the Problem binary_sensor trips."""
    registry = er.async_get(hass)
    instance_id = setup_integration.entry_id
    select_eid = registry.async_get_entity_id(
        "select", DOMAIN, f"problem_severity_threshold_{instance_id}"
    )
    problem_eid = registry.async_get_entity_id("binary_sensor", DOMAIN, f"problem_{instance_id}")
    assert select_eid and problem_eid

    select_state = hass.states.get(select_eid)
    assert select_state.attributes.get("options") == ["green", "yellow", "red"]
    assert select_state.state == "yellow"  # default threshold
    # Fixture severity is yellow → problem on at the default threshold.
    assert hass.states.get(problem_eid).state == "on"

    # Raise the threshold above the active severity → problem clears.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": select_eid, "option": "red"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(select_eid).state == "red"
    assert hass.states.get(problem_eid).state == "off"

    # Lower it to the most sensitive level → problem trips again.
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": select_eid, "option": "green"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(problem_eid).state == "on"
