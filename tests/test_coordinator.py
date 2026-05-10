"""Tests for the data update coordinator."""

from __future__ import annotations

from unittest.mock import patch

from aioresponses import aioresponses
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN
from custom_components.proconip_pool_controller.coordinator import (
    ProconipPoolControllerDataUpdateCoordinator,
)


async def test_first_refresh_success(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    assert coordinator.data is not None
    assert coordinator.last_update_success is True


async def test_auth_failure_marks_entry_for_reauth(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
) -> None:
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=401,
        body="Unauthorized",
        repeat=True,
    )
    # The integration does not implement async_step_reauth yet (added in Task 9).
    # Patch async_start_reauth on the config entry class to prevent HA from
    # attempting a reauth flow that would raise UnknownStep during teardown.
    with patch(
        "homeassistant.config_entries.ConfigEntry.async_start_reauth",
        return_value=None,
    ):
        assert not await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_update_failure_keeps_entry_loaded(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    aio_mock: aioresponses,
) -> None:
    aio_mock.get(
        "http://192.0.2.10/GetState.csv",
        status=500,
        body="Server Error",
        repeat=True,
    )
    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_dosage_relay_tracking(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> None:
    entry = setup_integration
    coordinator: ProconipPoolControllerDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    chlorine_id = coordinator.data.chlorine_dosage_relay_id
    assert coordinator.is_active_dosage_relay(relay_id=chlorine_id) is (
        coordinator.data.is_chlorine_dosage_enabled()
    )
    # A relay ID that is not a dosage relay should always return False.
    assert coordinator.is_active_dosage_relay(relay_id=999) is False
