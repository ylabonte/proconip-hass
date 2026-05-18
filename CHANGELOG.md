# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note on the changelog process:** from the next release onward,
> [release-please](https://github.com/googleapis/release-please) owns
> this file — entries are auto-generated from Conventional Commits on
> `main`. The `[Unreleased]` block below is a hand-curated summary of
> everything staged for `v2.0.0` (the first release-please-managed
> release). When this branch lands on `main` with a `feat!:` squash-
> merge subject, release-please will open a "release: 2.0.0" PR; the
> auto-generated entry can be merged into or replaced with the
> `[Unreleased]` content below before the PR ships.

## [Unreleased]

### Breaking changes

- **Home Assistant minimum version is now 2025.1.0.** Older HA installs must upgrade before installing this release.
- **`proconip` library bumped to `>=2.1.0`** (Python 3.13+ required by the library, matching HA Core 2026.5). The 2.0.0 release fixed a double-application bug in `offset`/`gain` calibration — controllers with non-default calibration may report different relay state after upgrading; verify state for any custom-calibrated controller. 2.1.0 itself adds MIT relicensing and updated dev-deps; no further API changes.
- **OptionsFlow internals changed** — the `__init__` override and the v1 → v1.2 entry-layout migration code were removed. Users on entry layouts from before v1.2.0 (Feb 2024) must upgrade through an older release first.

### Added

- **DMX light support.** Configure RGB, RGBW, or single-channel dimmer lights from the integration's options flow by mapping them to channels on your ProCon.IP. Each declared light becomes a Home Assistant `light` entity with the appropriate color mode.
- **DMX lights can be added during initial setup.** After validating credentials, a new optional menu lets users add DMX lights up front before the config entry is created (no need to re-open Options afterwards). The menu can be skipped with one click for users without DMX hardware. Localised in English and German.
- **Full entity name localisation (English + German).** Every entity in the integration (binary sensors, sensors, switches, selects, the dosage `number`, DMX lights) now ships its display name through HA's translation system. New languages can be added by dropping in a `translations/<lang>.json` file with the same `entity.<platform>.<key>.name` keys.
- **DMX-lights submenu polish (in Options).** The submenu shows one labelled row per light (`Edit "<name>" (<TYPE> · ch <N>)`), gates the `Remove a light…` entry behind a confirmation step, and is fully localised.
- pytest test suite with `pytest-homeassistant-custom-component`, 80% coverage gate.
- ruff (lint + format) and `mypy --strict` replace black; pre-commit config.
- `CHANGELOG.md` (Keep-a-Changelog) — taken over by release-please from the next release.

### Fixed

- **OptionsFlow crashes on modern Home Assistant** — closes #70 and #71. Modern HA's `OptionsFlow.config_entry` is a read-only property; the previous assignment raised `AttributeError` and prevented users from reconfiguring the integration.
- **DMX RGB light control** — closes #61. ProCon.IP DMX channels can now be grouped into HA lights with proper color modes; users no longer need a separate Art-Net integration.

### Changed

- **Entity display names use HA's modern `_attr_has_entity_name = True` pattern.** In the device card the entity name appears alone (e.g. `Redox sensor`); in dashboards and the entities list it's prefixed with the device name (`ProCon.IP Pool Controller Redox sensor`). This is a *display-only* change — `entity_id`s are unchanged, so automations, scripts, and dashboards that reference entities by ID (`sensor.redox_electrode_<…>`) keep working without edits.
- Tooling: `pyproject.toml` centralizes ruff/mypy/pytest config; `requirements.txt` removed.

### CI / Tooling

- **Release pipeline switched to [release-please](https://github.com/googleapis/release-please)** (mirrors the `proconip-pypi` sibling repo). Conventional Commit titles on `main` now drive version bumps, changelog generation, tagging, and the auto-opened "release: X.Y.Z" PR. The old release-drafter + manual-publish flow has been removed. See **Release flow** in `CONTRIBUTING.md` and **Release / version bumping** in `CLAUDE.md` for the full walkthrough.
- New `hacs-release.yml` workflow handles the zip-and-attach on `release: published`, replacing the in-tree `yq`-based version rewrite (release-please's `extra-files` config keeps `manifest.json` and `const.py` in sync at release-PR time).
- Replaced Dependabot's `github-actions` ecosystem with a dedicated weekly workflow that runs `ylabonte/github-actions-updater@v1` to open a single grouped PR for outdated action references. `automerge.yml` broadened to handle that bot alongside Dependabot.
- Refreshed action versions across CI; concurrency groups + least-privilege permissions; pip caching keyed on `pyproject.toml`.
- Repo prepared for HACS default-list submission (post-release).

## [1.2.0] — 2024-02-12

See `README.md` (Changelog section) for entries prior to the introduction of
this file.
