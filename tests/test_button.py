"""Tests for the button platform (digital input triggers)."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN

from .conftest import BASE_URL

USRCFG_URL = f"{BASE_URL}/usrcfg.cgi"
GET_STATE_URL = f"{BASE_URL}/GetState.csv"

# Device-name prefix HA composes onto every friendly_name (NAME in const.py),
# because the base entity sets `_attr_has_entity_name = True`.
DEVICE_PREFIX = "ProCon.IP Pool Controller"


def _usrcfg_posts(m: aioresponses) -> list:
    return [
        call
        for (method, url), calls in m.requests.items()
        for call in calls
        if method == "POST" and "usrcfg.cgi" in str(url)
    ]


def _state_gets(m: aioresponses) -> int:
    return sum(
        len(calls)
        for (method, url), calls in m.requests.items()
        if method == "GET" and "GetState.csv" in str(url)
    )


async def test_button_entities_created(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    """One trigger button per digital input (4), with instance-suffixed ids."""
    entry = setup_integration
    registry = er.async_get(hass)
    for n in range(1, 5):
        eid = registry.async_get_entity_id(
            "button", DOMAIN, f"digital_input_trigger_{n}_{entry.entry_id}"
        )
        assert eid, f"digital input trigger button {n} not registered"
    # Fixture names all four inputs (TASTER1..4), so all four are visible.
    assert len(hass.states.async_entity_ids("button")) == 4


async def test_button_press_triggers_and_refreshes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Pressing sends the press+release POSTs and refreshes the coordinator."""
    mock_state_endpoint.post(USRCFG_URL, status=200, body="OK", repeat=True)
    entry = setup_integration
    eid = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"digital_input_trigger_1_{entry.entry_id}"
    )
    assert eid

    gets_before = _state_gets(mock_state_endpoint)
    await hass.services.async_call("button", "press", {"entity_id": eid}, blocking=True)

    posts = _usrcfg_posts(mock_state_endpoint)
    # Button 1 -> digital_input_id 0 -> mask 1; press then release.
    assert [p.kwargs["data"] for p in posts] == ["IO=1&WEBIO=1", "IO=0&WEBIO=1"]
    # A coordinator refresh (extra GetState.csv) followed the press.
    assert _state_gets(mock_state_endpoint) > gets_before


@pytest.mark.parametrize(
    "language,expected",
    [
        ("en", f"{DEVICE_PREFIX} Trigger Digital Input No. 1: TASTER1"),
        ("de", f"{DEVICE_PREFIX} Digitalen Eingang Nr. 1 auslösen: TASTER1"),
    ],
)
async def test_button_friendly_name_follows_language(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
    language: str,
    expected: str,
) -> None:
    """The trigger button resolves a translated friendly name per language."""
    hass.config.language = language
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    eid = er.async_get(hass).async_get_entity_id(
        "button", DOMAIN, f"digital_input_trigger_1_{config_entry.entry_id}"
    )
    assert eid
    state = hass.states.get(eid)
    assert state is not None
    assert state.attributes["friendly_name"] == expected
