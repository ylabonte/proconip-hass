"""Tests for the config flow and options flow."""

from __future__ import annotations

import pytest
from aioresponses import aioresponses
from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.config_flow import (
    ProconipPoolControllerOptionsFlowHandler,
)
from custom_components.proconip_pool_controller.const import CONF_DMX_LIGHTS, DOMAIN

USER_INPUT = {
    CONF_NAME: "Test Pool",
    CONF_URL: "http://192.0.2.10",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "admin",
    CONF_SCAN_INTERVAL: 30,
}


async def test_user_flow_happy_path(
    hass: HomeAssistant,
    mock_state_endpoint_dmx_on: aioresponses,
) -> None:
    """Credentials (DMX-on controller) → setup_menu → setup_finish → CREATE_ENTRY."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    # Controller reports DMX enabled → flow lands on the optional setup menu.
    assert result2["type"] is FlowResultType.MENU
    assert result2["step_id"] == "setup_menu"
    assert "setup_add_dmx_light" in result2["menu_options"]
    assert "setup_finish" in result2["menu_options"]

    # Skip DMX, finish setup.
    result3 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], user_input={"next_step_id": "setup_finish"}
    )
    assert result3["type"] is FlowResultType.CREATE_ENTRY
    assert result3["title"] == "Test Pool"
    assert result3["data"] == {CONF_NAME: "Test Pool"}
    assert result3["options"] == {
        CONF_URL: USER_INPUT[CONF_URL],
        CONF_USERNAME: USER_INPUT[CONF_USERNAME],
        CONF_PASSWORD: USER_INPUT[CONF_PASSWORD],
        CONF_SCAN_INTERVAL: USER_INPUT[CONF_SCAN_INTERVAL],
    }
    # No DMX lights configured → key omitted from options.
    assert CONF_DMX_LIGHTS not in result3["options"]


async def test_user_flow_skips_setup_menu_when_dmx_disabled(
    hass: HomeAssistant,
    mock_state_endpoint: aioresponses,
) -> None:
    """DMX-off controller: credentials submit creates the entry immediately.

    The default ``get_state.csv`` fixture has SYSINFO[5]=0 → DMX disabled.
    No reason to show an "Add a DMX light" menu the user can't use.
    """
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    # Goes straight from credentials to CREATE_ENTRY, no setup_menu in between.
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Pool"
    assert CONF_DMX_LIGHTS not in result2["options"]


async def test_user_flow_with_dmx_light_added(
    hass: HomeAssistant,
    mock_state_endpoint_dmx_on: aioresponses,
) -> None:
    """DMX-on controller → add one DMX light → finish → entry has CONF_DMX_LIGHTS."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_menu = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    # Open the add-light form.
    result_form = await hass.config_entries.flow.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "setup_add_dmx_light"}
    )
    assert result_form["type"] is FlowResultType.FORM
    assert result_form["step_id"] == "setup_add_dmx_light"

    # Submit a valid light → back at setup_menu, count placeholder = 1.
    result_after_add = await hass.config_entries.flow.async_configure(
        result_form["flow_id"],
        user_input={"name": "Pool main", "type": "rgbw", "start_channel": 1},
    )
    assert result_after_add["type"] is FlowResultType.MENU
    assert result_after_add["step_id"] == "setup_menu"
    assert result_after_add["description_placeholders"] == {"count": "1"}

    # Finish setup.
    result_done = await hass.config_entries.flow.async_configure(
        result_after_add["flow_id"], user_input={"next_step_id": "setup_finish"}
    )
    assert result_done["type"] is FlowResultType.CREATE_ENTRY
    saved_lights = result_done["options"][CONF_DMX_LIGHTS]
    assert len(saved_lights) == 1
    assert saved_lights[0]["slug"] == "pool_main"
    assert saved_lights[0]["name"] == "Pool main"
    assert saved_lights[0]["type"] == "rgbw"
    assert saved_lights[0]["start_channel"] == 1


async def test_user_flow_initial_dmx_overlap_rejected(
    hass: HomeAssistant,
    mock_state_endpoint_dmx_on: aioresponses,
) -> None:
    """Adding a second light that overlaps the first re-renders the form with an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result_menu = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    # Add Pool main RGBW@1 → occupies channels 1-4.
    result_form = await hass.config_entries.flow.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "setup_add_dmx_light"}
    )
    result_after = await hass.config_entries.flow.async_configure(
        result_form["flow_id"],
        user_input={"name": "Pool main", "type": "rgbw", "start_channel": 1},
    )
    assert result_after["type"] is FlowResultType.MENU
    # Open the add form again, try to add RGB@3 → overlaps channels 3-5.
    result_form2 = await hass.config_entries.flow.async_configure(
        result_after["flow_id"], user_input={"next_step_id": "setup_add_dmx_light"}
    )
    result_overlap = await hass.config_entries.flow.async_configure(
        result_form2["flow_id"],
        user_input={"name": "Conflicting", "type": "rgb", "start_channel": 3},
    )
    assert result_overlap["type"] is FlowResultType.FORM
    assert result_overlap["errors"] == {"start_channel": "overlap"}


async def test_user_flow_auth_error(
    hass: HomeAssistant,
    aio_mock: aioresponses,
) -> None:
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=401,
        body="Unauthorized",
        repeat=True,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "auth"}


async def test_user_flow_connection_error(
    hass: HomeAssistant,
    aio_mock: aioresponses,
) -> None:
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=500,
        body="Server Error",
        repeat=True,
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "connection"}


async def test_user_flow_timeout_maps_to_connection_error(
    hass: HomeAssistant,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A controller timeout should land in the 'connection' bucket, not 'unknown'."""
    from unittest.mock import AsyncMock

    from proconip import TimeoutException

    from custom_components.proconip_pool_controller import config_flow as cf_module

    monkeypatch.setattr(
        cf_module.ProconipConnectionTester,
        "async_test_credentials",
        AsyncMock(side_effect=TimeoutException("API request timed out")),
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": "connection"}


async def test_options_flow_no_init_required(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Modern HA wires self.config_entry automatically; we don't override __init__."""
    handler = ProconipPoolControllerOptionsFlowHandler()
    # No exception. config_entry binding happens via the platform when the
    # flow actually starts (covered by test_options_flow_happy_path).
    assert handler is not None


async def test_options_flow_hides_dmx_entry_when_dmx_disabled(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Default fixture has DMX off: top-level menu omits the dmx_lights_menu entry."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    # No "dmx_lights_menu" — controller doesn't support DMX, no existing lights either.
    assert set(result["menu_options"]) == {"connection", "save_and_finish"}

    # Unload the entry cleanly before test teardown
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_options_flow_shows_dmx_entry_when_dmx_enabled(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint_dmx_on: aioresponses,
) -> None:
    """DMX-on controller: top-level menu includes the dmx_lights_menu entry."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert set(result["menu_options"]) == {
        "connection",
        "dmx_lights_menu",
        "save_and_finish",
    }

    # Unload the entry cleanly before test teardown
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
