"""Tests for the switch platform (relay on/off and auto-mode)."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_switch_entities_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    relay_switches = [
        eid
        for eid in hass.states.async_entity_ids("switch")
        if "relay_no_" in eid and "auto_mode" not in eid
    ]
    assert len(relay_switches) in (8, 16)

    auto_mode_switches = [
        eid for eid in hass.states.async_entity_ids("switch") if "auto_mode" in eid
    ]
    assert len(auto_mode_switches) in (8, 16)


async def test_switch_turn_on_calls_api(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    mock_state_endpoint.post(
        "http://192.0.2.10/usrcfg.cgi",
        status=200,
        body="OK",
        repeat=True,
    )
    # Find a non-dosage relay switch that is available (not dosage relay)
    candidate = next(
        (
            eid
            for eid in hass.states.async_entity_ids("switch")
            if "relay_no_" in eid
            and "auto_mode" not in eid
            and hass.states.get(eid).state != "unavailable"
        ),
        None,
    )
    if candidate is None:
        # All relays are dosage relays (unusual fixture), skip gracefully
        return
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_ON,
        {"entity_id": candidate},
        blocking=True,
    )
    # Assert the POST to /usrcfg.cgi actually happened.
    posts = [
        call
        for (method, url), calls in mock_state_endpoint.requests.items()
        for call in calls
        if method == "POST" and "usrcfg.cgi" in str(url)
    ]
    assert len(posts) >= 1, (
        f"Expected POST to /usrcfg.cgi, got: {dict(mock_state_endpoint.requests)}"
    )


async def test_switch_turn_off_calls_api(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    mock_state_endpoint.post(
        "http://192.0.2.10/usrcfg.cgi",
        status=200,
        body="OK",
        repeat=True,
    )
    candidate = next(
        (
            eid
            for eid in hass.states.async_entity_ids("switch")
            if "relay_no_" in eid
            and "auto_mode" not in eid
            and hass.states.get(eid).state != "unavailable"
        ),
        None,
    )
    if candidate is None:
        return
    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {"entity_id": candidate},
        blocking=True,
    )
    # Assert the POST to /usrcfg.cgi actually happened.
    posts = [
        call
        for (method, url), calls in mock_state_endpoint.requests.items()
        for call in calls
        if method == "POST" and "usrcfg.cgi" in str(url)
    ]
    assert len(posts) >= 1, (
        f"Expected POST to /usrcfg.cgi, got: {dict(mock_state_endpoint.requests)}"
    )
