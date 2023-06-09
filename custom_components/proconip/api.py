"""Sample API Client."""
import logging

import aiohttp

import proconip.api

from proconip.definitions import (
    ConfigObject,
    GetStateData,
)

TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


class ProconipApiClient:
    """ProCon.IP API Wrapper"""
    _api_config: ConfigObject
    _session: aiohttp.ClientSession
    _most_recent_data: GetStateData | None

    def __init__(
        self, base_url: str, username: str, password: str, session: aiohttp.ClientSession
    ) -> None:
        """Sample API Client."""
        self._api_config = ConfigObject(base_url, username, password)
        self._session = session
        self._most_recent_data = None

    async def async_get_data(self) -> GetStateData:
        """Get data from the API."""
        self._most_recent_data = await proconip.api.async_get_state(self._session, self._api_config)
        return self._most_recent_data

    async def async_switch_on(self, relay_id: int) -> None:
        """Switch relay on."""
        if self._most_recent_data is None:
            await self.async_get_data()
        await proconip.api.async_switch_on(self._session, self._api_config, self._most_recent_data,
                                           self._most_recent_data.get_relay(relay_id))

    async def async_switch_off(self, relay_id: int) -> None:
        """Switch relay off."""
        if self._most_recent_data is None:
            await self.async_get_data()
        await proconip.api.async_switch_off(self._session, self._api_config, self._most_recent_data,
                                            self._most_recent_data.get_relay(relay_id))

    async def async_set_auto_mode(self, relay_id: int) -> None:
        """Set relay to auto mode."""
        if self._most_recent_data is None:
            await self.async_get_data()
        await proconip.api.async_set_auto_mode(self._session,
                                               self._api_config,
                                               self._most_recent_data,
                                               self._most_recent_data.get_relay(relay_id))
