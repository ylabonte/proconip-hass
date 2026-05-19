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

The repo ships a fully-configured devcontainer with Python 3.14, a
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

> **`scripts/setup` pre-installs HA's eager-import deps** (`pymicro-vad`,
> `hassil`, `PyTurboJPEG`, `home-assistant-frontend`, …) by walking each
> integration's `manifest.json` via `scripts/install-ha-deps.py`. That
> way `scripts/develop` can boot with `--skip-pip` and HA initializes in
> well under a second — no lazy-install storm, no recovery mode. Don't
> hand-curate a pip-package list to replace this; HA's manifests are
> the source of truth.

A **mock ProCon.IP controller** starts automatically on every container
start via `.devcontainer.json`'s `postStartCommand`, which runs
`.devcontainer/start-mock.sh`. The script backgrounds the server, polls
`/GetState.csv` until it answers, and fails the postStart hook if the
mock didn't come up — so a silent startup failure can't hide. Logs go
to `/tmp/proconip-mock.log` inside the container.

The mock is an aiohttp server with drifting sensor values + mutable
relay/DMX state. It binds `0.0.0.0:8080` inside the container (the
devcontainer overrides the package's loopback default via
`PROCONIP_MOCK_HOST=0.0.0.0` in `remoteEnv`), and the container's port
8080 is forwarded to the host. Point HA at `http://127.0.0.1:8080` with
`admin`/`admin` to exercise the full flow without owning real hardware.

> **`tools/proconip_mock/` and `.devcontainer/start-mock.sh` are
> vendored from `ylabonte/proconip-pypi`.** That's where the canonical
> implementation lives (alongside the library). Update there first,
> then re-sync here — don't edit in place.

For a foreground mock with visible logs, run `scripts/mock-server` or use
the **Tasks → ProCon.IP mock server** task in VS Code (defaults to
loopback only; override via `PROCONIP_MOCK_HOST=0.0.0.0` if you need
external access). Restart the auto-started instance with `bash
.devcontainer/start-mock.sh` from the container terminal.

### Option B — Local dev (host machine)

Requirements:

- **Python ≥ 3.14.2** for development. (Runtime ships fine on Python ≥ 3.13 — see `hacs.json` — but `[dev,test]` pulls in `pytest-homeassistant-custom-component`, which pulls current HA Core, which itself requires 3.14.2+. `scripts/setup` enforces this and will reject 3.14.0/3.14.1.)
- Git
- A terminal

Setup:

```bash
git clone https://github.com/ylabonte/proconip-hass.git
cd proconip-hass
scripts/setup
```

`scripts/setup` will:

- Pick the newest Python ≥ 3.14.2 it can find (`python3.14`, then
  `python3`; 3.14.0 and 3.14.1 are rejected). Override with
  `PYTHON=python3.X scripts/setup` to force a specific interpreter
  (the override is gated on the same ≥ 3.14.2 floor).
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
| `scripts/dev-reset`                    | Wipe `config/.storage/`, the recorder DB, logs, etc. — fresh HA state on next run. Keeps `config/configuration.yaml`. Use when stale config entries cause lazy-install errors after a `manifest.json` change. |
| `scripts/mock-server`                  | Run the mock ProCon.IP controller in the foreground (logs to stdout). Defaults to `127.0.0.1:8080` with `admin`/`admin`. The devcontainer auto-starts a backgrounded mock on `0.0.0.0:8080` via `.devcontainer/start-mock.sh`; use this script only for manual smoke-testing. Override via `PROCONIP_MOCK_HOST=…`, `PROCONIP_MOCK_PORT=…`, `PROCONIP_MOCK_USER=…`, `PROCONIP_MOCK_PASS=…`. |

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
- **Suffix every entity `unique_id` with the config entry ID.**
  Multi-instance support (one HA, multiple ProCon.IP controllers)
  depends on it. The current pattern in every entity module is to set
  `self._attr_unique_id = f"<stable_key>_{instance_id}"` *after*
  `super().__init__()` — keep that shape rather than relying on the
  base class to append. (`ProconipPoolControllerEntity` only appends the
  entry-id suffix when `_attr_unique_id` is still unset by the subclass.)

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
- **Commit titles must be Conventional Commits.** The maintainer
  squash-merges, so the PR title becomes the commit subject — title your
  PR like the commit you want recorded.
- Keep commits focused. One logical change per commit. Multiple related
  commits per PR is fine, but each should still carry the right
  conventional type.
- Reference issues in the commit body or PR description (`Closes #123`).

### Conventional Commits — type → release behaviour

