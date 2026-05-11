# Contributing

Thanks for wanting to help! This file is the developer-facing handbook.
The [README](README.md) is the user-facing "cover" (install + usage); read
this one if you want to hack on the integration.

## Ways to contribute

- 🐛 **Report a bug**: [open an issue](../../issues/new/choose). Great bug
  reports include reproduction steps, expected vs. actual behavior, and HA
  + integration version info.
- 💡 **Propose a feature**: open a feature-request issue first so we can
  discuss scope before you write code.
- 🛠️ **Submit a fix or feature**: fork → branch from `main` → PR back to
  `main`. Read the rest of this file first.
- 💬 **Discuss the current state of the code**: issues are also fine for
  open-ended questions.

All contributions are released under the project's [MIT license](LICENSE).

## Development environment

### Option A — VS Code Dev Container (recommended)

The repo ships a fully-configured devcontainer with Python 3.13, a
ready-to-run Home Assistant, and all dev/test tooling preinstalled.

1. Install [Docker](https://docs.docker.com/get-docker/) and the
   [Dev Containers VS Code extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).
2. Open the repo folder in VS Code.
3. Command Palette → **"Dev Containers: Reopen in Container"**.
4. Wait for `postCreateCommand` to finish (it runs `scripts/setup` and
   installs everything into an isolated `.venv` mounted as a Docker
   volume — your host's `.venv` is hidden from the container, so the
   two environments don't conflict).

After the container is up, VS Code uses
`/workspaces/proconip-hass/.venv/bin/python` as the interpreter, and the
Ruff + Mypy extensions pick up the project's tool versions automatically.

### Option B — Local dev (host machine)

Requirements:

- **Python ≥ 3.13** (we test on 3.13 and 3.14)
- Git
- A terminal

Setup:

```bash
git clone https://github.com/ylabonte/proconip-hass.git
cd proconip-hass
scripts/setup
```

`scripts/setup` will:

- Pick the newest Python ≥ 3.13 it can find (`python3.14`, then
  `python3.13`, then `python3`). Override with
  `PYTHON=python3.X scripts/setup` to force a specific interpreter.
- Create (or rebuild, if broken) `.venv` in the repo root.
- Install the dev + test extras via `pip install -e ".[dev,test]"`.

Activate the environment for an interactive session:

```bash
source .venv/bin/activate
```

## Common commands

| Command                                | What it does                                                                 |
|----------------------------------------|------------------------------------------------------------------------------|
| `scripts/setup`                        | Create/refresh `.venv` and install dev/test deps.                            |
| `scripts/lint`                         | Run `ruff check` + `ruff format --check` + `mypy --strict`. All must pass.   |
| `pytest`                               | Run the full test suite with coverage (must stay ≥ 80%).                     |
| `pytest tests/test_config_flow.py -v`  | Run a single test file (verbose).                                            |
| `pytest -k test_options_flow_no_init`  | Run tests matching a name.                                                   |
| `pytest --cov-report=html`             | Generate an HTML coverage report at `htmlcov/index.html`.                    |
| `pre-commit run --all-files`           | Run all pre-commit hooks against every file (same checks as `scripts/lint`). |
| `pre-commit install`                   | Install pre-commit hooks (`git commit` will then auto-run them).             |
| `ruff format .`                        | Auto-format your changes.                                                    |
| `ruff check --fix .`                   | Auto-fix safe lint findings.                                                 |
| `scripts/develop`                      | Boot a local Home Assistant on port 8123 with this integration loaded.       |
| `scripts/dev-reset`                    | Wipe `config/.storage/`, the recorder DB, logs, etc. — fresh HA state on next run. Keeps `config/configuration.yaml`. Use when stale config entries (e.g. from a previous `default_config:` run) cause lazy-install errors. |

## Code conventions

- **Format and lint with ruff. Type-check with `mypy --strict`.** All three
  must pass before a PR will be reviewed. `scripts/lint` runs them
  together; `pre-commit` runs the same checks on `git commit`.
- **Use keyword arguments** when calling HA / `proconip` library functions
  (`coordinator=coordinator`, `relay_id=…`, `entry=entry`). The existing
  code is consistent about this — match it.
- **Add `from __future__ import annotations`** at the top of new modules.
- **Single logger per package** — use `LOGGER` from `const.py`, don't
  create new loggers.
- **Public classes and async functions get docstrings.** Short one-liners
  are fine; that's the established pattern.
- **Keep `manifest.json` and `const.py` `VERSION` in sync** during dev.
  Releases overwrite `manifest.json` automatically from the GitHub release
  tag (see [Release flow](#release-flow)), but don't let them drift in
  feature branches.
- **Keep `translations/en.json` and `translations/de.json` in sync** when
  changing the config or options flow. New strings need entries in both.
- **Don't read connection settings from `entry.data`** — use
  `entry.options`. (`entry.data` only holds `CONF_NAME`.)
- **Suffix every entity `unique_id` with the config entry ID** (the base
  class handles this). Multi-instance support depends on it.

## Testing

Tests live under `tests/`. Conventions:

- `tests/conftest.py` provides shared fixtures
  (`hass`, `mock_state_endpoint`, `mock_dmx_endpoint`, `config_entry`,
  `setup_integration`, …). Use them.
- `tests/fixtures/*.csv` are real controller payloads copied from the
  [`proconip` library's test fixtures](https://github.com/ylabonte/proconip-pypi/tree/main/tests/fixtures).
  Don't inline test CSVs into test functions.
- HTTP calls are mocked with [`aioresponses`](https://github.com/pnuckowski/aioresponses).
  Tests should **assert that the right request actually fired** (e.g. by
  checking `mock.requests`), not just that the service call didn't raise.
- Tests are async-by-default (pytest-asyncio in auto mode). You don't
  need `@pytest.mark.asyncio`.
- The **80% coverage gate** is enforced by `pytest`'s `--cov-fail-under=80`.
  If you add a new entity class or branch, add at least one test that
  exercises its behavior.
- Use `pytest-freezer` to control time in tests that depend on it (e.g.
  DMX quiet-window assertions).

## Architecture cheat-sheet

The integration is a thin Home Assistant adapter on top of the
[`proconip` PyPI library](https://github.com/ylabonte/proconip-pypi) (docs:
https://ylabonte.github.io/proconip-pypi/). When a question is about
*what data exists* or *how a call works*, the answer is in that library —
not here.

```
proconip lib (GetState/RelaySwitch/DosageControl/DmxControl)
        ↑
api.py (ProconipApiClient)            ← thin wrapper, owns aiohttp session
        ↑
coordinator.py (DataUpdateCoordinator) ← single poll → GetStateData
        ↑                              + DMX shadow + debounced write coalescer
entity.py (ProconipPoolControllerEntity) ← CoordinatorEntity base, sets DeviceInfo
        ↑
binary_sensor.py / sensor.py / switch.py / select.py / number.py / light.py
```

For deeper detail (dosage-relay handling, DMX race-condition strategy,
multi-instance `unique_id` rules), see [`CLAUDE.md`](CLAUDE.md) at the
repo root.

## Branching and commits

- Branch from `main`. Use a descriptive branch name
  (`feat/dmx-rgb-light`, `fix/options-flow-crash`, etc.).
- Write **short, imperative commit subject lines** — no Conventional
  Commits prefix in the subject. Recent log: `Update actions versions`,
  `Bump proconip to >=2.0.0 and switch to top-level imports`, etc.
- Keep commits focused. One logical change per commit. Multiple related
  commits per PR is fine.
- Reference issues in the commit body or PR description (`Closes #123`).

## Pull requests

- PR against `main`.
- Describe **what** and **why**. The reviewer should be able to skip the
  diff and still understand intent.
- Include a **Test plan** — what you did to verify the change. For
  user-facing changes, a manual smoke-test checklist (run via
  `scripts/develop`) is welcome.
- CI must be green: `Lint`, `Test`, `Validate (Hassfest + HACS)`, `CodeQL`.
- Update [`CHANGELOG.md`](CHANGELOG.md) under `## [Unreleased]` for any
  user-visible change (entity additions/removals, breaking config
  changes, HA-min bumps).
- Note that **adding or removing entities** means users have to clean up
  obsolete entities manually. Call this out in the changelog when it
  happens.

## Translations

The integration is fully translatable. Strings live under
`custom_components/proconip_pool_controller/translations/`.

- `en.json` is the source. Update it when you change the config flow or
  options flow.
- `de.json` must be kept in sync (the maintainer is German). If you don't
  speak German, leave a TODO in the PR — the maintainer will fill it in.
- Other languages welcome via PR.

## Release flow

Releases are cut by **publishing a GitHub release** with a `vX.Y.Z` tag.
The [`release.yml`](.github/workflows/release.yml) workflow:

1. Re-runs `test` and `lint` workflows (a release won't ship with broken
   CI).
2. Rewrites `manifest.json` `version` to the tag.
3. Zips the integration directory and attaches it to the release as
   `proconip_pool_controller.zip` (the HACS download).

Don't hand-edit `manifest.json` `version` for a release — let the tag
drive it.

After publishing the release, the maintainer opens a PR against
[`hacs/default`](https://github.com/hacs/default) (post-2.0.0) to keep
the HACS-default listing current.

## Getting help

- Look at the [issues](../../issues) — your question may already be
  answered.
- The [proconip library docs](https://ylabonte.github.io/proconip-pypi/)
  cover the device-side API.
- The [HA developer docs](https://developers.home-assistant.io/) cover
  the integration-side conventions.
- Ping in a comment on an open issue if you're stuck on a related PR.

By contributing, you agree your contributions are licensed under the
project's [MIT license](LICENSE).
