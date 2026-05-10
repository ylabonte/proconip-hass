# Major refactor + DMX support — design

**Date:** 2026-05-10
**Target version:** 2.0.0
**Author:** Yannic Labonte (with Claude as collaborator)

## Context

The `proconip-hass` integration has accumulated drift since v1.2.0 (Feb 2024):

- A latent bug in `OptionsFlow` (`config_flow.py:139`) crashes on modern Home Assistant because HA's `OptionsFlow.config_entry` became a read-only property. Reported as issues #70 and #71 — same root cause, same stack, same fix.
- The pinned `proconip` library is `>=1.3.0`. Today (2026-05-10) the library shipped v2.0.0 — major overhaul, Python 3.13 minimum (matching HA Core 2026.5), top-level imports, real DMX read+write surface, the `Relay` calibration bug fix.
- `light.py` is dormant scaffold code that was never wired up: it imports symbols (`GET_STATE_DATA`, `GET_DMX_DATA`) that don't exist in `coordinator.py`, has a stray `from sqlalchemy import null`, and isn't registered in `PLATFORMS` in `__init__.py`. DMX feature request #61 has been open since May 2024.
- Repo tooling lags the library: `black`-only lint, no tests, no `pyproject.toml`, no Dependabot, action versions are stale.

This design covers the version 2.0.0 PR: bug fix, library bump, tooling overhaul mirroring `proconip-pypi`, HA-API modernization, and DMX support. Issue #61 is also resolved.

## Goals

- Resolve issues #70, #71 (regression in modern HA's `OptionsFlow`).
- Adopt `proconip` v2.0.0 surface.
- Bring repo tooling to parity with the library where it makes sense for an integration: `pyproject.toml` for tool config, `ruff` + `mypy --strict`, `pytest` + `pytest-homeassistant-custom-component` + `aioresponses` + `pytest-cov` with an 80% gate, refreshed CI workflows, Dependabot, pre-commit, `CHANGELOG.md`.
- Resolve #61 with a real DMX implementation: user-configurable channel-to-light mapping, `LightEntity` subclasses for dimmer / RGB / RGBW, race-resilient write path.
- Prepare the repo for HACS default-list submission.

## Non-goals

- PyPI publication. The integration is distributed by HACS as a directory zip via the existing `release.yml`. There is no `[build-system]` packaging surface in `pyproject.toml`.
- A docs site. README + HACS rendering remain the user-facing documentation. `CLAUDE.md` is for AI agents.
- Becoming a Home Assistant Core integration (Path 2 from earlier discussion). The license question (library is AGPL-3.0-or-later), translation rewrite, and quality-scale climb make that a separate, future, multi-PR effort.
- Auto-discovery of DMX channel layouts from controller-side names. Users declare lights explicitly via OptionsFlow.
- Migration code beyond what already exists. The 1.0 → 1.2 entry-layout `async_migrate_entry` is dropped together with the HA-min bump (anyone affected has had ~2 years to upgrade).
- Bonus light types beyond dimmer / RGB / RGBW (no RGBWW, no CCT, no `number`-entity fallback for unmapped channels). Add later if asked.

## Commit plan

The PR consists of 13 commits, ordered so that the bug fix lands first (user value), the library bump goes early (later commits use v2 imports), tooling and HA-modernization land before the DMX feature, and tests are bundled with feature work after the test infrastructure exists.

### Phase A — bug fix

