# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Home Assistant **custom integration** (HACS-distributed) for the [ProCon.IP pool controller](https://www.pooldigital.de). The integration code lives in `custom_components/proconip_pool_controller/` and follows the [@ludeeus/integration_blueprint](https://github.com/ludeeus/integration_blueprint) pattern.

All HTTP/CSV parsing and relay/dosage commands are delegated to the **`proconip` PyPI package** (declared in `manifest.json` requirements as `proconip>=2.1.0`). When a question is about *what data exists* or *how a call works*, the answer is in that library, not here:

- Source: https://github.com/ylabonte/proconip-pypi
- Docs: https://ylabonte.github.io/proconip-pypi/

This integration is a thin Home Assistant adapter on top of that library. Prefer extending the library when adding new device-side behavior, then expose it here.

## Common commands

All scripts cd into the repo root themselves; run them from anywhere.

| Command | What it does |
|---|---|
| `scripts/setup` | Creates `.venv` (Python ≥ 3.13), `pip install -e ".[dev,test]"` + `colorlog`, then runs `scripts/install-ha-deps.py` to pre-install HA's eager-import deps (parsed from each `manifest.json`). |
| `scripts/install-ha-deps.py` | Walks HA's bundled `components/<name>/manifest.json` to install the pip packages our slim config + HA's `_base_components()` need. The source of truth is HA's manifests — *do not hand-curate a list of pip packages here.* |
| `scripts/develop` | Boots a local Home Assistant on port 8123 with `--skip-pip` (everything was pre-installed by setup). Use this to manually verify changes. |
| `scripts/lint` | Ruff lint and format, mypy type-check. |
| `scripts/mock-server` | Foreground ProCon.IP mock for manual smoke-testing (logs to stdout, defaults to `127.0.0.1:8080` admin/admin). The devcontainer auto-starts a *backgrounded* mock on `0.0.0.0:8080` via `.devcontainer/start-mock.sh` (wired to `postStartCommand`). |
| `scripts/dev-reset` | Wipes `config/` (except `configuration.yaml`) to re-onboard HA from scratch. |

**If you add an integration to `config/configuration.yaml`,** also add it to `CONFIG_INTEGRATIONS` in `scripts/install-ha-deps.py` so its manifest requirements get pre-installed. Same goes for `BASE_COMPONENTS` if HA Core changes `_base_components()`. Don't `default_config:` the dev config — that loads ~30 integrations whose lazy install races at boot and lands HA in recovery mode.

**`tools/proconip_mock/` and `.devcontainer/start-mock.sh` are vendored from `ylabonte/proconip-pypi`** (canonical home, alongside the library). When the mock needs changes, do them in `proconip-pypi` first and re-sync here — don't edit in place. Useful diff:
```bash
diff -rq tools/proconip_mock/ ../proconip-pypi/tools/proconip_mock/
```

Verification is: `pytest` (`scripts/lint` runs ruff + mypy) + boot via `scripts/develop` + manually exercise the integration in the HA UI. There is a real pytest suite — see `tests/` and `pyproject.toml`'s `[tool.pytest.ini_options]`.

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

- **Format and lint with ruff. Type-check with mypy --strict.** Run via `scripts/lint`.
- **Use keyword arguments everywhere** when calling HA / library functions. The existing code is consistent about this (`coordinator=coordinator`, `relay_id=...`, `entry=entry`) — match it.
- **Use `from __future__ import annotations`** at the top of new modules (every existing module does).
- **Logging** goes through `LOGGER` from `const.py` (already a `logging.Logger` named after the package). Don't create new loggers.
- Docstrings on every public class / async function — short one-liners are fine; that is the pattern in this codebase.

## Release / version bumping

