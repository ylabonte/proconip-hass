"""Shared pytest fixtures for proconip-hass tests."""

from __future__ import annotations

import pathlib
from collections.abc import AsyncIterator, Generator
from typing import Any

import pytest
from aioresponses import aioresponses
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proconip_pool_controller.const import DOMAIN

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

BASE_URL = "http://192.0.2.10"
USERNAME = "admin"
PASSWORD = "admin"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: Any,
) -> None:
    """Enable loading of the custom integration in every test."""
    return


@pytest.fixture
def get_state_csv() -> str:
    return (FIXTURES_DIR / "get_state.csv").read_text()


@pytest.fixture
def get_dmx_csv() -> str:
    return (FIXTURES_DIR / "get_dmx.csv").read_text()


@pytest.fixture
def aio_mock() -> Generator[aioresponses]:
    with aioresponses() as m:
        yield m


@pytest.fixture
def mock_state_endpoint(aio_mock: aioresponses, get_state_csv: str) -> aioresponses:
    aio_mock.get(
        f"{BASE_URL}/GetState.csv",
        status=200,
        body=get_state_csv,
        repeat=True,
    )
    return aio_mock


@pytest.fixture
def mock_dmx_endpoint(aio_mock: aioresponses, get_dmx_csv: str) -> aioresponses:
    aio_mock.get(
        f"{BASE_URL}/GetDmx.csv",
        status=200,
        body=get_dmx_csv,
        repeat=True,
    )
    return aio_mock


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Pool",
        data={CONF_NAME: "Test Pool"},
        options={
            CONF_URL: BASE_URL,
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: PASSWORD,
            CONF_SCAN_INTERVAL: 30,
        },
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    mock_state_endpoint: aioresponses,
) -> AsyncIterator[MockConfigEntry]:
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    yield config_entry
    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
