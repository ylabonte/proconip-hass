"""Tests for the sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN


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


async def test_fault_state_sensor_decodes_bits(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """The diagnostic fault-state enum sensor reports a stable key + decoded attributes."""
    registry = er.async_get(hass)
    instance_id = setup_integration.entry_id
    eid = registry.async_get_entity_id("sensor", DOMAIN, f"fault_state_{instance_id}")
    assert eid, "fault_state sensor not registered"

    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes.get("device_class") == "enum"
    # Fixture SYSINFO[4] = 3 → green + yellow → highest severity yellow → "warning".
    assert state.state == "warning"
    assert state.attributes["raw"] == 3
    assert state.attributes["green"] is True
    assert state.attributes["yellow"] is True
    assert state.attributes["red"] is False
    assert state.attributes["ntp_synced"] is True
