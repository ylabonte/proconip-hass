"""ProCon.IP API Client."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from proconip.definitions import (
    ConfigObject,
    GetStateData,
)

from proconip.api import (
    GetState,
    RelaySwitch,
    DosageControl,
)


class ProconipApiClient:
    """ProCon.IP API Client."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        hass: HomeAssistant,
    ) -> None:
        """ProCon.IP API Client."""
        self.hass = hass
        self._base_url = base_url
        self._username = username
        self._password = password
        self._session = async_get_clientsession(hass=hass)
        self._api_config = ConfigObject(
            base_url=self._base_url,
            username=self._username,
            password=self._password,
        )
        self._get_state_api = GetState(
            client_session=self._session, config=self._api_config
        )
        self._relay_switch_api = RelaySwitch(
            client_session=self._session, config=self._api_config
        )
        self._dosage_control_api = DosageControl(
            client_session=self._session, config=self._api_config
        )
        self._most_recent_data = None

    async def async_get_data(
        self,
    ) -> GetStateData:
        """Get data from the API."""
        self._most_recent_data = await self._get_state_api.async_get_state()
        return self._most_recent_data

    async def async_switch_on(
        self,
        relay_id: int,
    ) -> str:
        """Switch on the relay with given relay_id."""
        current_state = (
            self._most_recent_data
            if self._most_recent_data is not None
            else await self.async_get_data()
        )
        return await self._relay_switch_api.async_switch_on(
            current_state=current_state,
            relay_id=relay_id,
        )

    async def async_switch_off(
        self,
        relay_id: int,
    ) -> str:
        """Switch off the relay with given relay_id."""
        current_state = (
            self._most_recent_data
            if self._most_recent_data is not None
            else await self.async_get_data()
        )
        return await self._relay_switch_api.async_switch_off(
            current_state=current_state,
            relay_id=relay_id,
        )

    async def async_switch_to_auto(
        self,
        relay_id: int,
    ) -> str:
        """Set relay with given relay_id to auto mode."""
        current_state = (
            self._most_recent_data
            if self._most_recent_data is not None
            else await self.async_get_data()
        )
        return await self._relay_switch_api.async_set_auto_mode(
            current_state=current_state,
            relay_id=relay_id,
        )

    async def async_start_chlorine_dosage(
        self,
        duration_in_seconds: int,
    ) -> str:
        """Start chlorine dosage for given amount of time."""
        return await self._dosage_control_api.async_chlorine_dosage(
            dosage_duration=duration_in_seconds,
        )

    async def async_start_ph_minus_dosage(
        self,
        duration_in_seconds: int,
    ) -> str:
        """Start pH minus dosage for given amount of time."""
        return await self._dosage_control_api.async_ph_minus_dosage(
            dosage_duration=duration_in_seconds,
        )

    async def async_start_ph_plus_dosage(
        self,
        duration_in_seconds: int,
    ) -> str:
        """Start pH plus dosage for given amount of time."""
        return await self._dosage_control_api.async_ph_plus_dosage(
            dosage_duration=duration_in_seconds,
        )


class ProconipConnectionTester:
    """Helper class for connection testing."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize connection tester."""
        self.hass = hass

    async def async_test_credentials(
        self, url: str, username: str, password: str
    ) -> None:
        """Validate base url and credentials."""
        client = ProconipApiClient(
            base_url=url,
            username=username,
            password=password,
            hass=self.hass,
        )
        await client.async_get_data()
