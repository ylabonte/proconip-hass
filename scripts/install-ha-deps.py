"""Pre-install Home Assistant's eager-import requirements.

HA's `helpers/service.py:_base_components()` imports 19 built-in
components at module-load time. Each may transitively pull in pip
packages via its own `manifest.json` `requirements:` / `dependencies:`
lists. If those packages aren't installed by the time `_base_components()`
runs (which happens during any integration's `services.yaml` validation),
HA crashes with `ModuleNotFoundError`.

HA's own lazy installer can install these on demand, but it runs in
worker threads and does NOT block component setup. On a cold venv the
imports lose the race against the install and we end up in recovery
mode (see https://github.com/home-assistant/core/issues/... — this is
intentional, not a bug, but it makes for a miserable dev loop).

This script walks HA's manifest.json files to determine the minimum
pip-requirement set, then installs it. The source of truth is HA's
manifests, not a hand-curated package list — so the set stays correct
across HA Core upgrades without us tracking individual packages.

Run after `pip install -e .[dev,test]` (so `homeassistant` is importable)
and before launching HA via `scripts/develop`. `scripts/setup` does
both for you.

If you add an integration key to `config/configuration.yaml`, mirror it
in `CONFIG_INTEGRATIONS` below so its requirements get pre-installed too.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

# Eager-import set from helpers/service.py:_base_components(). This list
# is hard-coded in HA Core; if it changes between HA versions, mirror
# the change here. (Auto-parsing HA's source via ast was deemed too much
# magic — a manual mirror with a clear comment is easier to audit.)
BASE_COMPONENTS: tuple[str, ...] = (
    "ai_task",
    "alarm_control_panel",
    "assist_satellite",
    "calendar",
    "camera",
    "climate",
    "cover",
    "fan",
    "humidifier",
    "light",
    "lock",
    "media_player",
    "notify",
    "remote",
    "siren",
    "todo",
    "update",
    "vacuum",
    "water_heater",
)

# Integrations explicitly loaded in `config/configuration.yaml`. Keep in
# sync with that file.
CONFIG_INTEGRATIONS: tuple[str, ...] = (
    "frontend",
    "config",
    "api",
    "http",
    "logger",
    "homeassistant",
)


def find_components_dir() -> Path:
    """Locate HA Core's bundled `components/` directory."""
    import homeassistant

    components = Path(homeassistant.__file__).parent / "components"
    if not components.is_dir():
        raise SystemExit(f"HA components dir not found at {components}")
    return components


def collect_requirements(
    seeds: tuple[str, ...],
    components: Path,
    seen: set[str] | None = None,
) -> set[str]:
    """Walk manifests and gather pip requirements for the given integrations
    and their transitive HA-internal dependencies."""
    if seen is None:
        seen = set()
    requirements: set[str] = set()
    for name in seeds:
        if name in seen:
            continue
        seen.add(name)
        manifest = components / name / "manifest.json"
        if not manifest.is_file():
            continue
        data = json.loads(manifest.read_text())
        requirements.update(data.get("requirements", []))
        # Recurse into HA-internal integration deps (these are NOT pip
        # packages — they reference sibling components/<name>/ directories).
        next_seeds = tuple(data.get("dependencies", ()))
        if next_seeds:
            requirements |= collect_requirements(next_seeds, components, seen)
    return requirements


def main() -> int:
    components = find_components_dir()
    seeds = BASE_COMPONENTS + CONFIG_INTEGRATIONS
    reqs = collect_requirements(seeds=seeds, components=components)
    if not reqs:
        print("==> No HA component requirements to install.")
        return 0
    print(f"==> Installing {len(reqs)} HA component requirements via pip:")
    for r in sorted(reqs):
        print(f"      {r}")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", *sorted(reqs)]
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
