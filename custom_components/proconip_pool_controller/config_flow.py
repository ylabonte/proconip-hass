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
    TimeoutException,
)

from .api import ProconipConnectionTester
from .const import CONF_DMX_LIGHTS, DOMAIN, LIGHT_TYPE_CHANNEL_COUNT, LOGGER
from .coordinator import ProconipPoolControllerDataUpdateCoordinator

# Labels for the DMX submenu's dynamic per-light rows. These can't live
# in translations/<lang>.json because hassfest rejects custom top-level
# keys under `options`, and the standard `options.step.<step>.menu_options`
# slot expects fixed step_id keys — ours are dynamic (one per light slug).
# Localising by hand keeps the German UI intact without depending on a
# namespace the HA strings schema doesn't recognise.
_DOCS_URL = "https://github.com/ylabonte/proconip-hass"
_DMX_MENU_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "add_light": "Add light",
        "remove_light": "Remove a light…",
        "back": "Back",
        "cancel": "Cancel",
        "edit_light_template": 'Edit "{name}" ({type} · ch {channel})',
        "list_light_template": '"{name}" ({type} · ch {channel})',
        "remove_light_template": 'Remove "{name}"',
    },
    "de": {
        "add_light": "Licht hinzufügen",
        "remove_light": "Licht entfernen…",
        "back": "Zurück",
        "cancel": "Abbrechen",
        "edit_light_template": "„{name}“ bearbeiten ({type} · Kanal {channel})",
        "list_light_template": "„{name}“ ({type} · Kanal {channel})",
        "remove_light_template": "„{name}“ entfernen",
    },
}


