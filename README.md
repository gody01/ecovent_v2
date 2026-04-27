[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

# Blauberg EcoVent VENTO Expert A50/80/100 V.2 Fans
Home Assistant Integration. Integration for newest Fans with api version 2

This integration talks to the local BGCP/UDP Wi-Fi protocol used by devices on
the Blauberg Group / VENTS platform. VENTS is an official sibling brand, not
just a Blauberg relabel. The exact feature set is selected from the protocol
device type reported by parameter `0x00B9`.

## Device names and search keywords

Use this list for search/discovery. Some third-party/OEM names are recorded as
compatibility evidence or candidates; if your device is listed as a candidate,
please open an issue with its reported unit type (`0x00B9`) so it can be mapped
confidently.

Official Blauberg / VENTS platform families and names:

* Blauberg Ventilatoren, VENTS, Vento, VENTO, TwinFresh, EcoVent
* Blauberg VENTO Expert, VENTO Expert A50-1 W V.2, VENTO Expert A50-1 S10 W V.2,
  VENTO Expert A85-1 S10 W V.2, VENTO Expert A100-1 S10 W V.2,
  VENTO Expert A50-1 W V.3
* VENTS TwinFresh Expert, TwinFresh Expert RW1-50 V.2,
  TwinFresh Expert RW1-85 V.2, TwinFresh Expert RW1-100 V.2,
  TwinFresh Expert RW1-50 V.3
* Blauberg VENTO Expert DUO A30-1 W V.2,
  VENTO Expert DUO A30-1 S10 W V.2,
  VENTS TwinFresh Expert Duo RW1-30 V.2
* Blauberg VENTO Expert A30 W V.2, VENTO Expert A30 S10 W V.2,
  VENTS TwinFresh Expert RW-30 V.2
* Blauberg VENTO inHome, VENTO inHome W, VENTO inHome mini,
  VENTO inHome mini W, VENTO inHome 100, VENTO inHome 160
* VENTS TwinFresh Atmo, TwinFresh Atmo 100, TwinFresh Atmo 160,
  TwinFresh Atmo mini, TwinFresh Atmo Wi-Fi, TwinFresh Atmo mini Wi-Fi
* VENTS TwinFresh Style Wi-Fi, TwinFresh Style Frost Wi-Fi,
  TwinFresh Style Wi-Fi mini
* Blauberg Smart Wi-Fi, Smart IR Wi-Fi, VENTS iFan Wi-Fi,
  VENTS iFan Move Wi-Fi
* Blauberg Freshbox 100 WiFi, Freshbox 100 ERV WiFi, Freshbox E-100 WiFi,
  Freshbox E1-100 WiFi, Freshbox E2-100 WiFi
* VENTS Micra 100 WiFi, Micra 100 ERV WiFi, Micra 100 E WiFi,
  Micra 100 E1 WiFi, Micra 100 E2 WiFi
* VENTS Breezy, Breezy 160, Breezy 160-E, Breezy 160-E Smart,
  Breezy 200-E, Breezy 200-E Smart, Breezy Eco 160, Breezy Eco 200
* Blauberg Freshpoint, Freshpoint 160, Freshpoint 160-E,
  Freshpoint 160-E Pro, Freshpoint 200, Freshpoint 200-E,
  Freshpoint 200-E Pro, Freshpoint Eco 160, Freshpoint Eco 200
* VENTS Arc Smart, Arc Smart white, Arc Smart black,
  Blauberg O2 Supreme, O2 Supreme white, O2 Supreme black

External relabels and OEM names tracked as evidence or candidates:

* OXXIFY.smart 50, Oxxify.smart 50, Oxxify smart 50,
  Oxxify.smart 30, oxxify.smart 50k, OXXIFY.pro 50, OXXIFY.eco 50
* SIKU RV, SIKU RV 50 W Pro WiFi V2, SIKU RV 50 W PRO WIFI V2,
  SIKU RV 30 DW Pro Duo WiFi V2, SIKU RV 30 DW PRO DUO WIFI V2,
  SIKU RV 25 W Pro WiFi V2
* Flexit Roomie One WiFi V2, Roomie One Wifi V2, Roomie Dual Wifi,
  Roomie Dual WiFi V2, Flexit Aura, Flexit Muto
* DUKA One, DUKA One S6W, DUKA One S6BW, DUKA One S4 Wi-Fi,
  DUKA One S6 Wi-Fi, DUKA One Pro 25 S Wi-Fi, DUKA One Pro 50 S Wi-Fi
* RL Raumklima, RL PRO-Serie, RL 50RVW, RL 30DVW, RL 25RVW
* Winzel V.2, Winzel Expert WiFi RW1-50 P,
  Blauberg Winzel Expert WiFi RW1-50 P
* NIBE DVC 10, NIBE DVC 10-50W, NIBE DVC 10-D30W

# Tested on:
* Blauberg VENTO Expert A50-1 W V.2

# Currently supported:
* UI integration setup
* turn_on/turn_off
* Preset modes:
  - low
  - medium
  - high
  - manual
* In manual mode speed percentage
* Oscillating
  - When on, Fans are in 'heat_recovery' airflow
* Direction
  - "forward" means 'ventilation' airflow
  - "reverse" means 'air_supply' airflow
* Weekly schedule support on devices exposing `0x0072` / `0x0077`
  - one visible schedule entity for the weekly schedule
  - open the schedule entity's more-info dialog to edit the weekly schedule

# Changelog
version 0.0.5:
* Added sensors:
  - Humidity
  - Fan1 speed
  - Fan2 speed
  - Airflow

* Changed
  - Update method to DataUpdateCoordinator for reduced request to FAN device

version 0.1.0:
* Added sensors:
  - battery_voltage
  - timer_counter
  - humidity_treshold
  - filter_timer_countdown
  - boost_time
  - machine_hours
  - analogV
  - analogV_treshold

All sensors are categorised and some are disabled by default.

version 0.2.0:
* Added binary sensors:
  - boost_status
  - timer_mode
  - humidity_sensor_state
  - relay_sensor_state
  - relay_status
  - filter_replacement_status
  - alarm_status
  - cloud_server_state
  - humidity_status
  - analogV_status

All sensors are categorised and some are disabled by default.

* Changed:
  - Removed default IP address from config input field Host
  - Added some icon defintions to sensors
  - Battery percent caluclation

version 0.2.0:
* Added services
  - filter_timer_reset (Reset filter timer)
  - reset_alarms (Reset alarms)
* Changed:
  - From binary sensor to switch:
    - humidity_sensor_state
    - relay_sensor_state
    - analogV_sensor_state

version 0.4.0
* Added broadcast devices search
  - hack, that searches on network, if string: <broadcast> is entered
    instead of IP address
  - this is not yer proper HomaAssistant Auto Discovery, but it seems to
    work on my network

version 0.5.0
* Mainly fixes from autmated checks and hopefuly some latency improvements
  - Removed await coordinator in turn_on/turn_off and other interactive
    functions
  - Some cleanup in config_flow
  - Removed deprecated set_speed functions
  - Fix error if _battery_voltage is None

version 0.6.0
* Timeout Loop bailout

version 0.7.0
* Fix manifest, to require correct pyEcovent version (0.9.14)

version 0.8.0
* Removed calling blocking sleep in event loop

version 0.9.0
* Cleanup some definitions for HA checks

version 0.9.1
* replaced hass.config_entries.async_setup_platforms with await hass.config_entries.async_forward_entry_setups
* thanks to @berndulum for issue report

version 0.9.2
* fix name of sensor leaking to device name (hopefuly)

version 0.9.3
* bump requirements to pyEcoventV2==0.9.16 (fixed boost_status reading)

version 0.9.5
* Merged pull request for file "protocol.md" by @Styx85.

version 0.9.6
* Fix: Humidy Threshold creates errors trouble in newest HA #21
* humidity_treshold, analogV_treshold, boost_timer changed from sensor to number. Now they can be configured via HomeAssistant.

Version 0.9.7
* Updatet README.md

Version 0.9.8
* Fix number entities names.

Version 0.9.9
* more  entities names fixes.

Version 1.0.0
* some more name fixes
* fix code to be more compliant with latest HA
* some code cleanup

Version 1.0.1
* Values for humidity_threshold, analogV_threshold and boost ime read from device on initialization.

Version 1.0.2
* Fix for issue #25 VentoExpertFan does not set FanEntityFeature.TURN_OFF but implements the thurn_off method

Version 1.0.3
* Merge pull request #28 from SantaFox/main: Amended some sensors for better automations

Version 1.0.4

Version 1.0.5
* Bump pyEcoventV2 requirements to 0.9.19

Version 1.0.6
* Bump pyEcoventV2 requirements to 0.9.21, trying to resolve different lengths of returned value for filter_timer_counter

Version 1.0.7 / 1.0.8
* Bump pyyecoventv2 requirements to 0.9.22, still trying to fix 4 byte return of filter_timer_counter function

Version 1.0.9
* Bump pyyecoventv2 requirements to 0.9.23, remove beeper gueswork

Version 1.1.0
* Merged fixes from github contributors

Version 1.1.1
* Fix typos

Version 1.2.0

* Merged @AndyNew2 pull request v1.2.0 Rework ecovent library #36
** this is a massive rework of your integration:
** moved your library into the integration to avoid confusions ;-)
** There was a massive bug in the binary_sensor multiplying the update rate by 4 - 6. Therefore you had a real update rate around 10 seconds instead of the intended 1 minute ;-) This was on top of the double update before your last update ;-)
** Added job executor to free HA timings. I checked UDP async IO but do not like it. Timeout handling is really difficult with it. Since we do the updates many less now, due to a few fixed, the overhead of an executor thread is fine. This allows now reenabling sleeps for retries. Works very well now.
** Many bug fixes in the init and deinit code. Was no longer up to date for HA and would have created massive warnings soon. That is fixed now.
** Few further fixes like not updating manual speed etc. Do not remember each of them, but there had been quite a lot of them.
** Config flow has now update rate configurable and added reconfigure dialog. Set default update rate to 30 seconds (still is around 3x slower than before ;-))
** Let me know, what you think about the changes. Runs a lot better than before. This unindented fast update created together with the fix of retries many HA issues. HA is not prepared to be blocked around 5 - 10 seconds...

