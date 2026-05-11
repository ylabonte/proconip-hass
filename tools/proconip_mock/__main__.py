"""CLI entry point for the mock ProCon.IP HTTP server.

Run with:

    python -m tools.proconip_mock                  # 127.0.0.1:8080, admin/admin
    python -m tools.proconip_mock --port 9999
    python -m tools.proconip_mock --host 0.0.0.0   # bind to all interfaces
    python -m tools.proconip_mock --username u --password p

The mock serves the four endpoints a real ProCon.IP controller would
(`/GetState.csv`, `/GetDmx.csv`, `/usrcfg.cgi`, `/Command.htm`) with
drifting sensor values and mutable relay + DMX state. Useful for
exercising the Home Assistant integration end-to-end inside a
devcontainer without owning real hardware.
"""

import argparse
import logging
import sys

from aiohttp import web

from .server import create_app
from .state import MockState


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.proconip_mock",
        description="Mock ProCon.IP controller HTTP server.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Bind port (default: 8080).",
    )
    parser.add_argument(
        "--username",
        default="admin",
        help="Basic-auth username the mock requires (default: admin).",
    )
    parser.add_argument(
        "--password",
        default="admin",
        help="Basic-auth password the mock requires (default: admin).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    state = MockState()
    app = create_app(state, username=args.username, password=args.password)
    print(
        f"ProCon.IP mock listening on http://{args.host}:{args.port}/  "
        f"(basic auth: {args.username}/{args.password})"
    )
    web.run_app(app, host=args.host, port=args.port, print=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
