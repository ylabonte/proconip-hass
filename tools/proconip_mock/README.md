# `tools/proconip_mock` — local ProCon.IP mock

A small `aiohttp` server that mimics the four endpoints of a real ProCon.IP
pool controller closely enough that any `proconip` client function works
against it without modification. Used for local development, manual smoke
testing, and integration tests in this repo. **Not** shipped to PyPI.

## Run it

From the repo root, with the dev extras installed:

```bash
pip install -e ".[dev,test,docs]"
python -m tools.proconip_mock
```

The server logs `listening on http://localhost:8080 (bind=127.0.0.1, …)`
and stays up. Stop with Ctrl-C.

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `PROCONIP_MOCK_HOST` | `127.0.0.1` | Bind host. Loopback-only by default; the devcontainer overrides this to `0.0.0.0` so the forwarded port is reachable from outside the container. |
| `PROCONIP_MOCK_PORT` | `8080` | Bind port |
| `PROCONIP_MOCK_USER` | `admin` | HTTP basic-auth user |
| `PROCONIP_MOCK_PASS` | `admin` | HTTP basic-auth password |
| `PROCONIP_MOCK_DMX` | (unset) | Set to `1` to turn on every DMX-related bit (`config_other_enable = 4 \| 256 = 260`). Lets DMX-gated client code (`GetStateData.is_dmx_enabled()`, `is_dmx_extension_enabled()`) take the enabled branch without hand-picking bits. |
| `PROCONIP_MOCK_CONFIG_OTHER_ENABLE` | `0` | Raw integer override for SYSINFO[5] (the `config_other_enable` bitfield). Bit layout is documented on `MockState` in `tools/proconip_mock/state.py`. If both this and `PROCONIP_MOCK_DMX` are set, their values are OR'd together. |

## What it does

- **`GET /GetState.csv`** — serves the structural template from
  `tests/fixtures/get_state.csv` with row 6 (live values) freshly computed
  from `MockState` and the drift functions in `drift.py`. pH, redox, CPU
  temperature, and the column-8 "Pumpe" temperature oscillate slowly within
  realistic pool ranges (WHO band for pH/redox; idle MCU temps for the
  controller; pool-water range for the pump sensor). The clock column
  reflects the host's current local time.
- **`GET /GetDmx.csv`** — current 16-channel DMX state.
- **`POST /usrcfg.cgi`** — accepts both relay (`ENA=...&MANUAL=1`) and DMX
  (`TYPE=...&CH1_8=...&CH9_16=...`) payloads. State persists in memory until
  the process exits; a follow-up `GET /GetState.csv` reflects the change.
- **`GET /Command.htm?MAN_DOSAGE=t,s`** — accepts and logs manual dosage
  commands. Canister levels are not decremented (out of scope).

Bad credentials yield 401 with `WWW-Authenticate: Basic realm="ProCon.IP"`,
exercising the `BadCredentialsException` path in `proconip.api`.

## Try it

```bash
# Drift visible across two reads
curl -u admin:admin http://localhost:8080/GetState.csv | tail -1
sleep 60
curl -u admin:admin http://localhost:8080/GetState.csv | tail -1

# Manual dosage (60 s of chlorine)
curl -u admin:admin "http://localhost:8080/Command.htm?MAN_DOSAGE=0,60"
```

Or point a real `proconip` client at it:

```python
import aiohttp
from proconip import ConfigObject, async_get_state

async def main() -> None:
    config = ConfigObject("http://localhost:8080", "admin", "admin")
    async with aiohttp.ClientSession() as session:
        state = await async_get_state(session, config)
        print(f"pH: {state.ph_electrode.display_value}")
        print(f"Redox: {state.redox_electrode.display_value}")
```

## DMX

The mock's DMX endpoints (`POST /usrcfg.cgi` with `CH1_8`/`CH9_16`, `GET
/GetDmx.csv`) work in any configuration. Some client code, however, only
calls them after checking `GetStateData.is_dmx_enabled()`; the fixture's
default `config_other_enable = 0` makes that check return `False` and
those code paths never fire. Flip the DMX bits at startup to unblock
them:

```bash
PROCONIP_MOCK_DMX=1 python -m tools.proconip_mock

# Set DMX channels 1–8 — channel 1 to 255, the rest off
curl -u admin:admin -X POST \
     -d 'CH1_8=255,0,0,0,0,0,0,0&CH9_16=0,0,0,0,0,0,0,0' \
     http://localhost:8080/usrcfg.cgi

# Read them back
curl -u admin:admin http://localhost:8080/GetDmx.csv
```

The `.devcontainer/devcontainer.json` already sets `PROCONIP_MOCK_DMX=1`
in `remoteEnv`, so containers default to DMX-on for development.
