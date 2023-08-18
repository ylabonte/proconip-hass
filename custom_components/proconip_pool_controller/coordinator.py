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
from proconip.definitions import GetStateData
from proconip.api import (
    BadCredentialsException,
    BadStatusCodeException,
    ProconipApiException,
)

from .api import ProconipApiClient
from .const import DOMAIN, LOGGER


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class ProconipPoolControllerDataUpdateCoordinator(DataUpdateCoordinator[GetStateData]):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry
    config_entry_id: str
    data: GetStateData

    _active_dosage_relays = {}

    def __init__(
        self,
        hass: HomeAssistant,
        client: ProconipApiClient,
        update_interval_in_seconds: float,
        config_entry_id: str,
    ) -> None:
        """Initialize."""
        self.client = client
        self.config_entry_id = config_entry_id
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval_in_seconds),
            update_method=self.proconip_update_method,
        )

    async def proconip_update_method(self) -> GetStateData:
        """Update data via library."""
        data: GetStateData = None
        try:
            data = await self.client.async_get_data()
        except BadCredentialsException as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except (BadStatusCodeException, ProconipApiException) as exception:
            raise UpdateFailed(exception) from exception

        self._active_dosage_relays = {
            data.chlorine_dosage_relay_id: data.is_chlorine_dosage_enabled(),
            data.ph_minus_dosage_relay_id: data.is_ph_minus_dosage_enabled(),
            data.ph_plus_dosage_relay_id: data.is_ph_plus_dosage_enabled(),
        }

        return data

    def is_active_dosage_relay(self, relay_id) -> bool:
        """Return True if the given relay_id refers to an active dosage relay."""
        if relay_id in self._active_dosage_relays:
            return self._active_dosage_relays[relay_id]

        return False

    # @property
    # def config_entry(self):
    #     """Property wrapping the _config_entry attribite."""
    #     return self._config_entry

    # @config_entry.setter
    # def config_entry(self, value):
    #     """Setter for _config_entry attribute, updating the update_interval attribute."""
    #     self._config_entry = value
    #     if value is not None and CONF_SCAN_INTERVAL in value.options:
    #         self.update_interval = timedelta(seconds=value.options[CONF_SCAN_INTERVAL])