Releases are fully automated by [release-please](https://github.com/googleapis/release-please) — maintainers don't tag, draft notes, or zip by hand. Conventional Commits on `main` decide the next version and what appears in the changelog.

**Flow:**

1. Land PRs on `main` with Conventional Commit titles (`feat:`, `fix:`, `chore:`, etc. — see the table below). Squash-merge is the default, so the PR title becomes the commit subject.
2. `.github/workflows/release.yml` runs on every push to `main`. It invokes `googleapis/release-please-action@v5`, which:
    - Scans new commits since the last release.
    - If any new `feat`/`fix`/`perf`/`revert` commits exist, opens or updates a **"chore(main): release X.Y.Z" PR** that bumps `.release-please-manifest.json`, `custom_components/proconip_pool_controller/manifest.json:version` (via `extra-files: json`), and `custom_components/proconip_pool_controller/const.py:VERSION` (via `extra-files: generic` — that's what the `# x-release-please-version` comment marker is for; do not remove it), and prepends a changelog entry to `CHANGELOG.md`.
3. Review the auto-PR. CI runs against it (App-token-authored, so downstream workflows fire). Merge it.
4. release-please cuts the `vX.Y.Z` tag and creates the GitHub release with the auto-generated notes.
5. `.github/workflows/hacs-release.yml` triggers on `release: published`, re-runs `test` + `lint` against the released tag, zips `custom_components/proconip_pool_controller/`, and attaches `proconip_pool_controller.zip` to the release. HACS picks it up on next poll.

**Don't:** hand-edit `manifest.json:version` or `const.py:VERSION`. Both are owned by release-please's `extra-files` config. The marker comment on the `VERSION` line must stay verbatim.

**Do:** bump `hacs.json:homeassistant` minimum if you start using newer HA APIs. Current minimum: **HA 2024.2.1**, Python **3.13+** (see devcontainer image `python:dev-3.14` and `pyproject.toml:requires-python`).

### Conventional Commits — when to bump, when to be silent

**Default behavior on every code-changing task:** at commit-write time, decide the conventional-commit `type` from the table below. **If the type would trigger a release entry, ask the user to confirm subject + type before committing.** For silent types (`ci`/`chore`/`test`/etc.) commit without asking.

| Type | Trigger release? | Visible in CHANGELOG? | Use when |
|---|---|---|---|
| `feat` | minor bump | yes (Features) | new entity, new config option, new feature |
| `feat!` or `BREAKING CHANGE:` footer | major bump | yes (Features + breaking note) | renamed entity_id, removed entity, raised HA minimum version |
| `fix` | patch bump | yes (Bug Fixes) | bugfix that users would notice |
| `perf` | patch bump | yes (Performance) | perf change without behaviour change |
| `deps` | none | yes (Dependencies) | proconip / HA / other runtime dep bumps |
| `docs` | none | yes (Documentation) | README/CONTRIBUTING/CLAUDE.md changes |
| `refactor` | none | hidden | internal rewrites with no behaviour change |
| `test` | none | hidden | adding/changing tests only |
| `build` | none | hidden | build system tweaks |
| `ci` | none | hidden | anything under `.github/` or release workflows |
| `chore` | none | hidden | catch-all: lockfile bumps, formatting, devcontainer/scripts/tools |

**Silent-by-default paths** (commit with `ci:` / `chore:` / `test:` / `docs:` as appropriate, no question asked):

- `.github/`, `.devcontainer/`, `.vscode/`
- `scripts/`, `tools/`
- `tests/`, `pyproject.toml` test/lint config, `.pre-commit-config.yaml`
- `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, comments, docstrings
- Pure formatting, type-only refactors

**Always ask before committing** when the change touches:

- `custom_components/proconip_pool_controller/**` non-trivially (any new/changed/removed entity, config-flow change, user-visible string, behaviour change)
- `manifest.json` (other than the release-please-owned `version` field)
- `translations/*.json` for user-visible labels
- Dependency version constraints

**Mixed-change PR rule:** split into separate commits with the right types. Don't describe a CI tweak in a `feat:` commit — release-please would file the wrong section.

**When in doubt, ask the user.** Never silently choose `chore:` for a borderline case.

### Post-release follow-up: HACS default-list submission

After publishing the v2.0.0 GitHub release and watching CI go green,
open a PR against [hacs/default](https://github.com/hacs/default) adding
`ylabonte/proconip-hass` alphabetically to the `integration` file. The
brand assets at `home-assistant/brands/custom_integrations/proconip_pool_controller/`
are already in place. PR must be opened from a personal account, not an org.

**Once the hacs/default PR is merged** (not before — the badge would be
a false claim and the install steps wouldn't work until the listing
propagates), apply the README rewrite staged in
[`docs/HACS-DEFAULT-README-snippet.md`](docs/HACS-DEFAULT-README-snippet.md).
That file contains the exact patch (Install section + badge + link
refs) plus a step to delete itself. Suggested PR title:
`docs: remove custom-repository install steps now that we're in HACS default`.

## Commit / PR guidance

- Branch from `main`, PR back to `main`. Lint must pass (`scripts/lint`); hassfest + HACS validation run automatically.
- **Commit titles must be Conventional Commits** — release-please reads them to decide version bumps and changelog placement. See the table in the **Release / version bumping** section above for the type → behaviour mapping.
- Squash-merge is the default: the PR title is the resulting commit subject on `main`. Title your PR like the commit you want release-please to record.
- The `CHANGELOG.md` is owned by release-please. Don't edit historical entries (anything below `## [Unreleased]`); new entries are prepended automatically when the release PR opens.
