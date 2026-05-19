"""Tests for the binary_sensor platform (controller flags)."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

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
    assert len(binary_sensors) == len(EXPECTED_FLAGS)

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
