"""Tests for the number platform (dosage timer)."""

from __future__ import annotations

import re
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN
from custom_components.proconip_pool_controller.coordinator import (
    ProconipPoolControllerDataUpdateCoordinator,
)
from custom_components.proconip_pool_controller.number import (
    ProconipPoolControllerDosageRelayTimer,
)


async def test_dosage_timer_created_only_for_active_dosage_relays(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    timer_entities = [
        eid
        for eid in hass.states.async_entity_ids("number")
        if "relay_no_" in eid and "dosage" in eid
    ]
    expected = sum(1 for is_active in coordinator._active_dosage_relays.values() if is_active)
    assert len(timer_entities) == expected


def _timer_state(hass: HomeAssistant, entry: MockConfigEntry, relay_no: int) -> Any:
    registry = er.async_get(hass)
    eid = registry.async_get_entity_id(
        "number", DOMAIN, f"relay_dosage_{relay_no}_{entry.entry_id}"
    )
    assert eid, f"dosage timer for relay {relay_no} not registered"
    state = hass.states.get(eid)
    assert state is not None
    return state


def _man_dosage_queries(mock: aioresponses) -> list[str]:
    return [
        url.query_string
        for (method, url), _calls in mock.requests.items()
        if method == "GET" and url.path == "/Command.htm"
    ]


async def test_liquid_dosage_timers_mirror_vendor_mmss_limits(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Liquid channels take 0..59:59 (mm:ss) like the vendor GUI: 0..3599 s, 1 s steps."""
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        setup_integration.entry_id
    ]
    assert not coordinator.data.is_electrolysis_enabled()
    state = _timer_state(hass, setup_integration, coordinator.data.chlorine_dosage_relay_id + 1)
    assert state.attributes["min"] == 0
    assert state.attributes["max"] == 3599
    assert state.attributes["step"] == 1


async def test_liquid_dosage_sends_seconds_up_to_3599(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    mock_state_endpoint.get(re.compile(r".*/Command\.htm.*"), status=200, body="", repeat=True)
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        setup_integration.entry_id
    ]
    state = _timer_state(hass, setup_integration, coordinator.data.chlorine_dosage_relay_id + 1)
    with patch.object(ProconipPoolControllerDosageRelayTimer, "countdown", new=AsyncMock()):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": state.entity_id, "value": 3599},
            blocking=True,
        )
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": state.entity_id, "value": 3600},
                blocking=True,
            )
    assert _man_dosage_queries(mock_state_endpoint) == ["MAN_DOSAGE=0,3599"]


async def test_electrolysis_dosage_timer_mirrors_vendor_hhmm_limits(
    hass: HomeAssistant,
    setup_integration_electrolysis: MockConfigEntry,
) -> None:
    """Chlorine with an electrolysis cell takes 00:00..23:59 (hh:mm): 0..86340 s in minutes."""
    entry = setup_integration_electrolysis
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.data.is_electrolysis_enabled()
    chlorine = _timer_state(hass, entry, coordinator.data.chlorine_dosage_relay_id + 1)
    assert chlorine.attributes["min"] == 0
    assert chlorine.attributes["max"] == 86340
    assert chlorine.attributes["step"] == 60


async def test_electrolysis_dosage_sends_seconds_in_whole_minutes(
    hass: HomeAssistant,
    setup_integration_electrolysis: MockConfigEntry,
    mock_state_endpoint_electrolysis: aioresponses,
) -> None:
    mock = mock_state_endpoint_electrolysis
    mock.get(re.compile(r".*/Command\.htm.*"), status=200, body="", repeat=True)
    entry = setup_integration_electrolysis
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    state = _timer_state(hass, entry, coordinator.data.chlorine_dosage_relay_id + 1)
    with patch.object(ProconipPoolControllerDosageRelayTimer, "countdown", new=AsyncMock()):
        # 23:59 is the vendor GUI's maximum.
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": state.entity_id, "value": 86340},
            blocking=True,
        )
        # Not expressible as hh:mm -> rejected before anything is sent.
        with pytest.raises(ServiceValidationError) as excinfo:
            await hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": state.entity_id, "value": 90},
                blocking=True,
            )
    assert excinfo.value.translation_domain == DOMAIN
    assert excinfo.value.translation_key == "electrolysis_whole_minutes"
    assert excinfo.value.translation_placeholders == {"seconds": "90"}
    assert "whole minutes" in str(excinfo.value)
    assert "90 seconds" in str(excinfo.value)
    assert _man_dosage_queries(mock) == ["MAN_DOSAGE=0,86340"]


async def test_shared_relay_routes_to_first_enabled_channel(
    hass: HomeAssistant,
    setup_integration_shared_relay_electrolysis: MockConfigEntry,
    mock_state_endpoint_shared_relay_electrolysis: aioresponses,
) -> None:
    """Disabled electrolysis chlorine on the pH- relay must not hijack the pH- timer.

    The vendor GUI routes a relay to the first *enabled* channel (Cl, pH-,
    pH+). Chlorine is disabled here, so relay 4 is pH-: mm:ss limits and
    ``MAN_DOSAGE=1,…`` — not the hh:mm limits or target 0 of electrolysis.
    """
    mock = mock_state_endpoint_shared_relay_electrolysis
    mock.get(re.compile(r".*/Command\.htm.*"), status=200, body="", repeat=True)
    entry = setup_integration_shared_relay_electrolysis
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    assert data.is_electrolysis_enabled()
    assert not data.is_chlorine_dosage_enabled()
    assert data.chlorine_dosage_relay_id == data.ph_minus_dosage_relay_id == 4

    state = _timer_state(hass, entry, 5)
    assert state.attributes["max"] == 3599
    assert state.attributes["step"] == 1
    with patch.object(ProconipPoolControllerDosageRelayTimer, "countdown", new=AsyncMock()):
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": state.entity_id, "value": 90},
            blocking=True,
        )
    assert _man_dosage_queries(mock) == ["MAN_DOSAGE=1,90"]


def _timer_entity(hass: HomeAssistant, entity_id: str) -> ProconipPoolControllerDosageRelayTimer:
    entity = hass.data["number"].get_entity(entity_id)
    assert isinstance(entity, ProconipPoolControllerDosageRelayTimer)
    return entity


async def test_new_value_replaces_running_countdown(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """A second value cancels the first countdown instead of running two loops."""
    mock_state_endpoint.get(re.compile(r".*/Command\.htm.*"), status=200, body="", repeat=True)
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        setup_integration.entry_id
    ]
    state = _timer_state(hass, setup_integration, coordinator.data.chlorine_dosage_relay_id + 1)
    entity = _timer_entity(hass, state.entity_id)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": state.entity_id, "value": 120}, blocking=True
    )
    first = entity._countdown_task
    assert first is not None
    assert not first.done()

    await hass.services.async_call(
        "number", "set_value", {"entity_id": state.entity_id, "value": 60}, blocking=True
    )
    await hass.async_block_till_done(wait_background_tasks=False)
    second = entity._countdown_task
    assert second is not None
    assert second is not first
    assert first.cancelled()
    assert not second.done()
    assert entity.native_value is not None
    assert 0 < entity.native_value <= 60


async def test_countdown_cancelled_when_entry_unloads(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Unloading (e.g. the mode-flip reload) must not leave a countdown running."""
    mock_state_endpoint.get(re.compile(r".*/Command\.htm.*"), status=200, body="", repeat=True)
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        setup_integration.entry_id
    ]
    state = _timer_state(hass, setup_integration, coordinator.data.chlorine_dosage_relay_id + 1)
    entity = _timer_entity(hass, state.entity_id)

    await hass.services.async_call(
        "number", "set_value", {"entity_id": state.entity_id, "value": 3599}, blocking=True
    )
    task = entity._countdown_task
    assert task is not None
    assert not task.done()

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()
    assert task.cancelled()
    assert entity._countdown_task is None
