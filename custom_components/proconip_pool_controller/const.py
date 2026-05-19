"""Constants for proconip."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "ProCon.IP Pool Controller"
DOMAIN = "proconip_pool_controller"
VERSION = "2.0.0"  # x-release-please-version
ATTRIBUTION = "Data provided by your Pool Digital ProCon.IP (https://www.pooldigital.de)"

# DMX
DMX_DEBOUNCE_SECONDS = 0.15
DMX_QUIET_WINDOW_SECONDS = 1.5
CONF_DMX_LIGHTS = "dmx_lights"
# Single source of truth for supported DMX light types and how many
# consecutive DMX channels each one occupies. config_flow.py validates
# against this; light.py reads/writes that many channels per entity.
LIGHT_TYPE_CHANNEL_COUNT: dict[str, int] = {"dimmer": 1, "rgb": 3, "rgbw": 4}
