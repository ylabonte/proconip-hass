"""Tests for the binary_sensor platform (controller flags)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

EXPECTED_FLAGS = [
    "chlorine_dosage_enabled",
    "electrolysis_enabled",
    "ph_minus_dosage_enabled",
    "ph_plus_dosage_enabled",
    "tcp_ip_boost_enabled",
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
    assert len(binary_sensors) == len(EXPECTED_FLAGS)
