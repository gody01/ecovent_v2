[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

# Blauberg EcoVent VENTO Expert A50/80/100 V.2 Fans
Home Assistant Integration. Integration for newest Fans with api version 2


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
  - filter_timer_reset (Reset air filter timer)
  - reset_alarms (Reset fan Vento alarms)
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
* Document live TwinFresh V.2 beeper testing: writing `0x0306=00` or `0x0306=02`
  did not disable command beeps reliably on the tested device, so the integration
  does not expose a writable beeper control.
