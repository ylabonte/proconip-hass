"""Adds config flow for ProCon.IP Pool Controller."""

from __future__ import annotations

import re
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
from .const import CONF_DMX_LIGHTS, DOMAIN, LOGGER

LIGHT_TYPE_CHANNEL_COUNT: dict[str, int] = {"dimmer": 1, "rgb": 3, "rgbw": 4}


def _slugify_name(name: str) -> str:
    """Lowercase, alphanumeric + underscore, collapsed."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "light"


def _validate_no_overlap(
    lights: list[dict],
    new_start: int,
    new_count: int,
    skip_slug: str | None = None,
) -> bool:
    """Return True when the new channel range does not overlap with existing lights."""
    new_range = set(range(new_start, new_start + new_count))
    for light in lights:
        if skip_slug is not None and light["slug"] == skip_slug:
            continue
        existing_count = LIGHT_TYPE_CHANNEL_COUNT[light["type"]]
        existing_range = set(
            range(light["start_channel"], light["start_channel"] + existing_count)
        )
        if existing_range & new_range:
            return False
    return True


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
                base = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
                new_options = {**base, **user_input}
                self._merged_options = new_options
                return await self.async_step_menu()

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

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the top-level integration management menu."""
        return self.async_show_menu(
            step_id="menu",
            menu_options=["init", "dmx_lights_menu", "save_and_finish"],
        )

    async def async_step_save_and_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save all accumulated options and finish the flow."""
        options = getattr(self, "_merged_options", None) or dict(
            self.config_entry.options
        )
        return self.async_create_entry(data=options)

    async def async_step_dmx_lights_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the DMX lights management menu."""
        options = getattr(self, "_merged_options", None) or dict(
            self.config_entry.options
        )
        lights: list[dict] = list(options.get(CONF_DMX_LIGHTS, []))
        menu: list[str] = ["dmx_light_add"]
        for light in lights:
            menu.append(f"dmx_light_edit_{light['slug']}")
        for light in lights:
            menu.append(f"dmx_light_remove_{light['slug']}")
        menu.append("menu")
        return self.async_show_menu(step_id="dmx_lights_menu", menu_options=menu)

    async def async_step_dmx_light_add(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle adding a new DMX light."""
        return await self._show_dmx_light_form(user_input, edit_slug=None)

    async def _show_dmx_light_form(
        self,
        user_input: dict[str, Any] | None,
        edit_slug: str | None,
    ) -> config_entries.ConfigFlowResult:
        """Show the form for adding or editing a DMX light."""
        options = getattr(self, "_merged_options", None) or dict(
            self.config_entry.options
        )
        lights: list[dict] = list(options.get(CONF_DMX_LIGHTS, []))
        existing = next(
            (light for light in lights if light["slug"] == edit_slug), None
        )

        errors: dict[str, str] = {}
        if user_input is not None:
            light_type = user_input["type"]
            count = LIGHT_TYPE_CHANNEL_COUNT[light_type]
            start = int(user_input["start_channel"])

            if start < 1 or start + count - 1 > 16:
                errors["start_channel"] = "out_of_range"
            elif not _validate_no_overlap(lights, start, count, skip_slug=edit_slug):
                errors["start_channel"] = "overlap"

            slug = existing["slug"] if existing else _slugify_name(user_input["name"])
            if existing is None:
                if any(light["slug"] == slug for light in lights):
                    errors["name"] = "duplicate"

            if not errors:
                new_light = {
                    "slug": slug,
                    "name": user_input["name"],
                    "type": light_type,
                    "start_channel": start,
                }
                if existing is not None:
                    lights = [
                        new_light if light["slug"] == edit_slug else light
                        for light in lights
                    ]
                else:
                    lights.append(new_light)
                options[CONF_DMX_LIGHTS] = lights
                self._merged_options = options
                return await self.async_step_dmx_lights_menu()

        defaults = (
            user_input
            if errors and user_input is not None
            else existing or {"name": "", "type": "rgbw", "start_channel": 1}
        )
        step_id = "dmx_light_add" if existing is None else f"dmx_light_edit_{edit_slug}"
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=defaults["name"]): str,
                    vol.Required("type", default=defaults["type"]): vol.In(
                        list(LIGHT_TYPE_CHANNEL_COUNT.keys())
                    ),
                    vol.Required(
                        "start_channel", default=defaults["start_channel"]
                    ): vol.All(int, vol.Range(min=1, max=16)),
                }
            ),
            errors=errors,
        )

    async def async_step_dmx_light_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Placeholder — edit/remove are dispatched dynamically via __getattr__."""
        raise NotImplementedError(
            "Edit/Remove are dispatched dynamically — see __getattr__"
        )

    def __getattr__(self, item: str) -> Any:
        """Dynamically resolve async_step_dmx_light_edit_<slug> and async_step_dmx_light_remove_<slug>."""
        if item.startswith("async_step_dmx_light_edit_"):
            slug = item[len("async_step_dmx_light_edit_"):]

            async def _edit_step(user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
                return await self._show_dmx_light_form(user_input, edit_slug=slug)

            return _edit_step
        if item.startswith("async_step_dmx_light_remove_"):
            slug = item[len("async_step_dmx_light_remove_"):]

            async def _remove_step(user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
                options = getattr(self, "_merged_options", None) or dict(
                    self.config_entry.options
                )
                options[CONF_DMX_LIGHTS] = [
                    light
                    for light in options.get(CONF_DMX_LIGHTS, [])
                    if light["slug"] != slug
                ]
                self._merged_options = options
                return await self.async_step_dmx_lights_menu()

            return _remove_step
        raise AttributeError(item)
