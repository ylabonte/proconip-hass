"""Adds config flow for ProCon.IP Pool Controller."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from proconip.api import (
    BadCredentialsException,
    BadStatusCodeException,
    ProconipApiException,
)

from .api import ProconipApiClient
from .const import DOMAIN, LOGGER


class ProconipPoolControllerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ProCon.IP Pool Controller."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    url=user_input[CONF_URL],
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except BadCredentialsException as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except BadStatusCodeException as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except ProconipApiException as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_URL],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=(user_input or {}).get(CONF_URL),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL),
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=(user_input or {CONF_SCAN_INTERVAL: 3}).get(
                            CONF_SCAN_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.SLIDER,
                            min=1,
                            max=60,
                            step=0.5,
                        ),
                    ),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {CONF_USERNAME: "admin"}).get(
                            CONF_USERNAME
                        ),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def _test_credentials(self, url: str, username: str, password: str) -> None:
        """Validate base url and credentials."""
        client = ProconipApiClient(
            base_url=url,
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()
