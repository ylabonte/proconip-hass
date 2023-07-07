# ProCon.IP Pool Controller

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacs-badge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymeacoffee-badge]][buymeacoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

![ProCon.IP Home Assistant Integration](./logo.png)

**This component will set up the following platforms.**

| Platform        | Description                                         |
|-----------------|-----------------------------------------------------|
| `binary_sensor` | Show flags/binary data from `GetState.csv` API.     |
| `sensor`        | Show various data from `GetState.csv` API.          |
| `switch`        | `On`/`Off` and `Auto`/`Manual` switches for relays. |
| `select`        | `Auto`/`On`/`Off` dropdowns for relays.             |
| `number`        | Dosage relay timer/countdown in seconds.            |

![picture]

## Install with HACS (recommended)

1. Open HACS Settings and add this repository.
2. Open HACS again and go to "Integrations".
3. Search for "ProCon.IP Pool Controller".
4. Install the "ProCon.IP Pool Controller" integration.
5. Restart Home Assistant
6. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "ProCon.IP Pool Controller"

## Manual Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `proconip_pool_controller`.
4. Download _all_ the files from the `custom_components/proconip_pool_controller/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "ProCon.IP Pool Controller"

## Configuration is done in the UI

<!---->

## Support for this integration

If you have trouble with this integration and want to get support, you can open an [issue on github][issues], so others
can benefit from the solution, too.

## Support this integration

If you want to support this integration or say thank you, you can:

[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 40px !important;width: 144px !important;" >](https://www.buymeacoffee.com/ylabonte)

## Contributions are welcome!

If you want to contribute to this project please read the [Contribution guidelines](CONTRIBUTING.md).

## Credits

This project was generated using the [integration blueprint][integration_blueprint] from [@Ludeeus](https://github.com/ludeeus).

---

[integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[buymeacoffee]: https://www.buymeacoffee.com/ylabonte
[buymeacoffee-badge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/ylabonte/proconip-hass.svg?style=for-the-badge
[commits]: https://github.com/ylabonte/proconip-hass/commits/main
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[picture]: picture.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/ylabonte/proconip-hass.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Yannic%20Labonte%20(%40ylabonte)-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ylabonte/proconip-hass.svg?style=for-the-badge
[releases]: https://github.com/ylabonte/proconip-hass/releases
[user_profile]: https://github.com/ylabonte
[issues]: https://github.com/ylabonte/proconip-hass/issues