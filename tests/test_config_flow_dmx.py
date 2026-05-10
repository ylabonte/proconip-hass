"""Tests for the DMX lights subflow in OptionsFlow."""

from __future__ import annotations

from aioresponses import aioresponses
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import CONF_DMX_LIGHTS

CONNECTION_INPUT = {
    CONF_URL: "http://192.0.2.10",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "admin",
    CONF_SCAN_INTERVAL: 30,
}


async def test_options_flow_chains_to_menu(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=CONNECTION_INPUT
    )
    assert result2["type"] is FlowResultType.MENU
    assert result2["step_id"] == "menu"


async def test_dmx_light_add_happy_path(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=CONNECTION_INPUT
    )
    # Navigate menu -> dmx_lights_menu -> dmx_light_add
    result_menu = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_add = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_light_add"}
    )
    # Submit form
    result_form = await hass.config_entries.options.async_configure(
        result_add["flow_id"],
        user_input={"name": "Pool main", "type": "rgbw", "start_channel": 1},
    )
    assert result_form["type"] is FlowResultType.MENU  # back at dmx_lights_menu
    assert result_form["step_id"] == "dmx_lights_menu"
    # Navigate back to top-level menu, then save and finish
    result_back = await hass.config_entries.options.async_configure(
        result_form["flow_id"], user_input={"next_step_id": "menu"}
    )
    assert result_back["type"] is FlowResultType.MENU
    assert result_back["step_id"] == "menu"
    result_save = await hass.config_entries.options.async_configure(
        result_back["flow_id"], user_input={"next_step_id": "save_and_finish"}
    )
    assert result_save["type"] is FlowResultType.CREATE_ENTRY
    # Process the update-listener reload triggered by async_create_entry before
    # the test teardown unloads the entry independently.
    await hass.async_block_till_done()
    saved_lights = result_save["data"][CONF_DMX_LIGHTS]
    assert len(saved_lights) == 1
    assert saved_lights[0]["slug"] == "pool_main"
    assert saved_lights[0]["start_channel"] == 1
    assert saved_lights[0]["type"] == "rgbw"


async def test_dmx_light_add_overlap_rejected(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    entry = setup_integration
    # Pre-seed an existing light via direct options write
    hass.config_entries.async_update_entry(
        entry,
        options={
            **entry.options,
            CONF_DMX_LIGHTS: [
                {
                    "slug": "pool_main",
                    "name": "Pool main",
                    "type": "rgbw",
                    "start_channel": 1,
                }
            ],
        },
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=CONNECTION_INPUT
    )
    result_menu = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_add = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_light_add"}
    )
    # Try to add an RGB starting at channel 3 (overlaps with channels 1-4)
    result_form = await hass.config_entries.options.async_configure(
        result_add["flow_id"],
        user_input={"name": "Conflicting", "type": "rgb", "start_channel": 3},
    )
    assert result_form["type"] is FlowResultType.FORM
    assert result_form["errors"] == {"start_channel": "overlap"}


async def test_round_trip_to_connection_settings_preserves_dmx_lights(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Adding a light then revisiting connection settings must not drop the light."""
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=CONNECTION_INPUT
    )
    # Navigate to dmx_lights_menu -> add
    result_lights = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_add = await hass.config_entries.options.async_configure(
        result_lights["flow_id"], user_input={"next_step_id": "dmx_light_add"}
    )
    await hass.config_entries.options.async_configure(
        result_add["flow_id"],
        user_input={"name": "Pool main", "type": "rgbw", "start_channel": 1},
    )
    # Back to top menu, then back into connection settings, re-submit
    result_back = await hass.config_entries.options.async_configure(
        result_add["flow_id"], user_input={"next_step_id": "menu"}
    )
    result_init = await hass.config_entries.options.async_configure(
        result_back["flow_id"], user_input={"next_step_id": "init"}
    )
    result_resubmit = await hass.config_entries.options.async_configure(
        result_init["flow_id"], user_input=CONNECTION_INPUT
    )
    # Now navigate back to top menu and finish
    result_save = await hass.config_entries.options.async_configure(
        result_resubmit["flow_id"], user_input={"next_step_id": "save_and_finish"}
    )
    assert result_save["type"] is FlowResultType.CREATE_ENTRY
    saved_lights = result_save["data"][CONF_DMX_LIGHTS]
    assert len(saved_lights) == 1, (
        f"Expected 1 light to survive the round-trip; got: {saved_lights}"
    )
    assert saved_lights[0]["slug"] == "pool_main"
    await hass.async_block_till_done()


async def test_dmx_light_add_out_of_range_rejected(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    entry = setup_integration
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=CONNECTION_INPUT
    )
    result_menu = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_add = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_light_add"}
    )
    # RGBW (4 channels) starting at channel 14 -> would need channels 14-17
    result_form = await hass.config_entries.options.async_configure(
        result_add["flow_id"],
        user_input={"name": "Spans past 16", "type": "rgbw", "start_channel": 14},
    )
    assert result_form["type"] is FlowResultType.FORM
    assert result_form["errors"] == {"start_channel": "out_of_range"}
