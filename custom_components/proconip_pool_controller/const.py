"""Constants for proconip."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "ProCon.IP Pool Controller"
DOMAIN = "proconip_pool_controller"
VERSION = "2.0.0"
ATTRIBUTION = "Data provided by your Pool Digital ProCon.IP (https://www.pooldigital.de)"

# DMX
DMX_DEBOUNCE_SECONDS = 0.15
DMX_QUIET_WINDOW_SECONDS = 1.5
CONF_DMX_LIGHTS = "dmx_lights"
