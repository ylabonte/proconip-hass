"""DataUpdateCoordinator for ProCon.IP Pool Controller."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from proconip.api import (
    BadCredentialsException,
    BadStatusCodeException,
    ProconipApiException,
)

from .api import ProconipApiClient
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class ProconipPoolControllerDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: ProconipApiClient,
        update_interval_in_seconds: int,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_in_seconds),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.async_get_data()
        except BadCredentialsException as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except (BadStatusCodeException, ProconipApiException) as exception:
            raise UpdateFailed(exception) from exception
