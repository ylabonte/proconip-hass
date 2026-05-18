"""Mutable in-memory state of the mock ProCon.IP controller.

Holds the relay enable/output bitmaps (16 bits each — internal relays in bits
0–7, external relays in bits 8–15) and the 16 DMX channels. Mutated by the
HTTP server in response to `POST /usrcfg.cgi`; read by the CSV renderer when
serving `GET /GetState.csv` and `GET /GetDmx.csv`.

Time is tracked via a monotonic clock captured at construction. The drift
module derives sensor values from `elapsed_seconds()` so that everything is
deterministic given a clock and start time.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field

NUM_RELAY_BITS = 16
NUM_DMX_CHANNELS = 16


@dataclass
class MockState:
    """Snapshot of every mutable controller state the mock cares about.

    The ``config_other_enable`` field is rendered into row 1 (SYSINFO) of
    ``/GetState.csv`` and gates the client-side feature flags exposed by
    `proconip.definitions.GetStateData`. Bit layout (from `definitions.py`):

    - bit 0 (1)   — TCP/IP boost
    - bit 1 (2)   — SD card logging
    - bit 2 (4)   — DMX
    - bit 3 (8)   — Avatar
    - bit 4 (16)  — Relay extension (internal + external relays)
    - bit 5 (32)  — High bus load
    - bit 6 (64)  — Flow sensor
    - bit 7 (128) — Repeated mails
    - bit 8 (256) — DMX extension

    Default is 0 so the mock's emitted CSV stays byte-compatible with
    ``tests/fixtures/get_state.csv``; client code that depends on a flag
    constructs ``MockState(config_other_enable=…)`` to turn it on.
    """

    relay_enabled: list[bool] = field(default_factory=lambda: [False] * NUM_RELAY_BITS)
    relay_on: list[bool] = field(default_factory=lambda: [False] * NUM_RELAY_BITS)
    dmx: list[int] = field(default_factory=lambda: [0] * NUM_DMX_CHANNELS)
    config_other_enable: int = 0
    monotonic: Callable[[], float] = field(default=time.monotonic)
    _t0: float = field(init=False)

    def __post_init__(self) -> None:
        self._t0 = self.monotonic()

    def elapsed_seconds(self) -> float:
        """Seconds since the mock started, using the injected clock."""
        return self.monotonic() - self._t0

    def apply_ena(self, *, enable_mask: int, on_mask: int) -> None:
        """Apply a `usrcfg.cgi` ENA payload to the relay bitmaps.

        ``enable_mask`` selects which relays are in manual mode (bit set =
        manual, bit clear = auto); ``on_mask`` selects the ones whose output
        is currently driven.
        """
        for bit in range(NUM_RELAY_BITS):
            mask = 1 << bit
            self.relay_enabled[bit] = bool(enable_mask & mask)
            self.relay_on[bit] = bool(on_mask & mask)

    def csv_relay_value(self, bit: int) -> int:
        """Encode the relay's state as the 0–3 value the controller emits.

        Both bits independently follow the incoming ENA payload, so all four
        combinations are reachable:

        - 0 = Auto (off)  ``relay_enabled=False, relay_on=False``
        - 1 = Auto (on)   ``relay_enabled=False, relay_on=True``
        - 2 = Off         ``relay_enabled=True,  relay_on=False``
        - 3 = On          ``relay_enabled=True,  relay_on=True``

        The mock starts at all-zero and there's no internal scheduler that
        would set `Auto on`, but a client preserving an existing relay state
        via `GetStateData.determine_overall_relay_bit_state()` may legitimately
        POST `ENA=0,1<<bit`, which lands here as 1.
        """
        manual = self.relay_enabled[bit]
        on = self.relay_on[bit]
        return (2 if manual else 0) | (1 if on else 0)

    def apply_dmx(self, *, channels_1_8: list[int], channels_9_16: list[int]) -> None:
        """Apply a `usrcfg.cgi` DMX payload.

        Each list must contain exactly 8 values. Out-of-range values are
        clamped to [0, 255], matching the controller's hardware limit.
        """
        if len(channels_1_8) != 8 or len(channels_9_16) != 8:
            raise ValueError(
                f"DMX payload must contain 8 + 8 values; got "
                f"{len(channels_1_8)} + {len(channels_9_16)}"
            )
        for index, value in enumerate(channels_1_8 + channels_9_16):
            self.dmx[index] = max(0, min(255, value))