[release-please](https://github.com/googleapis/release-please) reads
these on every push to `main` and decides what to do.

| Type | Triggers a release? | Visible in CHANGELOG? | Use for |
|---|---|---|---|
| `feat` | minor bump | yes (Features) | new entity, new config option, new feature |
| `feat!` or `BREAKING CHANGE:` footer | major bump | yes (Features + breaking note) | renamed entity_id, removed entity, HA-min bump |
| `fix` | patch bump | yes (Bug Fixes) | user-visible bugfix |
| `perf` | patch bump | yes (Performance) | perf change without behaviour change |
| `deps` | none | yes (Dependencies) | proconip / HA / runtime dep bump |
| `docs` | none | yes (Documentation) | README/CONTRIBUTING/CLAUDE.md edits |
| `refactor` | none | hidden | internal cleanup with no behaviour change |
| `test` | none | hidden | adding/changing tests only |
| `build` | none | hidden | build-system / packaging changes |
| `ci` | none | hidden | anything under `.github/` |
| `chore` | none | hidden | catch-all: lockfile bumps, formatting, devcontainer/scripts/tools |

**Rule of thumb — when is a commit user-facing?** If the change is
limited to `.github/`, `.devcontainer/`, `.vscode/`, `scripts/`,
`tools/`, `tests/`, or documentation, use a silent type
(`ci`/`chore`/`test`/`docs`/`refactor` as appropriate). If the change
touches `custom_components/proconip_pool_controller/`, `manifest.json`'s
non-`version` fields, or `translations/*.json` user-visible labels, use
`feat`/`fix`/`perf` so it lands in the next release notes.

**Mixed-change PR rule:** split into separate commits with the right
types. Don't describe a CI tweak in a `feat:` commit — release-please
would file it in the wrong section.

## Pull requests

- PR against `main`.
- **Title the PR as the conventional commit you want recorded** —
  squash-merge turns the PR title into the commit subject.
- Describe **what** and **why**. The reviewer should be able to skip the
  diff and still understand intent.
- Include a **Test plan** — what you did to verify the change. For
  user-facing changes, a manual smoke-test checklist (run via
  `scripts/develop`) is welcome.
- CI must be green: `Lint`, `Test`, `Validate (Hassfest + HACS)`,
  `CodeQL`.
- **Don't edit `CHANGELOG.md` yourself** — release-please owns it.
  Your conventional commit subject is what shows up in the next release
  entry.
- Note that **adding or removing entities** means users have to clean up
  obsolete entities manually. Mention this in the commit body or PR
  description so it makes it into the release notes context.

## Translations

The integration is fully translatable. Strings live under
`custom_components/proconip_pool_controller/translations/`.

- `en.json` is the source. Update it when you change the config flow or
  options flow.
- `de.json` must be kept in sync (the maintainer is German). If you don't
  speak German, leave a TODO in the PR — the maintainer will fill it in.
- Other languages welcome via PR.

## Release flow

Releases are **fully automated by [release-please](https://github.com/googleapis/release-please)** — maintainers don't tag, draft release notes, or zip by hand. Conventional Commit titles on `main` (see the table above) drive everything.

1. Land PRs on `main` with conventional commit titles.
2. [`release.yml`](.github/workflows/release.yml) runs `release-please-action@v5` on every push. If new `feat`/`fix`/`perf`/`revert`/`deps`/`docs` commits exist since the last release, it opens or updates a **"chore(main): release X.Y.Z" PR** that:
    - bumps `.release-please-manifest.json`
    - bumps `custom_components/proconip_pool_controller/manifest.json:version` (via release-please's `extra-files: json` config)
    - bumps `custom_components/proconip_pool_controller/const.py:VERSION` (via `extra-files: generic` — the `# x-release-please-version` comment is the marker; don't remove it)
    - prepends the generated changelog entry to `CHANGELOG.md`
3. Review and merge that PR. release-please cuts the `vX.Y.Z` tag and creates the GitHub release.
4. [`hacs-release.yml`](.github/workflows/hacs-release.yml) fires on `release: published`, re-runs `test` + `lint` against the released tag, zips `custom_components/proconip_pool_controller/`, and attaches `proconip_pool_controller.zip` to the release. HACS picks it up on next poll.

Don't hand-edit `manifest.json:version`, `const.py:VERSION`, or `.release-please-manifest.json` — release-please owns all three. The marker comment on `VERSION` must stay verbatim.

After the first release-please-managed release lands, the maintainer opens a PR against [`hacs/default`](https://github.com/hacs/default) (post-2.0.0) to keep the HACS-default listing current.

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
