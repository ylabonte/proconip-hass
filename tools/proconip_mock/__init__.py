"""Local-only mock of the ProCon.IP HTTP API for development and testing.

This package is **not** part of the published `proconip` library — it lives
under `tools/` so it stays out of the wheel and sdist. It exists to give
contributors and CI (locally or via GitHub Codespaces) a fake controller they
can drive with the real client functions.

Run with ``python -m tools.proconip_mock`` from the repo root. See the
package README for environment variables and example requests.
"""

from .server import create_app
from .state import MockState

__all__ = ["create_app", "MockState"]
