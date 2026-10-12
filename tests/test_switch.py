"""Tests for the switch platform (relay on/off and auto-mode)."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN

from .conftest import BASE_URL


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
        # All relays are dosage relays (unusual fixture) — no plain relay
        # switch to exercise. Skip so the test report shows the omission
        # explicitly instead of silently passing.
        pytest.skip("Fixture exposes no plain (non-dosage) relay switch to toggle")
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
        pytest.skip("Fixture exposes no plain (non-dosage) relay switch to toggle")
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


async def test_active_dosage_relay_switch_refuses_turn_on_only(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """An active dosage relay's switch stays available, can be switched off, never on.

    Fixture: DOSAGE_CNTRL 257 (chlorine + pH- on), chlorine on relay id 5 and
    pH- on relay id 4 (0-based), so relays no. 6 and 5 are active dosage
    relays and relay no. 1 is a plain relay.
    """
    mock_state_endpoint.post(
        "http://192.0.2.10/usrcfg.cgi",
        status=200,
        body="OK",
        repeat=True,
    )
    registry = er.async_get(hass)

    def entity_id_of(relay_no: int) -> str:
        entity_id = registry.async_get_entity_id(
            "switch", DOMAIN, f"relay_{relay_no}_{setup_integration.entry_id}"
        )
        assert entity_id is not None
        return entity_id

    def usrcfg_posts() -> int:
        return sum(
            len(calls)
            for (method, url), calls in mock_state_endpoint.requests.items()
            if method == "POST" and "usrcfg.cgi" in str(url)
        )

    for relay_no in (6, 5, 1):
        state = hass.states.get(entity_id_of(relay_no))
        assert state is not None
        assert state.state != STATE_UNAVAILABLE

    for relay_no in (6, 5):
        with pytest.raises(ServiceValidationError) as excinfo:
            await hass.services.async_call(
                "switch",
                SERVICE_TURN_ON,
                {"entity_id": entity_id_of(relay_no)},
                blocking=True,
            )
        assert excinfo.value.translation_key == "dosage_relay_permanent_on"
        assert excinfo.value.translation_placeholders == {"relay_no": str(relay_no)}
        assert f"Relay {relay_no} is used for dosing" in str(excinfo.value)
    assert usrcfg_posts() == 0, "turn_on of a dosage relay must not reach the controller"

    await hass.services.async_call(
        "switch",
        SERVICE_TURN_OFF,
        {"entity_id": entity_id_of(6)},
        blocking=True,
    )
    assert usrcfg_posts() == 1


async def test_relay_of_disabled_dosage_channel_refuses_turn_on_with_hint(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
    get_state_csv: str,
) -> None:
    """A relay only a *disabled* dosage channel points at gets a translated hint.

    The README's "or some unused relay" variant: pH+ disabled (DOSAGE_CNTRL
    257 = Cl + pH- only) but pointed at relay id 0 (relay no. 1). The relay is
    not an active dosage relay, so the switch lets the call through, and the
    library refuses it (BadRelayException ignores the enable flags). That must
    surface as a translated ServiceValidationError, with nothing sent.
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
    entity_id = registry.async_get_entity_id("switch", DOMAIN, f"relay_1_{config_entry.entry_id}")
    assert entity_id is not None
    before = hass.states.get(entity_id)
    assert before is not None
    assert before.state != STATE_UNAVAILABLE

    with pytest.raises(ServiceValidationError) as excinfo:
        await hass.services.async_call(
            "switch", SERVICE_TURN_ON, {"entity_id": entity_id}, blocking=True
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
