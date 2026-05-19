"""Tests for the number platform (dosage timer)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN
from custom_components.proconip_pool_controller.coordinator import (
    ProconipPoolControllerDataUpdateCoordinator,
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
