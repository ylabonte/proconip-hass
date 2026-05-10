# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Home Assistant **custom integration** (HACS-distributed) for the [ProCon.IP pool controller](https://www.pooldigital.de). The integration code lives in `custom_components/proconip_pool_controller/` and follows the [@ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint) pattern.

All HTTP/CSV parsing and relay/dosage commands are delegated to the **`proconip` PyPI package** (declared in `manifest.json` requirements as `proconip>=1.3.0`). When a question is about *what data exists* or *how a call works*, the answer is in that library, not here:

- Source: https://github.com/ylabonte/proconip-pypi
- Docs: https://ylabonte.github.io/proconip-pypi/

This integration is a thin Home Assistant adapter on top of that library. Prefer extending the library when adding new device-side behavior, then expose it here.

## Common commands

All scripts cd into the repo root themselves; run them from anywhere.

| Command | What it does |
|---|---|
| `scripts/setup` | `pip install -r requirements.txt` (HA core, ruff, colorlog, proconip lib) |
| `scripts/develop` | Boots a local Home Assistant on port 8123 with `custom_components/` on `PYTHONPATH` and `config/configuration.yaml`. Use this to manually verify changes. |
| `scripts/lint` | `black --check --verbose custom_components/`. CI runs the same via `psf/black@stable`. |
| `black custom_components/` | Auto-format (the dev container's format-on-save does this too). |

There is **no test suite** and no `pytest` configured. Verification is: `scripts/lint` + boot via `scripts/develop` + manually exercise the integration in the HA UI.

CI also runs **hassfest** (`home-assistant/actions/hassfest`) and **HACS validation** (`hacs/action`) on push/PR — if you change `manifest.json`, `hacs.json`, or platform structure, expect those to enforce conformance.

## Architecture

Data flow for one config entry (one ProCon.IP device):

```
proconip lib (GetState/RelaySwitch/DosageControl)
        ↑
api.py (ProconipApiClient)            ← thin wrapper, owns aiohttp session
        ↑
coordinator.py (DataUpdateCoordinator) ← single poll → GetStateData
        ↑
entity.py (ProconipPoolControllerEntity) ← CoordinatorEntity base, sets DeviceInfo
        ↑
binary_sensor.py / sensor.py / switch.py / select.py / number.py
```

Key facts that aren't obvious from a single file:

- **One coordinator per config entry**, stored at `hass.data[DOMAIN][entry.entry_id]`. All platforms read from it. There is no per-entity polling.
- **Multi-instance is supported.** Every entity's `unique_id` *must* be suffixed with `instance_id` (= `entry.entry_id`) — see how `entity.py` re-prefixes `_attr_unique_id` in `__init__`. Breaking this convention will collide entities when a user runs more than one ProCon.IP (e.g. pool + jacuzzi).
- **Config entry layout (v1.2):** `entry.data` holds only `CONF_NAME`. `entry.options` holds `CONF_URL`, `CONF_USERNAME`, `CONF_PASSWORD`, `CONF_SCAN_INTERVAL`. `async_migrate_entry` in `__init__.py` rewrites older entries that mixed these. Don't read connection settings from `entry.data` — always use `entry.options`.
- **Dosage relays are special.** Three relay IDs (chlorine / pH-minus / pH-plus) are derived from `GetStateData` each poll and tracked in `coordinator._active_dosage_relays`. They get:
  - hidden by default in the standard relay switch/select/sensor entities (see `is_dosage_relay()` checks),
  - replaced by a `NumberEntity` (`number.py` `ProconipPoolControllerDosageRelayTimer`) that triggers a timed dosage via `DosageControl` and runs a local async countdown for UI feedback,
  - allowed only `["auto", "off"]` in the select dropdown when the dosage is *active* (the device rejects permanent-on for an active dosage relay — see README "Cannot permanently switch on a dosage relay").
- **Relay count is dynamic.** 8 by default, 16 if `coordinator.data.is_relay_extension_enabled()`. Every platform that creates per-relay entities recomputes this — keep that pattern.
- **Sensor visibility uses `_attr_entity_registry_visible_default`** to hide unconfigured channels (e.g. temp slots whose name is `"n.a."`). Don't drop these entities; users may name them later and expect them to appear.

### Files to be aware of

- `const.py` — `DOMAIN`, `NAME`, `VERSION` (kept in sync with `manifest.json` `version`), `LOGGER`, `ATTRIBUTION`.
- `translations/en.json`, `translations/de.json` — config-flow strings. Keep both in sync when changing the flow.
- **`light.py` is dormant scaffold code, not wired up.** It is *not* in the `PLATFORMS` list in `__init__.py` and currently won't import (it references `GET_STATE_DATA` / `GET_DMX_DATA` symbols that don't exist in `coordinator.py`, and has a stray `from sqlalchemy import null`). Treat it as a TODO for future DMX-light support, not as a working reference. If touching it, fix the imports and add `Platform.LIGHT` to `PLATFORMS`.

## Coding conventions

- **Format with Black.** That is the *only* enforced style. `requirements.txt` lists `ruff` but nothing in this repo runs it — don't introduce ruff-specific rules without wiring them up.
- **Use keyword arguments everywhere** when calling HA / library functions. The existing code is consistent about this (`coordinator=coordinator`, `relay_id=...`, `entry=entry`) — match it.
- **Use `from __future__ import annotations`** at the top of new modules (every existing module does).
- **Logging** goes through `LOGGER` from `const.py` (already a `logging.Logger` named after the package). Don't create new loggers.
- Docstrings on every public class / async function — short one-liners are fine; that is the pattern in this codebase.

## Release / version bumping

Releases are cut by **publishing a GitHub release**:

1. `release.yml` triggers on `release: published`.
2. It rewrites `custom_components/proconip_pool_controller/manifest.json` `version` to the release tag using `yq`.
3. It zips the integration directory and attaches `proconip_pool_controller.zip` to the release for HACS.

So: don't hand-edit `manifest.json` `version` for a release — just create the GitHub release with the right tag. **Do** keep `const.py` `VERSION` and `manifest.json` `version` in sync for development (the README changelog references this) and bump `hacs.json` `homeassistant` minimum if you start using newer HA APIs. Current minimum: **HA 2024.2.1**, Python **3.12** (see devcontainer image `python:dev-3.12`).

## Commit / PR guidance

- Branch from `main`, PR back to `main`. Lint must pass (`scripts/lint`); hassfest + HACS validation run automatically.
- Commit style in `git log` is short imperative subjects ("Update actions versions", "Bump actions/setup-python ..."). Match that — no scope prefixes, no Conventional Commits.
- The README has a Changelog section. For user-visible changes (new entities, breaking entity-id changes, HA min-version bumps), add an entry there in addition to the release notes — note that adding/removing entities means *users have to clean up old ones manually* (see the v1.2.0 warning); call this out in the changelog when it happens.