Version 1.2.1
* Merged @AndyNew2 pull request bugfix for initialization not using job executor and some config flow fixes #37

Version 1.2.2
* Beeper status error/write value of val varable
* fix for case, where HW returns unknown value for some statuses/states

Version 1.2.3
* Merge pull request #39 from AndyNew2/AndyNew2-Rework   
** v1.2.3 bugfix and stability improvement

Version 1.2.4
* Merge pull request #40 from AndyNew2
** added weekly_schedule_state on request
** Add weekly schedule state to VentoSwitch

Version 1.2.5
* Clean up Home Assistant entity names and categories
* Move multi-state statuses from binary sensors to enum sensors
* Expose observed beeper flag as a read-only diagnostic sensor
* Add Airflow enum state translations for cleaner UI labels
* Add fan attribute translations so the built-in direction/oscillation controls
  read as Airflow and Heat recovery
* Add Off as a Home Assistant pseudo preset mode that turns the fan off
* Skip unchanged fan commands so automations can set desired final states
  without re-sending already-active state, preset, direction, heat recovery, or
  manual percentage writes
* Switch to manual speed automatically when setting the fan percentage directly
* Keep preset percentage synchronized from the device-reported low/medium/high
  supply/exhaust setpoints instead of hiding it outside manual mode
* Correct the VENTO/TwinFresh Expert `0x0306` interpretation from beeper state to
  the PDF-documented current schedule speed; writable beeper control remains
  exposed only for profiles with a documented sound-emitter parameter.

