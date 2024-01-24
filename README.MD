# Climate remote control

[![codecov](https://codecov.io/gh/avzhuiko/ac-remote/graph/badge.svg?token=6OX82SOJTB)](https://codecov.io/gh/avzhuiko/ac-remote)
[![Donate with PayPal][paypalbadge]][paypal]
[![Donate with Buy Me A Coffee][buymeacoffeebadge]][buymeacoffee]

This integration allows using remote control emulators (such as BroadLink) with climate units.
It uses home assistant service "Remote: Send command", so no matter which manufacturer is used for it.
When you define integration you will get default home assistant climate card.

**This component will set up the following platforms.**

| Platform  | Description                                       |
| --------- | ------------------------------------------------- |
| `climate` | For controlling AC unit via default climate card. |
| `button`  | For swing toggle mode.                            |

# Installation

## Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `climate_remote_control`.
1. Download _all_ the files from the `custom_components/climate_remote_control/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Climate remote control"

## Via HACS custom repository

This method allows you to get updates directly on the HACS main page

1. If HACS is not installed yet, download it following the instructions on https://hacs.xyz/docs/setup/download
1. Proceed to the HACS initial configuration following the instructions on https://hacs.xyz/docs/configuration/basic
1. On your sidebar go to HACS
1. Click on the 3 dots in the top right corner.
1. Select "Custom repositories"
1. Fill URL field with https://github.com/avzhuiko/climate-remote-control.
1. In category field select "Integration".
1. Click the "ADD" button.
1. You can now click on Add card in the bottom right corner and search for Climate remote control.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Climate remote control"

# Configuration

Just follow config flow

# Modes description

## Temperature

There are 3 modes for temperature control:

- none - if your climate entity does not have settings which is connected with the temperature.
- target - if you can set the target temperature for your climate entity.
- range - if you can set the range of target temperatures (minimum and maximum)

## Swing

Sometimes the climate units have modes for swing, but often you have the only one button for swing direction
which can start or stop swinging. So, we have 3 modes for it:

- none - swing does not support.
- toggle - your remote control have button (per direction) which enable or disable swing, but you don't have any signs
  about it. Also, it can be named as _stateless_ mode.
- state - if you have codes which can set a specific mode.

# Grouping attributes

When you change one of a climate parameter it can change other if it didn't match with remote control.
For example, you set up on your AC temperature 25C, medium fan and heat mode. Remote control has the same data on the
screen. Now you press increase temperature button on remote control, but AC didn't receive it (you can close
transmitter by your hand). After that you decide increase fan speed and now your AC with 26C, high fan and heat mode.
That happens because temperature, fan speed and HVAC mode are sent together in one command.

# Commands

When you change climate parameter the integration tries to find command for sending via HA service "Remote: send
command". You can find formats for parameters below:

| Parameter         | Format                                                                                       | Example             |
| ----------------- | -------------------------------------------------------------------------------------------- | ------------------- |
| HVAC mode         | mode:\<selected HVAC mode\>                                                                  | mode:heat           |
| Fan               | fan:\<selected fan mode\>                                                                    | fan:medium          |
| Swing             | swing:\<selected swing mode\>                                                                | swing:vertical      |
| Temperature       | temp:\<target temperature value with precision 1\>                                           | temp:24.0           |
| Temperature range | temprange:<low temperature value with precision 1>:<high temperature value with precision 1> | temprange:22.0:24.0 |
| Humidity (TBD)    | humid:\<target humidity level\>                                                              | humid:50            |

## Command structure

If changed parameter belongs to grouping attributes, all parameters from grouping attributes will be concatenated via
_underscore_. Ex: mode:heat_fan:medium_temp:24.0 for grouping attributes=[HVAC mode, Fan mode, Target temperature].  
**NOTE:** Order in grouping attributes is important because of concatenation order.

## Learning commands

See [Broadlink learning commands](https://www.home-assistant.io/integrations/broadlink/#learning-commands).

## Logs

If command hasn't been learned, the integration will log it with WARN level.  
Ex: Command "mode:heat_fan:low_temp:25.0" for device "LG_ES-H126LLA0" not found. You should learn it.

---

[paypal]: https://www.paypal.com/donate/?hosted_button_id=BH5J26BSR2734
[paypalbadge]: https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal
[buymeacoffee]: https://www.buymeacoffee.com/avzhuikow
[buymeacoffeebadge]: https://img.shields.io/badge/Donate-Buy%20me%20a%20coffee-yellow?logo=buy-me-a-coffee
