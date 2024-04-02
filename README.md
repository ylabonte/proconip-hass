# ProCon.IP Pool Controller

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacs-badge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymeacoffee-badge]][buymeacoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

![ProCon.IP Home Assistant Integration][logo]

**This component will set up the following platforms.**

| Platform        | Description                                         |
|-----------------|-----------------------------------------------------|
| `binary_sensor` | Show flags/binary data from `GetState.csv` API.     |
| `sensor`        | Show various data from `GetState.csv` API.          |
| `switch`        | `On`/`Off` and `Auto`/`Manual` switches for relays. |
| `select`        | `Auto`/`On`/`Off` dropdowns for relays.             |
| `number`        | Dosage relay timer/countdown in seconds.            |

## Table of contents
* [Screenshots](#screenshots)
* [Install with HACS (recommended)](#install-with-hacs-recommended)
* [Manual install](#manual-installation)
* [Configuration](#configuration-is-done-in-the-ui)
* [Common problems/erros and the solution](#common-problemserrors-and-the-solution)
* [Getting support for this integration](#getting-support-for-this-integration)
* [Supporting this integration](#supporting-this-integration)
* [Contributing](#contributions-are-welcome)
* [A brief description of the ProCon.IP](#a-brief-description-of-the-proconip-pool-controller)
* [Changelog](#changelog)
* [Credits](#credits)

## Screenshots

| Integration overview |
|-|
| [![Integration overview][screenshot1]][screenshot1] |

| controls | sensors | more sensors |
|-|-|-|
| [![Integration device controls][screenshot2]][screenshot2] | [![Integration device sensors][screenshot3]][screenshot3] | [![More integration device sensors][screenshot4]][screenshot4] |

## Install with HACS (recommended)
If you have not already done so, you should first install [HACS (Home Assistant Community Store)](https://hacs.xyz/).
It is the usual way to install custom integrations and keep them up to date.

1. Open HACS Settings and add this repository.
2. Open HACS again and go to "Integrations".
3. Search for "ProCon.IP Pool Controller".
4. Install the "ProCon.IP Pool Controller" integration.
5. Restart Home Assistant
6. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "ProCon.IP Pool Controller"

## Manual Installation
If you are running Home Assistant Core only or prefer manual installation for some other reason, keep in mind that you
also have to manually update the integration. So if HACS is an option for, use it!

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `proconip_pool_controller`.
4. Download _all_ the files from the `custom_components/proconip_pool_controller/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "ProCon.IP Pool Controller"

## Configuration is done in the UI
If you follow the installation guideline, the last step will lead to the configuration.
Since version 1.2.0 adding/running multiple instances of the integration is supported (eg. in case you have one
controller for your swimming pool and a second one for your jacuzzi).

## Common problems/errors and the solution
| Problem || Solution |
|-|-|-|
| Error: "Cannot permanently switch on a dosage relay" | → | Check deactivated dosage controls and select a different relay there. _Example: You are using chlorine and pH- dosage control and have pH+ deactivated; check which relay is selected for pH+ control and select the same as for pH- control or some unused relay._ (See also [proconip-dosage-trap.png][screenshot-solution1]) |

<!---->

## Getting support for this integration
If you have trouble with this integration and want to get help, please raise an [issue on github][issues].
This way others can benefit from the solution, too.

## Supporting this integration
If you want to support this integration or say thank you, you can:

[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 40px !important;width: 144px !important;" >](https://www.buymeacoffee.com/ylabonte)

## Contributions are welcome!
If you want to contribute to this project please read the [Contribution guidelines](CONTRIBUTING.md).

## A brief description of the ProCon.IP pool controller

![picture]

The ProCon.IP pool controller is a low budget network attached control unit for
home swimming pools. With its software switched relays, it can control
multiple pumps (for the pool filter and different dosage aspects) either
simply planned per time schedule or depending on a reading/value from one of
its many input channels for measurements (eg. i/o flow sensors, Dallas 1-Wire
thermometers, redox and pH electrodes). At least there is also the option to
switch these relays on demand, which makes them also applicable for switching
lights (or anything else you want) on/off.
Not all of its functionality is reachable via API. In fact there is one
documented API for reading (polling) values as CSV (`/GetState.csv`) and another
one for switching on/off and on with timer.
But I could not find the second one for a while. So not even pretty, but
functional: The ProCon.IP has two native web interfaces, which can be
analyzed, to some kind of reverse engineer a given functionality (like
switching the relays).

For more information see the following links (sorry it's only in german;
haven't found an english documentation/information so far):

* [pooldigital.de webshop](https://www.pooldigital.de/shop/poolsteuerungen/procon.ip/35/procon.ip-webbasierte-poolsteuerung-/-dosieranlage)
* [pooldigital.de forum](http://forum.pooldigital.de/)

## Changelog

### Version 1.2.0 (2024-02-12)
WARNING: This update will create new entities. I could not find a way to remove the old entities programatically, so I
apologize, but you will have to remove the obsolete entities manually (you can easily filter for them and remove all at
once).

* Require Home Assistant Core 2024.2.1 or newer.
* Fix configuration/setup bug (issue #28).
* Fix multi instance support.

### Earlier Versions
All earlier versions have known bugs. Please update!
For more information about

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
[logo]: https://github.com/ylabonte/proconip-hass/raw/main/logo.png
[picture]: https://github.com/ylabonte/proconip-hass/raw/main/picture.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/ylabonte/proconip-hass.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Yannic%20Labonte%20(%40ylabonte)-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/ylabonte/proconip-hass.svg?style=for-the-badge
[releases]: https://github.com/ylabonte/proconip-hass/releases
[user_profile]: https://github.com/ylabonte
[issues]: https://github.com/ylabonte/proconip-hass/issues
[screenshot1]: https://raw.githubusercontent.com/ylabonte/proconip-hass/main/screenshots/screenshots/ha-integration-overview.png
[screenshot2]: https://raw.githubusercontent.com/ylabonte/proconip-hass/main/screenshots/screenshots/device-controls.png
[screenshot3]: https://raw.githubusercontent.com/ylabonte/proconip-hass/main/screenshots/screenshots/device-sensors.png
[screenshot4]: https://raw.githubusercontent.com/ylabonte/proconip-hass/main/screenshots/screenshots/device-sensors2.png
[screenshot-solution1]: https://raw.githubusercontent.com/ylabonte/proconip-hass/main/screenshots/screenshots/proconip-dosage-trap.png