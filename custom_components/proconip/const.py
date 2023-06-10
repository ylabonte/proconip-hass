"""Constants for ProCon.IP Pool Controller."""
# Base component constants
NAME = "ProCon.IP Pool Controller"
MANUFACTURER = "Pool Digital"
DOMAIN = "proconip"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.0.1-alpha.3"

ATTRIBUTION = "Data provided by your ProCon.IP pool controller from Pool Digital."
ISSUE_URL = "https://github.com/ylabonte/proconip/issues"

# Icons
ICON = "mdi:format-quote-close"
ELECTRODE_ICON = "mdi:gauge"
RELAY_ICON = "mdi:light-switch"
RELAY_MODE_ICON = "mdi:refresh-auto"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
BINARY_SENSOR = "binary_sensor"
SENSOR = "sensor"
SWITCH = "switch"
PLATFORMS = [BINARY_SENSOR, SENSOR, SWITCH]


# Configuration and options
CONF_ENABLED = "enabled"
CONF_BASE_URL = "base_url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