**1. `fix(config_flow): drop self.config_entry assignment in OptionsFlow`**
- Remove `self.config_entry = config_entry` from `ProconipPoolControllerOptionsFlowHandler.__init__`.
- Rename remaining internal use to `self._config_entry` for now (full modernization arrives in commit #8).
- Closes #70, #71.
- No test (CI gate doesn't exist yet); regression test arrives in commit #5.

### Phase B — library bump

**2. `deps: bump proconip to >=2.0.0 and switch to top-level imports`**
- `manifest.json` requirement `proconip>=1.3.0` → `proconip>=2.0.0`.
- `api.py`: replace `from proconip.api import …` and `from proconip.definitions import …` with `from proconip import …`.
- Add catch for `proconip.TimeoutException` where appropriate (was previously masked by `ProconipApiException`).
- Audit for any v1-vs-v2 surface differences (relay calibration fix may shift readings on non-default `offset`/`gain` controllers — call out in CHANGELOG).

### Phase C — tooling overhaul

**3. `build: introduce pyproject.toml with ruff/mypy/pytest config and dev/test extras`**
- New `pyproject.toml`:
  - No `[build-system]` (not a package).
  - `[project]` with `name = "proconip-hass"`, no version/dependencies (HA reads from `manifest.json`), `requires-python = ">=3.13"`.
  - `[project.optional-dependencies]`:
    - `dev = ["ruff", "mypy", "pre-commit"]`
    - `test = ["pytest", "pytest-asyncio", "pytest-cov", "pytest-homeassistant-custom-component", "aioresponses", "pytest-freezer"]`
  - `[tool.ruff]` `target-version = "py313"`, `line-length = 100`, lint rules matching the library (`E, W, F, I, B, UP, SIM, RET, PTH`).
  - `[tool.mypy]` `python_version = "3.13"`, `strict = true`, `files = ["custom_components"]`.
  - `[tool.pytest.ini_options]` `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `addopts = "--cov=custom_components/proconip_pool_controller --cov-report=term-missing --cov-report=xml --cov-fail-under=80"`.
  - `[tool.coverage.run]` `source = ["custom_components/proconip_pool_controller"]`, `branch = true`.
- Delete `requirements.txt`.
- Update `scripts/setup` to `pip install -e ".[dev,test]"` (the `-e .` works because `[project]` provides a minimal pyproject; pip installs the dev/test extras into the env).

**4. `lint: switch to ruff and add mypy strict`**
- `scripts/lint`: `ruff check .` + `ruff format --check .` + `mypy custom_components`.
- Replace `.github/workflows/lint.yml`: remove `psf/black@stable`, install via `pip install -e ".[dev]"`, run the three checks. Match library's structure (concurrency group, least-privilege permissions, pip caching, `actions/checkout@v6`, `actions/setup-python@v6`).
- First-pass code formatting fixes from `ruff format` and any `mypy --strict` violations land in this commit.

**5. `test: add pytest scaffolding with full coverage of existing code`**
- `tests/__init__.py`, `tests/conftest.py` with shared fixtures:
  - `enable_custom_integrations` (auto, from pytest-homeassistant-custom-component).
  - `mock_config_entry` factory (wraps `MockConfigEntry` with our domain + sane defaults).
  - `aioresponses_mock` for HTTP mocking.
  - CSV fixture loaders for `GetState.csv` and `GetDmx.csv` (copied from `proconip-pypi/tests/fixtures/`).
- Test files:
  - `tests/test_config_flow.py` — user flow happy + auth-fail + connection-fail + unknown-error paths; OptionsFlow happy + error paths; **regression test** asserting `OptionsFlowHandler(entry).config_entry is entry` does not raise (covers #70, #71).
  - `tests/test_coordinator.py` — happy poll, `BadCredentialsException` → `ConfigEntryAuthFailed`, `BadStatusCodeException` / `ProconipApiException` → `UpdateFailed`, dosage-relay tracking.
  - `tests/test_init.py` — `async_setup_entry` / `async_unload_entry` round-trip; `async_reload_entry`.
  - `tests/test_sensor.py`, `tests/test_switch.py`, `tests/test_select.py`, `tests/test_number.py`, `tests/test_binary_sensor.py` — entity creation, `unique_id` shape, dosage-relay availability/visibility, switch/select state changes call the right API method, dosage-timer countdown.
- Coverage gate (`--cov-fail-under=80`) enabled. With the existing surface fully tested, expected real coverage ~85%.

**6. `ci: refresh workflows`**
- New `.github/workflows/test.yml`: pytest with coverage upload, mirrors library's `test.yml` (concurrency, perms, cache).
- Existing `.github/workflows/release.yml`: add `needs: [test, lint]` jobs that re-call `test.yml` and `lint.yml` via `workflow_call`.
- New `.github/workflows/automerge.yml`: auto-approve and squash Dependabot PRs (mirrors library).
- New `.github/workflows/release-drafter.yml` + `.github/release-drafter.yml`: PR-label-driven release-note drafting (categories: breaking / feature / fix / dependencies / maintenance).
- Bump action versions: `actions/checkout@v6`, `actions/setup-python@v6`, `actions/upload-artifact@v7`, `softprops/action-gh-release@v3`.
- Apply concurrency groups, `permissions: contents: read` baseline, pip caching keyed on `pyproject.toml`.

**7. `chore: add dependabot config, pre-commit, CHANGELOG`**
- `.github/dependabot.yml`: weekly cadence; groups (`aiohttp-stack`, `dev-tools`, `actions`); commit-message prefixes (`deps`, `deps-dev`); `assignees: [ylabonte]`; PR limit 5.
- `.pre-commit-config.yaml`: ruff (lint+format) + mypy.
- `CHANGELOG.md` (Keep-a-Changelog format) with the 2.0.0 entry stubbed; entries get filled in commit #10.
- Update README's existing changelog section to point at `CHANGELOG.md` and stop duplicating entries.
- Add a one-line note in README's installation section: HACS default-list submission planned post-release.

### Phase D — HA modernization

**8. `refactor(config_flow): modernize OptionsFlow`**
- Drop `OptionsFlowHandler.__init__` entirely (HA wires `self.config_entry` automatically in modern versions).
- Read connection settings directly from `self.config_entry.options` instead of a copied `self.options` dict; build the new options dict at submit time.
- Update existing tests (`test_config_flow.py`) accordingly. Regression test from commit #5 stays green.

**9. `refactor: bump HA minimum, drop migration code, strip blueprint leftovers`**
- `manifest.json` `homeassistant` minimum bumped from `2024.2.1` to `2025.1` (or latest stable that's a clear floor — confirm at PR time).
- `hacs.json` `homeassistant` matched to the same value.
- Delete `async_migrate_entry` from `__init__.py` (handled the v1.0 → v1.2 entry layout fix; users on those versions have had ~2 years to upgrade).
- Fix `entity.py` docstring: `BlueprintEntity class` → `ProconipPoolControllerEntity class`.
- Delete the commented-out `@property config_entry` block at the bottom of `coordinator.py`.
- Remove now-dead migration tests if any; coordinator/init tests stay.

### Phase E — version bump

**10. `release: prepare 2.0.0`**
- `const.py` `VERSION` → `"2.0.0"`.
- In-tree `manifest.json` `version` → `"2.0.0"` (release workflow rewrites this from the tag at publish time, but in-tree must stay coherent during dev).
- `CHANGELOG.md` 2.0.0 entry: list breaking changes (HA min bump, library v2 surface, OptionsFlow shape, dropped migration), added (DMX support — referencing the upcoming feature commits), fixed (#70, #71), deps.
- Note in README that v1.x users running HA below `<min>` need to upgrade HA first; v1.x users with `proconip` controllers using non-default `offset`/`gain` calibration should verify relay state after upgrading (per library v2.0.0 breaking changes).

### Phase F — DMX feature

**11. `feat(coordinator): add DMX shadow, debounced writer, quiet window`**
- See [DMX architecture](#dmx-architecture) section below.
- Tests: `tests/test_coordinator_dmx.py`.

**12. `feat(config_flow): add DMX lights subflow`**
- See [DMX architecture](#dmx-architecture) section below.
- Tests: `tests/test_config_flow_dmx.py`.

**13. `feat(light): implement DMX dimmer/RGB/RGBW entities`**
- See [DMX architecture](#dmx-architecture) section below.
- Tests: `tests/test_light.py`.
- Adds `Platform.LIGHT` to `PLATFORMS` in `__init__.py`.
- Replaces the dormant `light.py` entirely.

## Tooling overhaul — what's mirrored vs. dropped

Mirroring the library where it serves the integration, dropping where it doesn't.

### Adopted

| Library element | Integration adoption |
|---|---|
| `pyproject.toml` for tool config + dev/test extras | Yes, identical layout minus packaging |
| `ruff` (lint + format), rules `E, W, F, I, B, UP, SIM, RET, PTH` | Yes, same rules |
| `mypy --strict` over source dir | Yes, over `custom_components/` |
| `pytest` + `pytest-asyncio` (auto) + `pytest-cov` | Yes |
| `aioresponses` for HTTP mocking | Yes (mocking the `proconip` library's HTTP layer) |
| Coverage gate `--cov-fail-under=80` | Yes |
| `tests/conftest.py` with shared fixtures | Yes |
| `tests/fixtures/*.csv` for parser test data | Yes (copied from library to keep CSVs identical) |
| `pre-commit` config | Yes |
| `CHANGELOG.md` (Keep-a-Changelog) | Yes |
| Dependabot weekly + grouped + prefixed | Yes |
| `automerge.yml` for Dependabot squash-merges | Yes |
| `release-drafter.yml` (label-driven) | Yes |
| CI hygiene: concurrency, least-privilege perms, pip caching | Yes |
| `actions/checkout@v6`, `setup-python@v6`, `upload-artifact@v7` | Yes |

### Added (integration-specific, not in library)

- `pytest-homeassistant-custom-component` for HA test fixtures.
- `pytest-freezer` for deterministic quiet-window assertions.

### Dropped

| Library element | Why not |
|---|---|
| `[build-system]` + `hatchling` + `hatch-vcs` | Integration is not a pip-installable package. HACS distributes the directory as a zip via `release.yml`. Version source-of-truth is `manifest.json` (rewritten from the GH release tag) + `const.py` `VERSION`. |
| `[project.dependencies]` | Runtime deps live in `manifest.json` for HA to install. |
| `requires-python` enforcement at install time | HA controls Python runtime. We set `target-version = "py313"` in ruff/mypy for tooling parity. |
| `mkdocs` + `docs/` + `docs.yml` workflow + GitHub Pages | No docs site needed. README is the user-facing doc; HACS renders it. CLAUDE.md is for agents. |
| `python-publish.yml` (PyPI Trusted Publishing OIDC) | No PyPI deployment. Existing `release.yml` produces the HACS zip. |
| `_version.py` | No version-from-VCS injection. |

## Testing strategy

- **Test runner:** `pytest` with `pytest-asyncio` in auto mode.
- **HA fixtures:** `pytest-homeassistant-custom-component` provides `hass`, `enable_custom_integrations`, `MockConfigEntry`, and the loop integration. We use these directly; no parallel HA harness.
- **HTTP mocking:** `aioresponses` intercepts `aiohttp` calls made by the `proconip` library. Fixtures load real `GetState.csv` and `GetDmx.csv` payloads from `tests/fixtures/`.
- **Time control:** `pytest-freezer` for tests that assert behavior across the DMX quiet window.
- **Coverage gate:** `--cov-fail-under=80`. Branch coverage on. Reports: terminal + `coverage.xml` artifact.
- **Test scope at end of PR:**
  - `test_config_flow.py` — user flow + options flow (post-modernization), all error branches, regression test for #70/#71.
  - `test_init.py` — setup/unload/reload round-trip.
  - `test_coordinator.py` — happy/auth-fail/update-fail/dosage-relay-tracking + DMX shadow + debounce + quiet window (after commit #11).
  - `test_sensor.py`, `test_switch.py`, `test_select.py`, `test_number.py`, `test_binary_sensor.py` — entity creation, state, action methods.
  - `test_light.py` — DMX entity creation, color round-trip, brightness, on/off semantics, reload-on-options-change.
  - `test_config_flow_dmx.py` — DMX subflow add/edit/remove, validation rejects.

## DMX architecture

### Components

- **Coordinator state** (`coordinator.py`):
  - `self._dmx_shadow: GetDmxData | None` — authoritative 16-channel state. Seeded on first successful `async_get_dmx`.
  - `self._dmx_last_write: datetime | None` — timestamp of last write (for the quiet window).
  - `self._dmx_flush_task: asyncio.Task | None` — pending debounced flush.
  - `self._dmx_flush_lock: asyncio.Lock` — serializes flushes; if a write arrives during a flush, the next flush is queued.
  - Constants: `DMX_DEBOUNCE_SECONDS = 0.15`, `DMX_QUIET_WINDOW_SECONDS = 1.5`.

- **OptionsFlow extension** (`config_flow.py`):
  - Existing `init` step retained for connection settings.
  - New `menu` step: `[ Connection settings | DMX lights | Done ]`.
  - New `dmx_lights_menu` step: dynamically built menu with one item per declared light (`Edit <name>`, `Remove <name>`) plus `Add` and `Back`.
  - New `dmx_light_form` step: form with `name` (text), `type` (select: dimmer/rgb/rgbw), `start_channel` (number 1–16). Used for both add and edit.
  - Validation at form submission: channel range fits within 16, no overlap with other lights (excluding the one being edited), name unique within entry.

- **Schema in `entry.options["dmx_lights"]`** — list of dicts:
  ```python
  {"slug": "pool_main", "name": "Pool main", "type": "rgbw", "start_channel": 1}
  ```
  - `slug` derived from `name` once, on the form-submit step that creates the light entry (`slugify(name)`); preserved on rename so HA's entity registry doesn't churn. If the slugified name collides with an existing light's slug, the form rejects with a validation error and the user must pick a different name.
  - `type` ∈ `{"dimmer", "rgb", "rgbw"}` → channel counts `{1, 3, 4}`.
  - `start_channel` 1-indexed; light occupies `[start_channel, start_channel + count)` in the controller's 1-indexed channel space.

- **Light entities** (`light.py`):
  ```
  ProconipDmxLightEntityBase(ProconipPoolControllerEntity, LightEntity)
    + ProconipDmxDimmerLight (ColorMode.BRIGHTNESS, 1 channel)
    + ProconipDmxRgbLight    (ColorMode.RGB,        3 channels)
    + ProconipDmxRgbwLight   (ColorMode.RGBW,       4 channels)
  ```
  - Each entity binds to a slice of `coordinator._dmx_shadow.channels` by start index.
  - `_attr_unique_id = f"dmx_light_{slug}_{instance_id}"` (consistent with the integration's existing `unique_id` convention).
  - `is_on` = any owned channel > 0.
  - `brightness` = max of owned channels (RGB/RGBW); single channel value (dimmer).
  - `rgb_color` / `rgbw_color` = direct channel values.

### Data flow

**Read path (every poll):**
1. `coordinator.proconip_update_method()` calls `client.async_get_data()` (existing).
2. **New:** if `data.is_dmx_enabled()` and `entry.options.get("dmx_lights")`, also `await client.async_get_dmx()`.
3. **New:** assign result to `self._dmx_shadow` only if `now - self._dmx_last_write > DMX_QUIET_WINDOW_SECONDS` (or `_dmx_last_write is None`). Otherwise discard the freshly-fetched DMX (relay/sensor data is always applied — they're independent).

**Write path (HA → controller):**
1. User toggles a light or sets a color.
2. `LightEntity.async_turn_on(...)` translates kwargs to channel values, mutates the relevant slice of `coordinator._dmx_shadow.channels`.
3. Calls `coordinator.schedule_dmx_flush()`:
   - sets `self._dmx_last_write = now`,
   - cancels any pending `_dmx_flush_task`,
   - creates a new task: `await asyncio.sleep(DMX_DEBOUNCE_SECONDS); async with self._dmx_flush_lock: await client.async_set_dmx(self._dmx_shadow); self._dmx_last_write = now`.
4. Entity calls `coordinator.async_request_refresh()`. The immediate refresh's DMX read is discarded by the quiet window; relay/sensor data still applies.
5. After `DMX_QUIET_WINDOW_SECONDS`, the next regular poll re-syncs DMX from the controller, picking up out-of-band changes (e.g. controller-side scripts).

### Error handling

- `async_set_dmx` raises `BadCredentialsException` → coordinator emits `ConfigEntryAuthFailed` (matching the relay-write path).
- `async_set_dmx` raises `BadStatusCodeException` / `TimeoutException` / `ProconipApiException` → log warning, mark all DMX entities unavailable until the next successful poll re-syncs the shadow.
- `async_get_dmx` failure during the regular poll → log + skip; relay/sensor updates still apply.
- Out-of-range / overlapping config (defensive, shouldn't occur due to OptionsFlow validation) → `async_setup_entry` skips the offending light + logs a warning.
- **DMX disabled on controller (`data.is_dmx_enabled()` returns False) but user has DMX lights configured**: skip the DMX read in the poll, log an info-level message once per setup, mark all DMX entities unavailable. The OptionsFlow `dmx_lights_menu` step shows a warning banner ("DMX is disabled on this controller — configured lights will not function until you enable DMX in the controller's settings") but still allows configuration so users can pre-stage lights before enabling DMX on-device.

### Reload behavior

Adding, editing, or removing a light through the OptionsFlow triggers `async_update_listener` → `async_reload_entry` (existing), which unloads and re-sets up the entry. The new entity set reflects the updated `entry.options["dmx_lights"]`. No manual entity-registry surgery.

## HACS default-list submission (Phase G)

In-PR work:
- README installation section gains a "HACS default-list submission planned post-release" note.
- `CHANGELOG.md` 2.0.0 entry references the post-release submission.
- `CLAUDE.md` documents the post-release follow-up step.
- `hacs.json` `homeassistant` minimum stays in lockstep with `manifest.json` (handled by commit #9).

Post-merge / post-tag (manual, outside this PR):
1. Tag `v2.0.0`, publish GitHub release. `release.yml` produces the HACS zip; `validate.yml` and `lint.yml` and `test.yml` go green.
2. Open a PR to [`hacs/default`](https://github.com/hacs/default) editing the `integration` file: add `ylabonte/proconip-hass` alphabetically. Submitted from the personal GitHub account, not an org. PR template completed in full.
3. Once merged: README installation section updates to "available in HACS default" (small follow-up PR).

Brand prerequisites (verified 2026-05-10):
- `home-assistant/brands` already has `custom_integrations/proconip_pool_controller/{icon.png,logo.png}`. No brands PR needed.

## Risks and open questions

- **`proconip` v2.0.0 surface changes during commit #2 may have edges we miss.** Mitigation: the test suite added in commit #5 will catch most behavioral drift; manual `scripts/develop` smoke test against a real controller is the final gate.
- **HA minimum version floor in commit #9 is TBD-confirmed at PR time.** `2025.1` is a sane default; will check HA's release calendar at the moment of writing the commit and pick the most recent stable that's been out long enough to be a safe floor.
- **DMX race-condition strategy is one of several reasonable designs.** The chosen approach (shadow + debounce + quiet window) is robust under typical HA usage but assumes (a) no pathological writes faster than the debounce window from automations, (b) controller-side state changes are infrequent enough that 1.5s of staleness is acceptable. If users report issues, the constants are easy to tune.
- **`coordinator._dmx_flush_task` lifecycle on entry unload.** Need to cancel the task in `async_unload_entry` to avoid the task firing against a torn-down session. Captured in the implementation plan.
- **OptionsFlow slug stability across renames.** Slug is derived once from name and persisted; subsequent renames update `name` but not `slug`. Tested in `test_config_flow_dmx.py`. Edge case: two lights, both renamed, second rename collides with first's slug — should not happen because slug stays bound to the original name's slug. Worth a test.
- **`pytest-homeassistant-custom-component` version compatibility with HA min.** The plugin is versioned per HA Core version. The `[project.optional-dependencies] test` extra needs the right pin (e.g. `pytest-homeassistant-custom-component~=0.13.x` for HA 2025.1 — verify at write time).

## Manual smoke-test checklist (before merging)

Run after all 13 commits land, against `scripts/develop` with a real ProCon.IP controller (or the provided sandbox if one is available):

- Fresh install via "Add Integration" — connection settings flow succeeds.
- Reconfigure existing instance via gear icon — OptionsFlow opens without error (regression-tests #70 #71 manually).
- Toggle a regular relay (switch, select, dosage timer) — controller responds, HA state matches.
- Configure an RGB DMX light (channels 1-3), an RGBW light (channels 4-7), a single dimmer (channel 8) via OptionsFlow.
- Set RGB color via HA color picker — controller channels 1-3 reflect the chosen color within 1.5s.
- Set RGBW color — channels 4-7 update; W channel handled correctly.
- Slide brightness on the dimmer — channel 8 reflects the value.
- Modify a DMX channel via the controller's native web UI — HA state catches up within ~1.5-2s after the next poll.
- Remove a DMX light via OptionsFlow — entity disappears from HA after reload.
- Stop / start HA — DMX entities and connection settings persist correctly.
