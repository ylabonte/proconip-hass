"""Tests for the select platform (relay auto/on/off dropdown)."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.proconip_pool_controller.const import DOMAIN

from .conftest import BASE_URL


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


async def test_relay_of_disabled_dosage_channel_refuses_on_with_hint(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
    get_state_csv: str,
) -> None:
    """Selecting "on" for a relay only a *disabled* dosage channel uses gets a hint.

    Same setup as the switch test: pH+ disabled (DOSAGE_CNTRL 257) but pointed
    at relay id 0 (relay no. 1). The select still offers "on" (the relay isn't
    an active dosage relay), the library refuses it, and the user must see the
    translated ServiceValidationError the switch raises, with nothing sent.
    """
    lines = get_state_csv.split("\n")
    sysinfo = lines[0].split(",")
    sysinfo[7] = "0"  # pH+ dosage relay id -> relay no. 1
    lines[0] = ",".join(sysinfo)
    aio_mock.get(f"{BASE_URL}/GetState.csv", status=200, body="\n".join(lines), repeat=True)
    aio_mock.post(f"{BASE_URL}/usrcfg.cgi", status=200, body="OK", repeat=True)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"relay_select_1_{config_entry.entry_id}"
    )
    assert entity_id is not None
    before = hass.states.get(entity_id)
    assert before is not None
    assert "on" in before.attributes["options"]

    with pytest.raises(ServiceValidationError) as excinfo:
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": entity_id, "option": "on"},
            blocking=True,
        )
    assert excinfo.value.translation_key == "relay_reserved_for_dosage"
    assert excinfo.value.translation_placeholders == {"relay_no": "1"}
    assert "disabled dosage channel" in str(excinfo.value)
    assert not any(
        method == "POST" and "usrcfg.cgi" in str(url) for (method, url) in aio_mock.requests
    )
    after = hass.states.get(entity_id)
    assert after is not None
    assert after.state == before.state
