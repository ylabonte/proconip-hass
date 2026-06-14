"""Regression guard: entity friendly_names follow `hass.config.language`.

If a translation key is removed, renamed, or its placeholder template
drifts, this test fails for the affected language. Covers both code
paths through HA's name resolver:

- A static `_attr_translation_key` with no placeholders (binary_sensor
  → ``chlorine_dosage_enabled``).
- A `_attr_translation_key` plus `_attr_translation_placeholders` that
  fill `{relay_no}` / `{device_name}` (sensor → ``relay_state``).

If you add a new language file under `translations/`, parametrize it
in here too.
"""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN

# Device-name prefix that HA composes onto every entity's friendly_name
# when `_attr_has_entity_name = True` is set on the base entity. Matches
# `NAME` from the integration's `const.py`.
DEVICE_PREFIX = "ProCon.IP Pool Controller"


@pytest.mark.parametrize(
    "language,expected_chlorine,expected_relay_state_1",
    [
        (
            "en",
            f"{DEVICE_PREFIX} Chlorine Dosage enabled",
            f"{DEVICE_PREFIX} Relay No. 1 (Terassenlicht) State",
        ),
        (
            "de",
            f"{DEVICE_PREFIX} Chlor-Dosierung aktiviert",
            f"{DEVICE_PREFIX} Relais Nr. 1 (Terassenlicht) Zustand",
        ),
    ],
)
async def test_entity_friendly_names_follow_language(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    language: str,
    expected_chlorine: str,
    expected_relay_state_1: str,
) -> None:
    """For each (language, entity) pair the resolved friendly_name must match."""
    hass.config.language = language
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    chlorine_eid = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"is_chlorine_dosage_enabled_{config_entry.entry_id}"
    )
    relay_state_1_eid = registry.async_get_entity_id(
        "sensor", DOMAIN, f"relay_state_1_{config_entry.entry_id}"
    )
    assert chlorine_eid and relay_state_1_eid, "expected entities not registered"

    chlorine_state = hass.states.get(chlorine_eid)
    relay_state_1 = hass.states.get(relay_state_1_eid)
    assert chlorine_state and relay_state_1

    assert chlorine_state.attributes["friendly_name"] == expected_chlorine, (
        f"[{language}] chlorine: got "
        f"{chlorine_state.attributes['friendly_name']!r}, expected "
        f"{expected_chlorine!r}"
    )
    assert relay_state_1.attributes["friendly_name"] == expected_relay_state_1, (
        f"[{language}] relay_state_1: got "
        f"{relay_state_1.attributes['friendly_name']!r}, expected "
        f"{expected_relay_state_1!r}"
    )


@pytest.mark.parametrize(
    "language,expected_names",
    [
        (
            "en",
            {
                ("sensor", "fault_state"): f"{DEVICE_PREFIX} Fault state",
                ("binary_sensor", "problem"): f"{DEVICE_PREFIX} Problem",
                (
                    "select",
                    "problem_severity_threshold",
                ): f"{DEVICE_PREFIX} Problem severity threshold",
            },
        ),
        (
            "de",
            {
                ("sensor", "fault_state"): f"{DEVICE_PREFIX} Fehlerzustand",
                ("binary_sensor", "problem"): f"{DEVICE_PREFIX} Problem",
                (
                    "select",
                    "problem_severity_threshold",
                ): f"{DEVICE_PREFIX} Schwelle für Problemmeldung",
            },
        ),
    ],
)
async def test_fault_state_entity_friendly_names_follow_language(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    language: str,
    expected_names: dict[tuple[str, str], str],
) -> None:
    """The new fault-state entities resolve translated friendly names per language."""
    hass.config.language = language
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    instance_id = config_entry.entry_id
    for (platform, key), expected in expected_names.items():
        eid = registry.async_get_entity_id(platform, DOMAIN, f"{key}_{instance_id}")
        assert eid, f"[{language}] {platform}/{key} not registered"
        state = hass.states.get(eid)
        assert state is not None
        assert state.attributes["friendly_name"] == expected, (
            f"[{language}] {platform}/{key}: got "
            f"{state.attributes['friendly_name']!r}, expected {expected!r}"
        )
