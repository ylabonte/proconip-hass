"""aiohttp web app implementing the four ProCon.IP HTTP endpoints.

Routes mirror the real controller's contract closely enough that any
`proconip` client function works against the mock without modification:

- `GET /GetState.csv` — drifted sensor values + current relay state, CSV body
- `GET /GetDmx.csv` — current 16-channel DMX state, CSV body
- `POST /usrcfg.cgi` — relay (`ENA=...&MANUAL=1`) and DMX (`TYPE=...&CH1_8=...`)
  writes; returns "OK"
- `GET /Command.htm?MAN_DOSAGE=t,s` — manual dosage trigger; returns "OK"

A single basic-auth middleware guards all routes. Bad creds yield 401 with
a `WWW-Authenticate` header so real clients raise `BadCredentialsException`
on the failure path too.
"""

import logging
from base64 import b64encode
from collections.abc import Awaitable, Callable
from typing import Any

from aiohttp import hdrs, web

from .csv_renderer import render_get_dmx, render_get_state
from .state import MockState

_LOG = logging.getLogger("proconip_mock")

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]

STATE_KEY: web.AppKey[MockState] = web.AppKey("state", MockState)


def _build_auth_middleware(username: str, password: str) -> Any:
    expected = "Basic " + b64encode(f"{username}:{password}".encode()).decode()

    @web.middleware
    async def auth(request: web.Request, handler: Handler) -> web.StreamResponse:
        if request.headers.get(hdrs.AUTHORIZATION) != expected:
            return web.Response(
                status=401,
                headers={"WWW-Authenticate": 'Basic realm="ProCon.IP"'},
                text="Unauthorized",
            )
        return await handler(request)

    return auth


async def _get_state(request: web.Request) -> web.Response:
    state = request.app[STATE_KEY]
    return web.Response(text=render_get_state(state), content_type="text/csv")


async def _get_dmx(request: web.Request) -> web.Response:
    state = request.app[STATE_KEY]
    return web.Response(text=render_get_dmx(state), content_type="text/csv")


async def _usrcfg(request: web.Request) -> web.Response:
    state = request.app[STATE_KEY]
    # aiohttp's request.post() handles `application/x-www-form-urlencoded`
    # to spec (percent-decoding, `+` → space, repeated keys), matching what
    # a real controller's form parser would do.
    fields = await request.post()

    # No raw form value is ever passed to a log call. Failures are logged as
    # the exception class name, successes log values that have already passed
    # through int()/== — CodeQL recognizes both as sanitization boundaries
    # for `py/log-injection`.
    if "ENA" in fields:
        try:
            enable_str, on_str = str(fields["ENA"]).split(",", 1)
            enable_mask = int(enable_str)
            on_mask = int(on_str)
        except (ValueError, KeyError) as exc:
            _LOG.warning("invalid ENA payload (%s)", type(exc).__name__)
            return web.Response(status=400, text="Invalid ENA payload")
        state.apply_ena(enable_mask=enable_mask, on_mask=on_mask)
        manual = str(fields.get("MANUAL", "")) == "1"
        _LOG.info("relay update: ENA=%d,%d MANUAL=%s", enable_mask, on_mask, manual)
        return web.Response(text="OK")

    if "CH1_8" in fields and "CH9_16" in fields:
        try:
            ch_low = [int(v) for v in str(fields["CH1_8"]).split(",")]
            ch_high = [int(v) for v in str(fields["CH9_16"]).split(",")]
            state.apply_dmx(channels_1_8=ch_low, channels_9_16=ch_high)
        except ValueError as exc:
            _LOG.warning("invalid DMX payload (%s)", type(exc).__name__)
            return web.Response(status=400, text="Invalid DMX payload")
        _LOG.info("dmx update: %s", state.dmx)
        return web.Response(text="OK")

    return web.Response(status=400, text="Unrecognized usrcfg.cgi payload")


async def _command(request: web.Request) -> web.Response:
    dosage = request.query.get("MAN_DOSAGE")
    if dosage is None:
        return web.Response(status=400, text="Missing MAN_DOSAGE query parameter")
    try:
        target_str, duration_str = dosage.split(",", 1)
        target = int(target_str)
        duration = int(duration_str)
    except ValueError as exc:
        _LOG.warning("invalid MAN_DOSAGE (%s)", type(exc).__name__)
        return web.Response(status=400, text="Invalid MAN_DOSAGE payload")
    _LOG.info("manual dosage: target=%d duration=%d", target, duration)
    return web.Response(text="OK")


def create_app(
    state: MockState, *, username: str = "admin", password: str = "admin"
) -> web.Application:
    """Build the aiohttp app, wired to the given state and credentials."""
    app = web.Application(middlewares=[_build_auth_middleware(username, password)])
    app[STATE_KEY] = state
    app.router.add_get("/GetState.csv", _get_state)
    app.router.add_get("/GetDmx.csv", _get_dmx)
    app.router.add_post("/usrcfg.cgi", _usrcfg)
    app.router.add_get("/Command.htm", _command)
    return app


__all__ = ["create_app"]