Version 1.2.6
* Harden the vendored protocol client with better transport error handling,
  bulk-read fallback, missing-battery tolerance, and four-byte filter countdown
  parsing.
* Split protocol maps, device profiles, model metadata, sensor specs, and tests
  out of the monolithic client for easier review and maintenance.
* Add profile-aware support for Smart Wi-Fi/iFan extract fans, Breezy/Freshpoint,
  Freshbox/Micra, and Arc Smart/O2 Supreme devices.
* Expand PDF-backed model aliases and README discovery keywords for Blauberg,
  VENTS, OXXIFY, SIKU, Flexit, DUKA, RL, Winzel, and NIBE labels.
* Keep Home Assistant fan direction values separate from EcoVent protocol airflow
  values, and expose optional entities only when the active profile supports
  them.

Version 1.2.7
* Add the built-in weekly schedule editor and expose the full weekly schedule
  through a single schedule summary entity.
* Register the custom schedule frontend with a content-hashed module URL and add
  localized schedule editor strings.
* Make schedule writes bounded by sending only changed days/periods and writing
  only changed records to the device.
* Correct VENTO/TwinFresh `0x0306` to schedule speed, remove false VENTO beeper
  exposure, and keep unknown enum sensor values stable.
* Add device clock sync support and clean stale helper entities from the previous
  schedule editor approach.

Version 1.2.8
* Restore `alarm_status` as a Home Assistant `problem` binary sensor while
  keeping the enum alarm sensor for `no` / `warning` / `alarm` detail.
* Expose manual speed as a visible configuration number so it can be adjusted
  without using the live fan speed control.
* Add disabled-by-default configuration numbers for preset supply/exhaust speed
  setpoints on VENTO/TwinFresh, Breezy/Freshpoint, and Freshbox/Micra profiles.
* Encode speed setpoint writes with the active protocol profile's percent scale,
  while keeping live fan percentage control Home Assistant-native.
