# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] — 2026-05-11

### Breaking changes

- **Home Assistant minimum version is now 2025.1.0.** Older HA installs must upgrade before installing this release.
- **`proconip` library bumped to `>=2.0.0`** (Python 3.13+ required by the library, matching HA Core 2026.5). Controllers with non-default `offset`/`gain` calibration may report different relay state after upgrading because the library v2.0.0 fixed a double-application bug; verify state for any custom-calibrated controller.
- **OptionsFlow internals changed** — the `__init__` override and the v1 → v1.2 entry-layout migration code were removed. Users on entry layouts from before v1.2.0 (Feb 2024) must upgrade through an older release first.

### Added

- **DMX light support.** Configure RGB, RGBW, or single-channel dimmer lights from the integration's options flow by mapping them to channels on your ProCon.IP. Each declared light becomes a Home Assistant `light` entity with the appropriate color mode.
- pytest test suite with `pytest-homeassistant-custom-component`, 80% coverage gate.
- ruff (lint + format) and `mypy --strict` replace black; pre-commit config.
- Dependabot weekly grouped updates; release-drafter; auto-merge for Dependabot PRs.
- `CHANGELOG.md` (Keep-a-Changelog).

### Fixed

- **OptionsFlow crashes on modern Home Assistant** — closes #70 and #71. Modern HA's `OptionsFlow.config_entry` is a read-only property; the previous assignment raised `AttributeError` and prevented users from reconfiguring the integration.
- **DMX RGB light control** — closes #61. ProCon.IP DMX channels can now be grouped into HA lights with proper color modes; users no longer need a separate Art-Net integration.

### Changed

- Tooling: `pyproject.toml` centralizes ruff/mypy/pytest config; `requirements.txt` removed.
- CI: refreshed action versions, concurrency groups, least-privilege permissions, pip caching keyed on `pyproject.toml`. `release.yml` gated on `test` and `lint` workflows.
- Repo prepared for HACS default-list submission (post-release).

## [1.2.0] — 2024-02-12

See `README.md` (Changelog section) for entries prior to the introduction of
this file.
