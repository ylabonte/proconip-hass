"""Run the mock controller as ``python -m tools.proconip_mock``.

Reads bind host, port, credentials, and feature flags from environment
variables, constructs the aiohttp app, and serves it forever.

Default bind is **127.0.0.1** — the mock listens only on the loopback
interface, so the default `admin`/`admin` credentials aren't reachable from
the LAN. Environments that need external access (devcontainer port
forwarding, Codespaces) override this to `0.0.0.0` via
``PROCONIP_MOCK_HOST`` in ``.devcontainer/devcontainer.json``.

Feature flags map onto SYSINFO[5] (the controller's ``config_other_enable``
bitfield) so client-side checks like ``is_dmx_enabled()`` see the intended
state without anyone editing ``tests/fixtures/get_state.csv``:

- ``PROCONIP_MOCK_CONFIG_OTHER_ENABLE`` — raw integer override. See the bit
  layout in `tools.proconip_mock.state.MockState`.
- ``PROCONIP_MOCK_DMX`` — set to ``1`` as a shortcut for "turn on every DMX-
  related bit" (bit 2 + bit 8 = 260). Useful for testing DMX-gated client
  code without knowing the bit numbers. If both vars are set, the two
  values are OR'd together.
"""

import logging
import os

from aiohttp import web

from .server import create_app
from .state import MockState

# Shortcut mask — bit 2 (DMX) | bit 8 (DMX extension).
_DMX_SHORTCUT_MASK = 4 | 256


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_truthy(name: str) -> bool:
    """Treat any value other than empty, "0", "false", "no" as truthy."""
    raw = os.environ.get(name)
    if raw is None:
        return False
    return raw.strip().lower() not in ("", "0", "false", "no")


def _resolved_config_other_enable() -> int:
    mask = int(_env("PROCONIP_MOCK_CONFIG_OTHER_ENABLE", "0"))
    if _env_truthy("PROCONIP_MOCK_DMX"):
        mask |= _DMX_SHORTCUT_MASK
    return mask


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    host = _env("PROCONIP_MOCK_HOST", "127.0.0.1")
    port = int(_env("PROCONIP_MOCK_PORT", "8080"))
    username = _env("PROCONIP_MOCK_USER", "admin")
    password = _env("PROCONIP_MOCK_PASS", "admin")
    config_other_enable = _resolved_config_other_enable()

    state = MockState(config_other_enable=config_other_enable)
    app = create_app(state, username=username, password=password)
    # When binding to an unspecified address (`0.0.0.0` / `::`), the literal
    # URL is not connectable from a client; substitute `localhost` so the log
    # line shows something a developer can paste into a browser or curl.
    display_host = "localhost" if host in ("0.0.0.0", "::") else host
    logging.getLogger("proconip_mock").info(
        "ProCon.IP mock listening on http://%s:%d (bind=%s, user=%s, config_other_enable=%d)",
        display_host,
        port,
        host,
        username,
        config_other_enable,
    )
    web.run_app(app, host=host, port=port, print=None)


if __name__ == "__main__":
    main()
