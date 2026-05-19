"""Pure functions producing slow, realistic drift on the mock controller's sensors.

All values are returned in **natural units** (pH units, mV, °C). The CSV
renderer is responsible for converting them back to the raw integers the
controller would emit, applying the inverse of `(raw * gain) + offset`.

The drift model is `center + amplitude * sin(2π * t / period)` for each
sensor — deterministic and stateless, so two clients that hit the mock at the
same time see the same values, and `*_PERIOD_SECONDS` corresponds to one full
cycle.
"""

import math

PH_CENTER = 7.40
PH_AMPLITUDE = 0.10
PH_PERIOD_SECONDS = 600.0

REDOX_CENTER_MV = 700.0
REDOX_AMPLITUDE_MV = 25.0
REDOX_PERIOD_SECONDS = 300.0

CPU_TEMP_CENTER_C = 30.0
CPU_TEMP_AMPLITUDE_C = 2.0
CPU_TEMP_PERIOD_SECONDS = 1800.0

PUMP_TEMP_CENTER_C = 27.0
PUMP_TEMP_AMPLITUDE_C = 1.0
PUMP_TEMP_PERIOD_SECONDS = 1800.0


def _phase(elapsed_seconds: float, period_seconds: float) -> float:
    return math.sin(2.0 * math.pi * elapsed_seconds / period_seconds)


def ph(elapsed_seconds: float) -> float:
    """Drifted pH value, oscillating in the WHO-recommended 7.30–7.50 band."""
    return PH_CENTER + PH_AMPLITUDE * _phase(elapsed_seconds, PH_PERIOD_SECONDS)


def redox_mv(elapsed_seconds: float) -> float:
    """Drifted redox/ORP value in millivolts (675–725 mV band)."""
    return REDOX_CENTER_MV + REDOX_AMPLITUDE_MV * _phase(elapsed_seconds, REDOX_PERIOD_SECONDS)


def cpu_temp_c(elapsed_seconds: float) -> float:
    """Drifted controller CPU temperature in °C (28–32 °C band)."""
    return CPU_TEMP_CENTER_C + CPU_TEMP_AMPLITUDE_C * _phase(
        elapsed_seconds, CPU_TEMP_PERIOD_SECONDS
    )


def pump_temp_c(elapsed_seconds: float) -> float:
    """Drifted temperature for the pump-mounted sensor (°C, 26–28 °C band).

    The fixture's column 8 is labeled ``Pumpe`` with unit ``C`` — the
    controller categorizes columns 8–15 as temperature sensors. Most pool
    installations wire a flow/water temperature probe here, so a typical
    pool-water range is the sensible drift target. Real deployments may
    instead measure pump-motor temperature on this channel; the mock's
    range is wide enough that either reading looks plausible at a glance.
    """
    return PUMP_TEMP_CENTER_C + PUMP_TEMP_AMPLITUDE_C * _phase(
        elapsed_seconds, PUMP_TEMP_PERIOD_SECONDS
    )


def packed_clock_value(hour: int, minute: int) -> int:
    """Encode a wall-clock time as the integer the controller emits in column 0.

    The controller stores time as ``hour * 256 + minute`` in the Time column;
    `GetStateData.time` decodes it back to the ``"HH:MM"`` display string.
    """
    return hour * 256 + minute


def sensors(elapsed_seconds: float) -> dict[str, float]:
    """Return all drifted sensor values keyed by short name.

    Convenience wrapper around the individual functions for callers that want
    a single dict rather than four separate calls.
    """
    return {
        "ph": ph(elapsed_seconds),
        "redox_mv": redox_mv(elapsed_seconds),
        "cpu_temp_c": cpu_temp_c(elapsed_seconds),
        "pump_temp_c": pump_temp_c(elapsed_seconds),
    }
