"""Tests for the select platform (relay auto/on/off dropdown)."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.proconip_pool_controller.const import DOMAIN


def _relay_select_entity_ids(hass: HomeAssistant) -> list[str]:
    """Relay-select entity ids resolved via unique_id (language-proof).

    Filtering on the ``relay_no_`` entity_id slug only works under English; the
    relay select's unique_id (``relay_select_<n>_<instance>``) is stable across
    languages and excludes the problem-severity-threshold select.
    """
    registry = er.async_get(hass)
    return [
        entry.entity_id
        for entry in registry.entities.values()
        if entry.platform == DOMAIN
        and entry.domain == "select"
        and "relay_select_" in entry.unique_id
    ]


async def test_select_entities_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    assert len(_relay_select_entity_ids(hass)) in (8, 16)


async def test_select_options_are_valid(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    for eid in _relay_select_entity_ids(hass):
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


async def test_restored_threshold_updates_binary_sensor_at_startup(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """A restored non-default threshold is reflected by the Problem sensor immediately.

    Regression: the coordinator's first refresh fires before any entity exists, so
    restoring the threshold in the select's `async_added_to_hass` must notify
    listeners — otherwise `binary_sensor.problem` keeps the state it computed from
    the default threshold until the next poll.
    """
    # First setup to learn the registry-assigned entity ids.
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    instance_id = config_entry.entry_id
    select_eid = registry.async_get_entity_id(
        "select", DOMAIN, f"problem_severity_threshold_{instance_id}"
    )
    problem_eid = registry.async_get_entity_id("binary_sensor", DOMAIN, f"problem_{instance_id}")
    assert select_eid and problem_eid

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Simulate a previous session that had raised the threshold to "red".
    mock_restore_cache(hass, (State(select_eid, "red"),))

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Fixture severity is yellow; the restored "red" threshold is stricter, so the
    # Problem sensor must read "off" right away — no poll has run since setup.
    assert hass.states.get(select_eid).state == "red"
    assert hass.states.get(problem_eid).state == "off"
