"""Tests for the binary_sensor platform (controller flags)."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN

# Each flag corresponds to a `GetStateData.is_<flag>()` call in the
# `proconip` library and a `binary_sensor` subclass in
# `custom_components/proconip_pool_controller/binary_sensor.py` with
# `_attr_unique_id = f"is_<flag>_{instance_id}"` and translation key
# `<flag>` under `entity.binary_sensor` in translations/<lang>.json.
# Keep this list in lockstep with binary_sensor.py — the test below
# asserts every entry resolves to a real entity, so a typo here (or a
# missing class there) fails loudly instead of slipping through a
# bare length check.
EXPECTED_FLAGS = [
    "chlorine_dosage_enabled",
    "electrolysis_enabled",
    "ph_minus_dosage_enabled",
    "ph_plus_dosage_enabled",
    "tcpip_boost_enabled",
    "sd_card_enabled",
    "dmx_enabled",
    "avatar_enabled",
    "relay_extension_enabled",
    "high_bus_load_enabled",
    "flow_sensor_enabled",
    "repeated_mails_enabled",
    "dmx_extension_enabled",
]


async def test_all_flag_binary_sensors_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    binary_sensors = hass.states.async_entity_ids("binary_sensor")
    # The config flags plus the single Problem binary_sensor.
    assert len(binary_sensors) == len(EXPECTED_FLAGS) + 1

    # Resolve each expected flag to a real entity via its unique_id —
    # that catches both missing-class regressions and typo-in-EXPECTED_FLAGS
    # bugs that a bare length check would miss.
    registry = er.async_get(hass)
    instance_id = setup_integration.entry_id
    found_uids = {entry.unique_id for entry in registry.entities.values()}
    missing = [
        f"is_{flag}_{instance_id}"
        for flag in EXPECTED_FLAGS
        if f"is_{flag}_{instance_id}" not in found_uids
    ]
    assert not missing, f"binary_sensor entries missing for flags: {missing}"


async def test_problem_binary_sensor_trips_at_threshold(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """Problem sensor is on for fixture SYSINFO[4]=3 (yellow) at the default threshold."""
    registry = er.async_get(hass)
    instance_id = setup_integration.entry_id
    eid = registry.async_get_entity_id("binary_sensor", DOMAIN, f"problem_{instance_id}")
    assert eid, "problem binary_sensor not registered"

    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes.get("device_class") == "problem"
    # Fixture fault state is 3 (green+yellow); highest severity = yellow, which
    # meets the default "yellow" threshold → problem reported.
    assert state.state == "on"


async def test_ntp_only_fault_does_not_trip_problem(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint_ntp_fault: aioresponses,
) -> None:
    """A pure NTP fault (no lamp bit) is surfaced by the sensor but not as a Problem.

    Characterises the deliberate scoping: the Problem sensor tracks only the
    green/yellow/red lamps, so an NTP-only fault (SYSINFO[4] = 65536) stays off
    while the diagnostic sensor reports it via `ntp_synced`.
    """
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    instance_id = config_entry.entry_id
    problem_eid = registry.async_get_entity_id("binary_sensor", DOMAIN, f"problem_{instance_id}")
    fault_eid = registry.async_get_entity_id("sensor", DOMAIN, f"fault_state_{instance_id}")
    assert problem_eid and fault_eid

    fault = hass.states.get(fault_eid)
    assert fault.attributes["raw"] == 65536
    assert fault.attributes["ntp_synced"] is False
    assert fault.attributes["green"] is False
    assert fault.attributes["yellow"] is False
    assert fault.attributes["red"] is False

    # No lamp severity → Problem stays off even though the controller flags NTP.
    assert hass.states.get(problem_eid).state == "off"