def _slugify_name(name: str) -> str:
    """Lowercase, alphanumeric + underscore, collapsed."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "light"


def _format_light(template: str, light: dict) -> str:
    """Apply ``template`` to a light's `{name}`, `{type}`, `{channel}` placeholders.

    Used to build the inline labels for the DMX submenu's per-light rows.
    The template comes from ``_DMX_MENU_STRINGS[lang][*_template]``; this
    function only handles substitution.
    """
    return template.format(
        name=light["name"],
        type=light["type"].upper(),
        channel=light["start_channel"],
    )


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
        existing_range = set(range(light["start_channel"], light["start_channel"] + existing_count))
        if existing_range & new_range:
            return False
    return True


def _validate_new_dmx_light(
    *,
    existing_lights: list[dict],
    name: str,
    light_type: str,
    start_channel: int,
    edit_slug: str | None = None,
) -> tuple[dict | None, dict[str, str]]:
    """Validate inputs for adding (or editing) a DMX light.

    Returns ``(light_dict, errors)``. When ``errors`` is non-empty,
    ``light_dict`` is ``None``. Shared between ConfigFlow's initial-setup
    add step and OptionsFlow's `_show_dmx_light_form` so the validation
    rules can't drift.
    """
    errors: dict[str, str] = {}
    count = LIGHT_TYPE_CHANNEL_COUNT[light_type]

    name = name.strip()
    if not name:
        # Reject blank or whitespace-only names so they never reach the
        # slugifier (which would fall back to "light") and don't end up
        # as a nameless row in the options UI.
        errors["name"] = "blank"

    if start_channel < 1 or start_channel + count - 1 > 16:
        errors["start_channel"] = "out_of_range"
    elif not _validate_no_overlap(existing_lights, start_channel, count, skip_slug=edit_slug):
        errors["start_channel"] = "overlap"

    if not errors.get("name"):
        slug = edit_slug or _slugify_name(name)
        if edit_slug is None and any(light["slug"] == slug for light in existing_lights):
            errors["name"] = "duplicate"
    else:
        slug = edit_slug or ""

    if errors:
        return None, errors

    return (
        {
            "slug": slug,
            "name": name,
            "type": light_type,
            "start_channel": start_channel,
        },
        {},
    )


class ProconipPoolControllerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for ProCon.IP Pool Controller."""

    VERSION = 1
    MINOR_VERSION = 2

    # In-flight state for the initial setup flow. All three attrs are
    # declared at class level (with immutable defaults) so mypy doesn't
    # infer the type from the first assignment in a step method. They're
    # populated in async_step_user once credentials validate, then
    # consumed by the setup_menu / setup_add_dmx_light / setup_finish chain.
    _initial_data: dict[str, Any] | None = None
    _initial_dmx_lights: list[dict[str, Any]] | None = None
    # True iff the controller's GetState response had bit 2 of SYSINFO[5]
    # set when credentials were validated. Gates whether setup_menu (with
    # its "Add a DMX light" option) is shown at all.
    _initial_dmx_enabled: bool = False

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        connection_tester = ProconipConnectionTester(self.hass)
        _errors = {}
        if user_input is not None:
            try:
                state = await connection_tester.async_test_credentials(
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
            except TimeoutException as exception:
                # Lib raises this distinctly from ProconipApiException when
                # the controller doesn't answer within the request timeout;
                # surface as a connection error, not "unknown".
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except ProconipApiException as exception:
                # Base class — also wraps aiohttp connection failures
                # (the lib re-raises ClientConnectorError as
                # ProconipApiException). Treat as a connection problem;
                # users see "Unable to connect to the server."
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except Exception as exception:  # noqa: BLE001
                # Genuinely unexpected — keep "unknown" as the catch-all
                # but log a full traceback so we can diagnose later.
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Credentials are good. Stash them and any in-flight DMX
                # list. If the controller reports DMX as enabled, route
                # to the optional setup menu (where the user can add DMX
                # lights up front). Otherwise skip straight to entry
                # creation — there's nothing to opt into.
                self._initial_data = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_URL: user_input[CONF_URL],
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                }
                self._initial_dmx_lights = []
                self._initial_dmx_enabled = state.is_dmx_enabled()
                if self._initial_dmx_enabled:
                    return await self.async_step_setup_menu()
                return await self.async_step_setup_finish()

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
            description_placeholders={"docs_url": _DOCS_URL},
            errors=_errors,
        )

    async def async_step_setup_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Optional setup menu shown after credentials validate.

        Two entries: "Add a DMX light" routes to the add form;
        "Finish setup" creates the config entry with whatever's been
        accumulated. The description carries the live light count via
        the ``{count}`` placeholder.
        """
        lights = self._initial_dmx_lights or []
        return self.async_show_menu(
            step_id="setup_menu",
            menu_options=["setup_add_dmx_light", "setup_finish"],
            description_placeholders={"count": str(len(lights))},
        )

    async def async_step_setup_add_dmx_light(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Add a single DMX light during initial setup.

        Only add (no edit/remove) — the user is creating the entry; if
        they make a mistake they can either restart the flow or fix it
        via Options after the entry is created.
        """
        lights = self._initial_dmx_lights if self._initial_dmx_lights is not None else []
        errors: dict[str, str] = {}
        if user_input is not None:
            new_light, errors = _validate_new_dmx_light(
                existing_lights=lights,
                name=user_input["name"],
                light_type=user_input["type"],
                start_channel=int(user_input["start_channel"]),
            )
            if new_light is not None:
                lights.append(new_light)
                self._initial_dmx_lights = lights
                return await self.async_step_setup_menu()

        defaults = (
            user_input
            if errors and user_input is not None
            else {"name": "", "type": "rgbw", "start_channel": 1}
        )
        return self.async_show_form(
            step_id="setup_add_dmx_light",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=defaults["name"]): str,
                    vol.Required("type", default=defaults["type"]): vol.In(
                        list(LIGHT_TYPE_CHANNEL_COUNT.keys())
                    ),
                    vol.Required("start_channel", default=defaults["start_channel"]): vol.All(
                        int, vol.Range(min=1, max=16)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_setup_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the config entry with credentials + any DMX lights added."""
        assert self._initial_data is not None  # set in async_step_user
        options: dict[str, Any] = {
            CONF_URL: self._initial_data[CONF_URL],
            CONF_USERNAME: self._initial_data[CONF_USERNAME],
            CONF_PASSWORD: self._initial_data[CONF_PASSWORD],
            CONF_SCAN_INTERVAL: self._initial_data[CONF_SCAN_INTERVAL],
        }
        if self._initial_dmx_lights:
            options[CONF_DMX_LIGHTS] = self._initial_dmx_lights
        return self.async_create_entry(
            title=self._initial_data[CONF_NAME],
            data={CONF_NAME: self._initial_data[CONF_NAME]},
            options=options,
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

    # Slug stashed by the remove-confirm step so the static
    # `async_step_dmx_light_remove_perform` knows which light to drop.
    # Declared at class level so mypy doesn't infer the type from the
    # first assignment (which sets it back to None).
    _pending_remove_slug: str | None = None

    # If the user updates Connection settings to point at a different
    # controller, that submitted credential test gives us fresh
    # GetStateData. We stash it so the DMX-menu gate reflects the new
    # controller's capabilities immediately, without waiting for a
    # config-entry reload to refresh `coordinator.data`.
    _latest_tested_state: Any = None

    def _dmx_currently_available(self) -> bool:
        """True if the controller is reporting DMX enabled *right now*.

        Preference order: (1) the freshest credentials-test state from
        this options session (wins over coordinator.data if the user
        just pointed at a different controller), (2) the live
        coordinator's last successful poll. Unhealthy coordinator (or
        no fresh test state) → False.

        Distinct from `_show_dmx_menu_entry`: the menu entry can still
        appear in orphan-management mode when DMX is currently off, but
        actions that *require* DMX (e.g. adding a new light) gate on
        this method.
        """
        if self._latest_tested_state is not None:
            return bool(self._latest_tested_state.is_dmx_enabled())
        coordinator: ProconipPoolControllerDataUpdateCoordinator | None = self.hass.data.get(
            DOMAIN, {}
        ).get(self.config_entry.entry_id)
        if coordinator is None or not coordinator.last_update_success:
            return False
        return coordinator.data.is_dmx_enabled()

    def _show_dmx_menu_entry(self) -> bool:
        """Whether the top-level menu should include the DMX-lights entry.

        True if either:

        - The entry already has configured DMX lights — even if the
          controller now reports DMX as disabled, the user needs a way
          to manage/remove these orphans via the UI.
        - OR DMX is currently available on the controller (see
          `_dmx_currently_available`).

        Unhealthy coordinator (no recent successful poll) and no
        fresh test state, with no existing lights → hide the entry.
        The user can fix the connection via the Connection settings
        entry, then re-open.
        """
        options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
        if options.get(CONF_DMX_LIGHTS):
            return True
        return self._dmx_currently_available()

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Entry point: show the top-level options menu directly.

        Credentials are already validated at entry creation; users only
        walk through the connection-settings form when they explicitly
        pick it. The DMX-lights entry is gated on whether the controller
        actually supports DMX (see `_show_dmx_menu_entry`).
        """
        menu_options = ["connection"]
        if self._show_dmx_menu_entry():
            menu_options.append("dmx_lights_menu")
        menu_options.append("save_and_finish")
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Update connection settings (URL / credentials / scan interval).

        Reached from the top-level menu (`async_step_init`). On
        successful credential validation, merges the new values into
        ``self._merged_options`` and bounces back to the menu.
        """
        connection_tester = ProconipConnectionTester(self.hass)
        _errors: dict[str, str] = {}
        if user_input is not None:
            try:
                state = await connection_tester.async_test_credentials(
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
            except TimeoutException as exception:
                # Lib raises this distinctly from ProconipApiException when
                # the controller doesn't answer within the request timeout;
                # surface as a connection error, not "unknown".
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except ProconipApiException as exception:
                # Base class — also wraps aiohttp connection failures
                # (the lib re-raises ClientConnectorError as
                # ProconipApiException). Treat as a connection problem;
                # users see "Unable to connect to the server."
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except Exception as exception:  # noqa: BLE001
                # Genuinely unexpected — keep "unknown" as the catch-all
                # but log a full traceback so we can diagnose later.
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                # Stash the fresh state so the DMX-menu gate in
                # _show_dmx_menu_entry reflects the newly-pointed-at
                # controller's capabilities immediately (otherwise the
                # gate keeps reading the previous coordinator.data until
                # the entry is reloaded).
                self._latest_tested_state = state
                base = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
                new_options = {**base, **user_input}
                self._merged_options = new_options
                return await self.async_step_init()

        # Prefer pending values from `_merged_options` (set above on a
        # successful credential test) so re-opening this step after a
        # menu bounce shows the user's just-entered URL/credentials,
        # not the stale ones persisted in `config_entry.options`.
        current = getattr(self, "_merged_options", None) or self.config_entry.options
        return self.async_show_form(
            step_id="connection",
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

    async def async_step_save_and_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Save all accumulated options and finish the flow."""
        options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
        return self.async_create_entry(data=options)

    async def _dmx_menu_strings(self) -> dict[str, str]:
        """Return the active language's DMX-submenu labels.

        We use the dict-of-dicts ``menu_options`` variant for the DMX
        submenu so that the per-light rows can carry user-chosen slugs in
        their step_ids — but that variant bypasses HA's automatic label
        translation, and hassfest rejects custom translation keys under
        ``options``. So the labels live in ``_DMX_MENU_STRINGS`` instead;
        templates with placeholders like ``{name}`` are formatted by
        ``_format_light``.
        """
        return _DMX_MENU_STRINGS.get(self.hass.config.language, _DMX_MENU_STRINGS["en"])

    async def async_step_dmx_lights_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show the DMX lights management menu."""
        t = await self._dmx_menu_strings()
        options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
        lights: list[dict] = list(options.get(CONF_DMX_LIGHTS, []))
        menu: dict[str, str] = {}
        # `Add light` only when DMX is currently available on the
        # controller — when this submenu is reachable purely because
        # orphan lights still exist (DMX got disabled after configuring
        # them), the user should be able to manage/remove the orphans
        # without piling on more nonfunctional entries.
        if self._dmx_currently_available():
            menu["dmx_light_add"] = t.get("add_light", "Add light")
        edit_template = t.get("edit_light_template", 'Edit "{name}" ({type} · ch {channel})')
        for light in lights:
            menu[f"dmx_light_edit_{light['slug']}"] = _format_light(edit_template, light)
        if lights:
            menu["dmx_lights_remove_menu"] = t.get("remove_light", "Remove a light…")
        # "Back" returns to the top-level options menu (now async_step_init).
        menu["init"] = t.get("back", "Back")
        return self.async_show_menu(step_id="dmx_lights_menu", menu_options=menu)

    async def async_step_dmx_lights_remove_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """List existing lights and let the user pick one to delete.

        Tapping a light routes to ``dmx_light_remove_confirm_<slug>``
        (resolved dynamically by ``__getattr__``), which shows a
        Remove/Cancel menu before any state mutation.
        """
        t = await self._dmx_menu_strings()
        options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
        lights: list[dict] = list(options.get(CONF_DMX_LIGHTS, []))
        menu: dict[str, str] = {}
        list_template = t.get("list_light_template", '"{name}" ({type} · ch {channel})')
        for light in lights:
            menu[f"dmx_light_remove_confirm_{light['slug']}"] = _format_light(list_template, light)
        menu["dmx_lights_menu"] = t.get("back", "Back")
        return self.async_show_menu(step_id="dmx_lights_remove_menu", menu_options=menu)

    async def async_step_dmx_light_remove_perform(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Delete the light tagged by `_pending_remove_slug` and return to the lights menu.

        The slug is stashed on `self` by the confirm step so this static
        handler doesn't need its own dynamic-dispatch entry in
        ``__getattr__``.
        """
        slug = getattr(self, "_pending_remove_slug", None)
        if slug is not None:
            options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
            options[CONF_DMX_LIGHTS] = [
                light for light in options.get(CONF_DMX_LIGHTS, []) if light["slug"] != slug
            ]
            self._merged_options = options
            self._pending_remove_slug = None
        return await self.async_step_dmx_lights_menu()

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
        options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
        lights: list[dict] = list(options.get(CONF_DMX_LIGHTS, []))
        existing = next((light for light in lights if light["slug"] == edit_slug), None)

        errors: dict[str, str] = {}
        if user_input is not None:
            new_light, errors = _validate_new_dmx_light(
                existing_lights=lights,
                name=user_input["name"],
                light_type=user_input["type"],
                start_channel=int(user_input["start_channel"]),
                edit_slug=edit_slug,
            )
            if new_light is not None:
                if existing is not None:
                    lights = [
                        new_light if light["slug"] == edit_slug else light for light in lights
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
                    vol.Required("start_channel", default=defaults["start_channel"]): vol.All(
                        int, vol.Range(min=1, max=16)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_dmx_light_edit(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Placeholder — edit/remove are dispatched dynamically via __getattr__."""
        raise NotImplementedError("Edit/Remove are dispatched dynamically — see __getattr__")

    def __getattr__(self, item: str) -> Any:
        """Dynamically resolve per-slug step methods.

        Two prefixes are routed:

        - ``async_step_dmx_light_edit_<slug>`` — opens the edit form for
          the given light (closure captures ``slug``).
        - ``async_step_dmx_light_remove_confirm_<slug>`` — stashes the
          slug on ``self._pending_remove_slug`` and shows a Remove/Cancel
          menu. The actual deletion is done by the static
          ``async_step_dmx_light_remove_perform`` step (no per-slug
          dispatch needed for the perform side).
        """
        if item.startswith("async_step_dmx_light_edit_"):
            slug = item[len("async_step_dmx_light_edit_") :]

            async def _edit_step(
                user_input: dict[str, Any] | None = None,
            ) -> config_entries.ConfigFlowResult:
                return await self._show_dmx_light_form(user_input, edit_slug=slug)

            return _edit_step
        if item.startswith("async_step_dmx_light_remove_confirm_"):
            slug = item[len("async_step_dmx_light_remove_confirm_") :]

            async def _confirm_step(
                user_input: dict[str, Any] | None = None,
            ) -> config_entries.ConfigFlowResult:
                self._pending_remove_slug = slug
                options = getattr(self, "_merged_options", None) or dict(self.config_entry.options)
                light = next(
                    (
                        candidate
                        for candidate in options.get(CONF_DMX_LIGHTS, [])
                        if candidate["slug"] == slug
                    ),
                    None,
                )
                name = light["name"] if light else slug
                t = await self._dmx_menu_strings()
                remove_template = t.get("remove_light_template", 'Remove "{name}"')
                return self.async_show_menu(
                    step_id=f"dmx_light_remove_confirm_{slug}",
                    menu_options={
                        "dmx_light_remove_perform": remove_template.format(name=name),
                        "dmx_lights_remove_menu": t.get("cancel", "Cancel"),
                    },
                )

            return _confirm_step
        raise AttributeError(item)
