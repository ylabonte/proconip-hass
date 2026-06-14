"""Constants for proconip."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "ProCon.IP Pool Controller"
DOMAIN = "proconip_pool_controller"
VERSION = "2.1.0"  # x-release-please-version
ATTRIBUTION = "Data provided by your Pool Digital ProCon.IP (https://www.pooldigital.de)"

# DMX
DMX_DEBOUNCE_SECONDS = 0.15
DMX_QUIET_WINDOW_SECONDS = 1.5
CONF_DMX_LIGHTS = "dmx_lights"
# Single source of truth for supported DMX light types and how many
# consecutive DMX channels each one occupies. config_flow.py validates
# against this; light.py reads/writes that many channels per entity.
LIGHT_TYPE_CHANNEL_COUNT: dict[str, int] = {"dimmer": 1, "rgb": 3, "rgbw": 4}

# Fault state (SYSINFO[4]) — the controller's bit-encoded GUI warning lamps
# (green/yellow/red) plus an NTP fault bit, surfaced by the proconip library as
# `GetStateData.ntp_fault_state`. The severity-threshold select lets the user
# choose the lowest lamp severity that flips the Problem binary_sensor on.
PROBLEM_SEVERITY_BITS: dict[str, int] = {"green": 0x1, "yellow": 0x2, "red": 0x4}
# Ascending severity; the select offers these and the binary_sensor trips when
# the active severity is at or above the chosen level. Default: yellow.
PROBLEM_SEVERITY_OPTIONS: list[str] = ["green", "yellow", "red"]
PROBLEM_SEVERITY_DEFAULT = "yellow"
NTP_FAULT_BIT = 0x10000  # SYSINFO[4] bit 16: set = no time from NTP server
# Stable, language-agnostic states for the fault_state enum sensor. Labels live
# in translations/<lang>.json under `entity.sensor.fault_state.state`.
FAULT_STATE_OPTIONS: list[str] = ["ok", "info", "warning", "error", "ntp_fault"]
