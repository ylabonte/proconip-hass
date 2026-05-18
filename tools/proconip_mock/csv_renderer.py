"""Render a `MockState` plus drift into the CSV bodies the controller would emit.

The structural template (column count, names, units, calibration rows, plus the
SYSINFO header) is loaded once from `tests/fixtures/get_state.csv` and cached
for the lifetime of the process. Each render substitutes a freshly-computed
values row (drifted sensors, current relay state) into that template, leaving
everything else identical to what a real controller would send.

Calibration is inverted on the way out: drift functions return values in
natural units, but the CSV stores them as the raw integers the parser will
convert back via `(raw * gain) + offset`. So we compute
``raw = (natural - offset) / gain`` for the columns we drive, and pass the
fixture's existing raw value through unchanged for the rest.
"""

from datetime import datetime
from datetime import time as dt_time
from functools import lru_cache
from pathlib import Path

from . import drift
from .state import MockState

REPO_ROOT = Path(__file__).resolve().parents[2]
GET_STATE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "get_state.csv"

_COL_TIME = 0
_COL_CPU_TEMP = 5
_COL_REDOX = 6
_COL_PH = 7
# Column 8 (`Pumpe`, unit °C) is in the controller's temperature category
# (columns 8–15). Despite the historical "pump flow" framing, the fixture and
# the parser both treat this as a temperature reading.
_COL_PUMP_TEMP = 8

_INTERNAL_RELAY_COLUMNS = range(16, 24)  # bits 0–7
_EXTERNAL_RELAY_COLUMNS = range(28, 36)  # bits 8–15


@lru_cache(maxsize=1)
def _load_template() -> tuple[
    list[str], list[str], list[str], list[float], list[float], list[float]
]:
    """Return the six CSV rows from the fixture as parsed lists.

    Cached so repeated `render_get_state` calls don't re-hit disk. Call
    ``_load_template.cache_clear()`` if you ever need to pick up a fresh
    fixture (only useful inside tests that rewrite the fixture file).
    """
    text = GET_STATE_FIXTURE.read_text()
    lines = [line for line in text.splitlines() if line.strip()]
    sysinfo = lines[0].split(",")
    names = lines[1].split(",")
    units = lines[2].split(",")
    offsets = [float(v) for v in lines[3].split(",")]
    gains = [float(v) for v in lines[4].split(",")]
    raw_values = [float(v) for v in lines[5].split(",")]
    return sysinfo, names, units, offsets, gains, raw_values


def _natural_to_raw(natural: float, offset: float, gain: float) -> float:
    """Invert `(raw * gain) + offset` so the parser recovers ``natural``."""
    return (natural - offset) / gain


def render_get_state(state: MockState, *, wall_clock: dt_time | None = None) -> str:
    """Render the CSV body the controller would return on `GET /GetState.csv`.

    Args:
        state: Current mock state. Drift values are derived from
            ``state.elapsed_seconds()``; relay columns are derived from
            ``state.csv_relay_value()``.
        wall_clock: Override the time-of-day used for column 0. Defaults to
            the host's current local time. Tests pin this to get a stable
            ``HH:MM`` value.
    """
    sysinfo, names, units, offsets, gains, fixture_raw = _load_template()
    elapsed = state.elapsed_seconds()
    sensors = drift.sensors(elapsed)
    now = wall_clock or datetime.now().time()

    new_raw = list(fixture_raw)
    new_raw[_COL_TIME] = float(drift.packed_clock_value(hour=now.hour, minute=now.minute))
    new_raw[_COL_CPU_TEMP] = _natural_to_raw(
        sensors["cpu_temp_c"], offsets[_COL_CPU_TEMP], gains[_COL_CPU_TEMP]
    )
    new_raw[_COL_REDOX] = _natural_to_raw(
        sensors["redox_mv"], offsets[_COL_REDOX], gains[_COL_REDOX]
    )
    new_raw[_COL_PH] = _natural_to_raw(sensors["ph"], offsets[_COL_PH], gains[_COL_PH])
    new_raw[_COL_PUMP_TEMP] = _natural_to_raw(
        sensors["pump_temp_c"], offsets[_COL_PUMP_TEMP], gains[_COL_PUMP_TEMP]
    )

    for column in _INTERNAL_RELAY_COLUMNS:
        new_raw[column] = float(state.csv_relay_value(column - 16))
    for column in _EXTERNAL_RELAY_COLUMNS:
        new_raw[column] = float(state.csv_relay_value(column - 28 + 8))

    # SYSINFO[5] is the `config_other_enable` bitfield consumed by
    # `GetStateData.is_*_enabled()`. The template is cached, so emit a
    # fresh copy with the runtime override applied.
    sysinfo_row = list(sysinfo)
    sysinfo_row[5] = str(state.config_other_enable)

    rows = [
        ",".join(sysinfo_row),
        ",".join(names),
        ",".join(units),
        ",".join(_format_float(v) for v in offsets),
        ",".join(_format_float(v) for v in gains),
        ",".join(_format_float(v) for v in new_raw),
    ]
    return "\n".join(rows) + "\n"


def render_get_dmx(state: MockState) -> str:
    """Render the single-line CSV body for `GET /GetDmx.csv`."""
    return ",".join(str(v) for v in state.dmx) + "\n"


def _format_float(value: float) -> str:
    """Render a float compactly — integers stay integer-shaped."""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(value)
