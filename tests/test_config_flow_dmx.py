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


async def test_dmx_light_add_happy_path(
    hass: HomeAssistant,
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    """init (menu) → dmx_lights_menu → add → back to dmx_lights_menu → back to init → save.

    Requires the DMX-on fixture: with DMX off + no pre-seeded light, the
    top-level menu would omit ``dmx_lights_menu`` and this flow would
    never start.
    """
    entry = setup_integration_dmx_on
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"

    # init → dmx_lights_menu → dmx_light_add
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
    # Back to init (top menu), then save and finish.
    result_back = await hass.config_entries.options.async_configure(
        result_form["flow_id"], user_input={"next_step_id": "init"}
    )
    assert result_back["type"] is FlowResultType.MENU
    assert result_back["step_id"] == "init"
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
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    # DMX must be currently available so the `Add light` submenu entry is
    # offered — orphan-management mode (DMX off + lights configured)
    # intentionally hides it, see
    # `test_dmx_lights_menu_hides_add_when_dmx_unavailable_with_orphans`.
    entry = setup_integration_dmx_on
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
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    """Adding a light then revisiting connection settings must not drop the light.

    DMX-on fixture so ``dmx_lights_menu`` is reachable from a clean start.
    """
    entry = setup_integration_dmx_on
    result = await hass.config_entries.options.async_init(entry.entry_id)
    # init → dmx_lights_menu → add
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
    # Back to init (top menu), then into connection, re-submit credentials.
    result_back = await hass.config_entries.options.async_configure(
        result_add["flow_id"], user_input={"next_step_id": "init"}
    )
    result_connection = await hass.config_entries.options.async_configure(
        result_back["flow_id"], user_input={"next_step_id": "connection"}
    )
    assert result_connection["type"] is FlowResultType.FORM
    assert result_connection["step_id"] == "connection"
    result_resubmit = await hass.config_entries.options.async_configure(
        result_connection["flow_id"], user_input=CONNECTION_INPUT
    )
    # Successful connection submit lands back on init (the menu).
    assert result_resubmit["type"] is FlowResultType.MENU
    assert result_resubmit["step_id"] == "init"
    # Save and finish.
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
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    entry = setup_integration_dmx_on
    result = await hass.config_entries.options.async_init(entry.entry_id)
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


async def test_dmx_light_add_blank_name_rejected(
    hass: HomeAssistant,
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    """Whitespace-only names must surface an explicit error, not be silently
    accepted with a placeholder slug.
    """
    entry = setup_integration_dmx_on
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result_menu = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_add = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_light_add"}
    )
    result_form = await hass.config_entries.options.async_configure(
        result_add["flow_id"],
        user_input={"name": "   ", "type": "rgbw", "start_channel": 1},
    )
    assert result_form["type"] is FlowResultType.FORM
    assert result_form["errors"] == {"name": "blank"}


def _seed_one_light(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Persist a single ``Pool main`` (RGBW, ch 1) light onto the entry."""
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


async def _open_dmx_lights_menu(hass: HomeAssistant, entry: MockConfigEntry) -> dict:
    """Drive the flow from init → dmx_lights_menu and return the menu result."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )


async def test_options_flow_shows_dmx_entry_when_orphan_lights_exist(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Controller reports DMX off but entry has lights → menu still shows dmx_lights_menu.

    Lets the user clean up orphans (e.g. they disabled DMX in the
    controller after configuring some lights). Uses the default DMX-off
    fixture deliberately.
    """
    entry = setup_integration
    _seed_one_light(hass, entry)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "dmx_lights_menu" in result["menu_options"]


async def test_dmx_lights_menu_hides_add_when_dmx_unavailable_with_orphans(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Orphan-management mode (DMX off + lights configured) must not show ``Add light``.

    The submenu surfaces in this mode so users can manage/remove existing
    lights — but offering to add more entries against a DMX-disabled
    controller would just create more nonfunctional state. Edit/remove
    rows must still appear so the existing lights remain manageable.
    """
    entry = setup_integration
    _seed_one_light(hass, entry)
    result_menu = await _open_dmx_lights_menu(hass, entry)
    assert result_menu["type"] is FlowResultType.MENU
    assert "dmx_light_add" not in result_menu["menu_options"], (
        f"Add light must be hidden in orphan-management mode; got: {result_menu['menu_options']}"
    )
    # Edit + remove paths still available so the orphans can be cleaned up.
    assert "dmx_light_edit_pool_main" in result_menu["menu_options"]
    assert "dmx_lights_remove_menu" in result_menu["menu_options"]


async def test_dmx_lights_menu_shows_add_when_dmx_currently_available(
    hass: HomeAssistant,
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    """The standard happy-path: DMX on → `Add light` is offered."""
    entry = setup_integration_dmx_on
    result_menu = await _open_dmx_lights_menu(hass, entry)
    assert result_menu["type"] is FlowResultType.MENU
    assert "dmx_light_add" in result_menu["menu_options"]


async def test_dmx_light_edit_persists_changes_without_duplicating(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Editing an existing DMX light updates it in place (same slug, new fields).

    The dispatcher creates `async_step_dmx_light_edit_<slug>` on the fly
    via `__getattr__`; this exercises that path end-to-end and confirms
    the saved light list keeps a single entry with the edited values.
    """
    entry = setup_integration
    _seed_one_light(hass, entry)
    result_menu = await _open_dmx_lights_menu(hass, entry)

    # Pick the dynamically-dispatched edit step for the seeded light.
    edit_step_id = "dmx_light_edit_pool_main"
    assert edit_step_id in result_menu["menu_options"]
    result_edit_form = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": edit_step_id}
    )
    assert result_edit_form["type"] is FlowResultType.FORM
    assert result_edit_form["step_id"] == edit_step_id

    # Change name + type + start_channel. RGB (3 channels) starting at 4
    # → uses channels 4-6, doesn't collide with the seeded layout's footprint.
    result_after_save = await hass.config_entries.options.async_configure(
        result_edit_form["flow_id"],
        user_input={"name": "Pool main renamed", "type": "rgb", "start_channel": 4},
    )
    # Saving an edit bounces back to the lights menu.
    assert result_after_save["type"] is FlowResultType.MENU

    # Finalise the options flow so the entry's options are persisted.
    result_back = await hass.config_entries.options.async_configure(
        result_after_save["flow_id"], user_input={"next_step_id": "init"}
    )
    await hass.config_entries.options.async_configure(
        result_back["flow_id"], user_input={"next_step_id": "save_and_finish"}
    )
    await hass.async_block_till_done()

    saved = entry.options[CONF_DMX_LIGHTS]
    assert len(saved) == 1, f"Expected exactly one light after edit; got: {saved}"
    assert saved[0]["slug"] == "pool_main", "slug must be preserved across an edit"
    assert saved[0]["name"] == "Pool main renamed"
    assert saved[0]["type"] == "rgb"
    assert saved[0]["start_channel"] == 4


async def test_dmx_lights_menu_includes_remove_when_lights_exist(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """The Remove submenu entry only makes sense when there's something to remove."""
    entry = setup_integration
    _seed_one_light(hass, entry)
    result_menu = await _open_dmx_lights_menu(hass, entry)
    assert result_menu["type"] is FlowResultType.MENU
    assert "dmx_lights_remove_menu" in result_menu["menu_options"]
    assert "dmx_light_edit_pool_main" in result_menu["menu_options"]
    # The old direct-remove row must be gone.
    assert "dmx_light_remove_pool_main" not in result_menu["menu_options"]


async def test_dmx_lights_menu_omits_remove_when_no_lights(
    hass: HomeAssistant,
    setup_integration_dmx_on: MockConfigEntry,
) -> None:
    """No lights → no Remove entry (else it'd open a dead-end submenu).

    Needs DMX-on fixture: with DMX off + no lights, ``dmx_lights_menu``
    isn't reachable from the top-level menu at all.
    """
    entry = setup_integration_dmx_on
    result_menu = await _open_dmx_lights_menu(hass, entry)
    assert result_menu["type"] is FlowResultType.MENU
    assert "dmx_lights_remove_menu" not in result_menu["menu_options"]
    # Back button now routes to "init" (the new top-level menu).
    assert list(result_menu["menu_options"]) == ["dmx_light_add", "init"]


async def test_dmx_light_remove_confirm_then_perform_deletes(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Confirm → Remove "<name>" should drop the light from the merged options."""
    entry = setup_integration
    _seed_one_light(hass, entry)
    result_menu = await _open_dmx_lights_menu(hass, entry)
    # dmx_lights_menu → dmx_lights_remove_menu
    result_remove_menu = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_lights_remove_menu"}
    )
    assert result_remove_menu["type"] is FlowResultType.MENU
    assert result_remove_menu["step_id"] == "dmx_lights_remove_menu"
    # → confirm screen for pool_main
    result_confirm = await hass.config_entries.options.async_configure(
        result_remove_menu["flow_id"],
        user_input={"next_step_id": "dmx_light_remove_confirm_pool_main"},
    )
    assert result_confirm["type"] is FlowResultType.MENU
    assert result_confirm["step_id"] == "dmx_light_remove_confirm_pool_main"
    assert set(result_confirm["menu_options"]) == {
        "dmx_light_remove_perform",
        "dmx_lights_remove_menu",
    }
    # → perform (irreversible delete) → bounces to dmx_lights_menu
    result_after = await hass.config_entries.options.async_configure(
        result_confirm["flow_id"], user_input={"next_step_id": "dmx_light_remove_perform"}
    )
    assert result_after["type"] is FlowResultType.MENU
    assert result_after["step_id"] == "dmx_lights_menu"
    # The light is gone, so the Remove entry should be hidden again.
    assert "dmx_lights_remove_menu" not in result_after["menu_options"]
    assert "dmx_light_edit_pool_main" not in result_after["menu_options"]
    # Save and finish to commit the deletion.
    result_back = await hass.config_entries.options.async_configure(
        result_after["flow_id"], user_input={"next_step_id": "init"}
    )
    result_save = await hass.config_entries.options.async_configure(
        result_back["flow_id"], user_input={"next_step_id": "save_and_finish"}
    )
    assert result_save["type"] is FlowResultType.CREATE_ENTRY
    assert result_save["data"][CONF_DMX_LIGHTS] == []
    await hass.async_block_till_done()


async def test_dmx_light_remove_cancel_keeps_light(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Cancel from the confirm screen returns to the remove menu without mutating state."""
    entry = setup_integration
    _seed_one_light(hass, entry)
    result_menu = await _open_dmx_lights_menu(hass, entry)
    result_remove_menu = await hass.config_entries.options.async_configure(
        result_menu["flow_id"], user_input={"next_step_id": "dmx_lights_remove_menu"}
    )
    result_confirm = await hass.config_entries.options.async_configure(
        result_remove_menu["flow_id"],
        user_input={"next_step_id": "dmx_light_remove_confirm_pool_main"},
    )
    # Cancel routes back to the remove menu — light still listed.
    result_cancelled = await hass.config_entries.options.async_configure(
        result_confirm["flow_id"], user_input={"next_step_id": "dmx_lights_remove_menu"}
    )
    assert result_cancelled["type"] is FlowResultType.MENU
    assert result_cancelled["step_id"] == "dmx_lights_remove_menu"
    assert "dmx_light_remove_confirm_pool_main" in result_cancelled["menu_options"]
    # Walk all the way back and save — the originally-seeded light must persist.
    result_back_to_lights = await hass.config_entries.options.async_configure(
        result_cancelled["flow_id"], user_input={"next_step_id": "dmx_lights_menu"}
    )
    result_back_to_top = await hass.config_entries.options.async_configure(
        result_back_to_lights["flow_id"], user_input={"next_step_id": "init"}
    )
    result_save = await hass.config_entries.options.async_configure(
        result_back_to_top["flow_id"], user_input={"next_step_id": "save_and_finish"}
    )
    assert result_save["type"] is FlowResultType.CREATE_ENTRY
    saved_lights = result_save["data"][CONF_DMX_LIGHTS]
    assert len(saved_lights) == 1
    assert saved_lights[0]["slug"] == "pool_main"
    await hass.async_block_till_done()
