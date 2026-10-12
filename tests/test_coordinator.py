"""Tests for the data update coordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from aioresponses import CallbackResult, aioresponses
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN
from custom_components.proconip_pool_controller.coordinator import (
    ProconipPoolControllerDataUpdateCoordinator,
)

from .conftest import BASE_URL


async def test_first_refresh_success(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.data is not None
    assert coordinator.last_update_success is True


async def test_auth_failure_marks_entry_for_reauth(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
) -> None:
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=401,
        body="Unauthorized",
        repeat=True,
    )
    # The integration does not implement async_step_reauth yet (added in Task 9).
    # Patch async_start_reauth on the config entry class to prevent HA from
    # attempting a reauth flow that would raise UnknownStep during teardown.
    with patch(
        "homeassistant.config_entries.ConfigEntry.async_start_reauth",
        return_value=None,
    ):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_initial_update_failure_triggers_setup_retry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
) -> None:
    """A 5xx on the first poll must put the entry in SETUP_RETRY, not LOADED.

    The old name was misleading: it suggested the integration stayed loaded
    after the failure, but `async_setup` actually returns False and HA
    marks the entry for retry — which is what we want (HA will re-attempt
    setup on its own backoff schedule).
    """
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=500,
        body="Server Error",
        repeat=True,
    )
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_dosage_relay_tracking(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    chlorine_id = coordinator.data.chlorine_dosage_relay_id
    assert coordinator.is_active_dosage_relay(relay_id=chlorine_id) is (
        coordinator.data.is_chlorine_dosage_enabled()
    )
    # A relay ID that is not a dosage relay should always return False.
    assert coordinator.is_active_dosage_relay(relay_id=999) is False


async def test_chlorine_supply_change_reloads_and_relabels(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
    get_state_csv: str,
    get_state_electrolysis_csv: str,
) -> None:
    """Switching liquid -> electrolysis between polls reloads the entry.

    The chlorine canister sensor picks its label at setup, so without the
    reload it would keep saying "Canister" next to a live
    "Electrolysis enabled: on".
    """
    served = {"body": get_state_csv}

    def _state(url: Any, **kwargs: Any) -> CallbackResult:
        return CallbackResult(status=200, body=served["body"])

    aio_mock.get(f"{BASE_URL}/GetState.csv", callback=_state, repeat=True)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    eid = registry.async_get_entity_id("sensor", DOMAIN, f"canister_1_{config_entry.entry_id}")
    assert eid
    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes["friendly_name"].endswith("Canister Cl Rest")

    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]
    with patch.object(
        hass.config_entries,
        "async_schedule_reload",
        wraps=hass.config_entries.async_schedule_reload,
    ) as schedule_reload:
        # Same mode again: no reload.
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        schedule_reload.assert_not_called()

        served["body"] = get_state_electrolysis_csv
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        schedule_reload.assert_called_once_with(config_entry.entry_id)

    assert config_entry.state is ConfigEntryState.LOADED
    # Same unique_id -> same entity_id, now with the cell label.
    assert (
        registry.async_get_entity_id("sensor", DOMAIN, f"canister_1_{config_entry.entry_id}") == eid
    )
    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes["friendly_name"].endswith("Electrolysis cell remaining lifetime")


async def test_shared_dosage_relay_stays_active_when_a_disabled_channel_points_at_it(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The README-recommended setup: pH+ disabled, pointed at the pH- relay.

    Fixture SYSINFO ``…,257,4,4,5``: pH+ -> relay 4, pH- -> relay 4, Cl -> relay
    5; DOSAGE_CNTRL 257 = Cl + pH- enabled, pH+ disabled. Relay 4 must count as
    an active dosage relay (pH- is on), not be overwritten by the disabled pH+.
    """
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    assert data.ph_minus_dosage_relay_id == data.ph_plus_dosage_relay_id == 4
    assert data.is_ph_minus_dosage_enabled()
    assert not data.is_ph_plus_dosage_enabled()
    assert coordinator.is_active_dosage_relay(relay_id=4) is True
    assert coordinator.is_active_dosage_relay(relay_id=5) is True

    registry = er.async_get(hass)
    instance_id = entry.entry_id
    # pH- relay (relay_no 5) now gets a dosage timer …
    assert registry.async_get_entity_id("number", DOMAIN, f"relay_dosage_5_{instance_id}")
    # … and no "on" option in its mode select.
    select_eid = registry.async_get_entity_id("select", DOMAIN, f"relay_select_5_{instance_id}")
    assert select_eid
    select_state = hass.states.get(select_eid)
    assert select_state is not None
    assert select_state.attributes["options"] == ["auto", "off"]


def _with_sysinfo(csv: str, *, dosage_control: int, cl: int, ph_minus: int, ph_plus: int) -> str:
    """Return ``csv`` with SYSINFO[6..9] (DOSAGE_CNTRL + dosage relay ids) replaced."""
    lines = csv.split("\n")
    sysinfo = lines[0].split(",")
    sysinfo[6:10] = [str(dosage_control), str(ph_plus), str(ph_minus), str(cl)]
    lines[0] = ",".join(sysinfo)
    return "\n".join(lines)


@pytest.mark.parametrize(
    ("change", "expect_reload"),
    [
        # Fixture: DOSAGE_CNTRL 257 (Cl + pH-), pH+ -> 4, pH- -> 4, Cl -> 5.
        ({"dosage_control": 257, "cl": 5, "ph_minus": 4, "ph_plus": 4}, False),
        ({"dosage_control": 1, "cl": 5, "ph_minus": 4, "ph_plus": 4}, True),  # pH- off
        ({"dosage_control": 4353, "cl": 5, "ph_minus": 4, "ph_plus": 4}, True),  # pH+ on
        ({"dosage_control": 257, "cl": 6, "ph_minus": 4, "ph_plus": 4}, True),  # Cl relay
        ({"dosage_control": 257, "cl": 5, "ph_minus": 3, "ph_plus": 4}, True),  # pH- relay
        ({"dosage_control": 259, "cl": 5, "ph_minus": 4, "ph_plus": 4}, False),  # reserved bit 1
    ],
    ids=[
        "unchanged",
        "ph_minus_disabled",
        "ph_plus_enabled",
        "cl_relay_moved",
        "ph_minus_moved",
        "reserved_bit_ignored",
    ],
)
async def test_dosing_config_change_reloads_entry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
    get_state_csv: str,
    change: dict[str, int],
    expect_reload: bool,
) -> None:
    """Any change to DOSAGE_CNTRL or a dosage relay id schedules exactly one reload."""
    served = {"body": get_state_csv}

    def _state(url: Any, **kwargs: Any) -> CallbackResult:
        return CallbackResult(status=200, body=served["body"])

    aio_mock.get(f"{BASE_URL}/GetState.csv", callback=_state, repeat=True)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    with patch.object(hass.config_entries, "async_schedule_reload") as schedule_reload:
        served["body"] = _with_sysinfo(get_state_csv, **change)
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        # A second poll with the same config must not reload again.
        await coordinator.async_refresh()
        await hass.async_block_till_done()

    if expect_reload:
        schedule_reload.assert_called_once_with(config_entry.entry_id)
    else:
        schedule_reload.assert_not_called()
