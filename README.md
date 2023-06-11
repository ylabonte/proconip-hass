# ProCon.IP Pool Controller

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacs-badge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymeacoffee-badge]][buymeacoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**This component will set up the following platforms.**

| Platform        | Description                                                           |
| --------------- |-----------------------------------------------------------------------|
| `binary_sensor` | Show flags/binary data from `GetState.csv` API.                       |
| `sensor`        | Show various data from `GetState.csv` API.                            |
| `switch`        | Switch relays `On`/`Off` and toggle between `Auto` and `Manual` mode. |

![picture]

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `proconip`.
4. Download _all_ the files from the `custom_components/integration_blueprint/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

## Configuration is done in the UI

<!---->

## Support for this integration

If you have trouble with this integration and want to get support, you can open an [issue on github][issues], so others
can benefit from the solution, too.

## Support this integration

If you want to support this integration or say thank you, you can:

[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 40px !important;width: 144px !important;" >](https://www.buymeacoffee.com/ylabonte)

### Contributions are welcome!

If you want to contribute to this project please read the [Contribution guidelines](CONTRIBUTING.md).
And if you need a starting point, you could take a look at the [Home Assistant documentation for the file structure when building integrations][building_integration_docs]
or read the [Home Assistant Custom Component Cookiecutter documentation][cookiecutter_docs].

## Credits

This project was built upon the [custom integration blueprint][updated_integration_blueprint] of [@Ludeeus](https://github.com/ludeeus).

---

[updated_integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[integration_blueprint]: https://github.com/custom-components/integration_blueprint
[buymeacoffee]: https://www.buymeacoffee.com/ylabonte
[buymeacoffee-badge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/ylabonte/homeassistant-proconip.svg?style=for-the-badge
[commits]: https://github.com/ylabonte/homeassistant-proconip/commits/main
[hacs]: https://hacs.xyz
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[projectlogo]: logo.png
[picture]: picture.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/ylabonte/homeassistant-proconip.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Yannic%20Labonte%20(%40ylabonte)-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ylabonte/homeassistant-proconip.svg?style=for-the-badge
[releases]: https://github.com/ylabonte/homeassistant-proconip/releases
[user_profile]: https://github.com/ylabonte
[issues]: https://github.com/ylabonte/proconip-hass/issues
[cookiecutter_docs]: https://cookiecutter-homeassistant-custom-component.readthedocs.io/en/stable/quickstart.html
[building_integration_docs]: https://developers.home-assistant.io/docs/creating_integration_file_structure
