"""Adds config flow for ProCon.IP Pool Controller."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import (
    callback,
)
from homeassistant.helpers import selector
from proconip import (
    BadCredentialsException,
    BadStatusCodeException,
    ProconipApiException,
)

from .api import ProconipConnectionTester
from .const import DOMAIN, LOGGER


class ProconipPoolControllerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ProCon.IP Pool Controller."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        connection_tester = ProconipConnectionTester(self.hass)
        _errors = {}
        if user_input is not None:
            try:
                await connection_tester.async_test_credentials(
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
                    title=user_input[CONF_NAME],
                    data={CONF_NAME: user_input[CONF_NAME]},
                    options={
                        CONF_URL: user_input[CONF_URL],
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME,
                        default=(user_input or {}).get(CONF_NAME),  # type: ignore
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                    ),
                    vol.Required(
                        CONF_URL,
                        default=(user_input or {}).get(CONF_URL),  # type: ignore
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.URL),
                    ),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {CONF_USERNAME: "admin"}).get(CONF_USERNAME),  # type: ignore
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD),
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=(user_input or {}).get(CONF_SCAN_INTERVAL, 3),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.SLIDER,
                            min=1,
                            max=60,
                            step=0.5,
                        ),
                    ),
                }
            ),
            description_placeholders={},
            errors=_errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return ProconipPoolControllerOptionsFlowHandler()


class ProconipPoolControllerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for this integration."""

    VERSION = 1
    MINOR_VERSION = 2

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle device options."""
        connection_tester = ProconipConnectionTester(self.hass)
        _errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await connection_tester.async_test_credentials(
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
                new_options = {**self.config_entry.options, **user_input}
                return self.async_create_entry(data=new_options)

        current = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_URL,
                        default=(user_input or current).get(CONF_URL),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.URL,
                        ),
                    ),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or current).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(
                        CONF_PASSWORD,
                        default=(user_input or current).get(CONF_PASSWORD),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=(user_input or current).get(CONF_SCAN_INTERVAL, 3),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.SLIDER,
                            min=1,
                            max=60,
                            step=0.5,
                        ),
                    ),
                }
            ),
            description_placeholders={},
            errors=_errors,
        )
