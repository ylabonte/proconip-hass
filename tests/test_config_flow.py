"""Tests for the config flow and options flow."""

from __future__ import annotations

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
from custom_components.proconip_pool_controller.const import DOMAIN

USER_INPUT = {
    CONF_NAME: "Test Pool",
    CONF_URL: "http://192.0.2.10",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "admin",
    CONF_SCAN_INTERVAL: 30,
}


async def test_user_flow_happy_path(
    hass: HomeAssistant,
    mock_state_endpoint: aioresponses,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=USER_INPUT
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Test Pool"
    assert result2["data"] == {CONF_NAME: "Test Pool"}
    assert result2["options"] == {
        CONF_URL: USER_INPUT[CONF_URL],
        CONF_USERNAME: USER_INPUT[CONF_USERNAME],
        CONF_PASSWORD: USER_INPUT[CONF_PASSWORD],
        CONF_SCAN_INTERVAL: USER_INPUT[CONF_SCAN_INTERVAL],
    }


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


async def test_options_flow_handler_init_does_not_raise(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Regression test for #70 / #71.

    Modern HA's OptionsFlow.config_entry is a read-only property; the previous
    `self.config_entry = config_entry` assignment raised AttributeError.
    """
    handler = ProconipPoolControllerOptionsFlowHandler(config_entry)
    assert handler.options == dict(config_entry.options)


async def test_options_flow_shows_init_form(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> None:
    """Test that options flow shows the init form when entry is loaded."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    # Unload the entry cleanly before test teardown
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
