[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

# Blauberg EcoVent VENTO Expert A50/80/100 V.2 Fans
Home Assistant Integration. Integration for newest Fans with api version 2

This integration talks to the local BGCP/UDP Wi-Fi protocol used by devices on
the Blauberg Group / VENTS platform and compatible units, and to VENTS A21
controllers over Modbus TCP or RTU. VENTS is an official sibling brand, not just
a Blauberg relabel. BGCP features are selected from parameter `0x00B9`; Modbus
onboarding requires the controller to report A21 value `1` in input register
`37`. Candidate OEM relationships remain labelled as candidates until device
or manufacturer evidence proves them.

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
  VENTO Expert DUO A30-1 S10 W V.2, VENTO Expert DUO A30-1 S10 W V.2 BLK,
  VENTS TwinFresh Expert Duo RW1-30 V.2
* Blauberg VENTO Expert A30 W V.2, VENTO Expert A30 S10 W V.2,
  VENTS TwinFresh Expert RW-30 V.2
* Blauberg VENTO inHome, VENTO inHome W, VENTO inHome mini,
  VENTO inHome mini W, VENTO inHome 100, VENTO inHome 160,
  VENTO inHome old
* VENTS TwinFresh Atmo, TwinFresh Atmo 100, TwinFresh Atmo 160,
  TwinFresh Atmo mini, TwinFresh Atmo Wi-Fi, TwinFresh Atmo mini Wi-Fi,
  TwinFresh Atmo old (`0x1A00`, firmware 1.0 2023-12-03)
* Blauberg RECOM 4 SR (heat recovery AHU; shown as “AHU” in the Blauberg Home
  app; reports unit type `0x0100` and firmware 0.43; four air temperatures
  and a read-only setpoint verified only from the issue #109 dump fixture)
* VENTS TwinFresh Style Wi-Fi, TwinFresh Style Frost Wi-Fi,
  TwinFresh Style Wi-Fi mini
* Blauberg Smart Wi-Fi, Smart IR Wi-Fi, VENTS iFan Wi-Fi,
  VENTS iFan Move Wi-Fi
* Blauberg Freshbox 100 WiFi, Freshbox 100 ERV WiFi, Freshbox E-100 WiFi,
  Freshbox E1-100 WiFi, Freshbox E2-100 WiFi, Freshbox E2-100 ERV WiFi
* VENTS Micra 100 WiFi, Micra 100 ERV WiFi, Micra 100 E WiFi,
  Micra 100 E1 WiFi, Micra 100 E2 WiFi, Micra 100 E2 ERV WiFi
* VENTS Breezy, Breezy 160, Breezy 160-E, Breezy 160-E Smart,
  Breezy 200-E, Breezy 200-E Smart, Breezy Eco 160, Breezy Eco 200
* Blauberg Freshpoint, Freshpoint 160, Freshpoint 160-E,
  Freshpoint 160-E L055/L07/L1, Freshpoint 160-E Pro L055/L07/L1,
  Freshpoint 200, Freshpoint 200-E L055/L07/L1,
  Freshpoint 200-E Pro L055/L07/L1, Freshpoint Eco 160, Freshpoint Eco 200,
  Freshpoint Eco 160-E L07
* VENTS Arc Smart, Arc Smart white, Arc Smart black,
  Blauberg O2 Supreme, O2 Supreme white, O2 Supreme black

External relabels and OEM names tracked as evidence or candidates:

* OXXIFY.smart 50, Oxxify.smart 50, Oxxify smart 50,
  Oxxify.smart 30, oxxify.smart 50k, OXXIFY.pro 50, OXXIFY.eco 50
* SIKU RV, SIKU RV 50 W Pro WiFi V2, SIKU RV 50 W PRO WIFI V2,
  SIKU RV 30 DW Pro Duo WiFi V2, SIKU RV 30 DW PRO DUO WIFI V2,
  SIKU RV 25 W Pro WiFi V2
* Flexit Roomie One WiFi V2, Romventilator Roomie One WiFi V2,
  Roomie One Wifi V2, Flexit Roomie Dual Wifi, Roomie Dual Wifi,
  Roomie Dual WiFi V2, Flexit Aura One WiFi, Flexit Aura, Flexit Muto,
  Flexit Bodo Supreme
* DUKA One, DUKA One S6W, DUKA One S6BW, DUKA One S4 Wi-Fi,
  DUKA One S6 Wi-Fi, DUKA One Pro 25 S Wi-Fi, DUKA One Pro 50 S Wi-Fi
* RL Raumklima, RL PRO-Serie, RL 50RVW, RL 30DVW, RL 25RVW
* Winzel V.2, Winzel Expert WiFi RW1-50 P,
  Blauberg Winzel Expert WiFi RW1-50 P
* NIBE DVC 10, NIBE DVC 10-50W, NIBE DVC 10-D30W
* ECONOPRIME DF270, ECONOPRIME DF270 Connect, and the reported seller spelling
  Econology DF270 Connect (`0x0100`, also reported by RECOM 4 SR; mapped to
  the tested VENTO protocol profile). VENTS VUT 270 V5B EC A21 is supported
  through the separate A21 Modbus transport; this does not make it a confirmed
  DF270 relabel or prove BGCP compatibility.
* ECONOPRIME Bora documentary candidates: Bora 160, Bora 160 L440,
  Bora 160 L550, Bora 160 L700, Bora 160 L1000, Bora 160 Prime L440,
  Bora 160 Prime L550, Bora 160 Prime L700, Bora 160 Prime L1000,
  Bora 200, Bora 200 L440, Bora 200 L550, Bora 200 L700, Bora 200 L1000,
  Bora 200 Prime L440, Bora 200 Prime L550, Bora 200 Prime L700,
  Bora 200 Prime L1000. No Bora unit type or BGCP capture is documented.
* Other ECONOPRIME DF search names: DF 180 Flat, DF 180 Flat Connect,
  DFF18021, DF 270, DF27014, DF 270 Connect, DF27021, DF 350,
  DF 350 Connect, DF35021
* Other ECONOPRIME Zephyr search names: Zephyr 100 S, ZEPH100, Zephyr 240 S,
  ZEPH240A14, Zephyr 240 S Connect, ZEPH240A21, Zephyr 270 V R, 114800001,
  Zephyr 270 V Connect R, 114800002, Zephyr 550 V PH Connect R, 114800003
* Other ECONOPRIME PremAIR/GatePass search names: URC 250, URC250, URHF 150,
  URHF150, URHFCF 150, URHFCF150, URHF 200, URHF200, URHFCF 200,
  URHFCF200, URH 350, URH350
* Other ECONOPRIME search names without BGCP evidence: Airion 100, Airion 150

# Tested on:
* Blauberg VENTO Expert A50-1 W V.2

# Currently supported:

* Home Assistant UI setup and reconfiguration, including VENTS A21 Modbus TCP/RTU.
* Power, low/medium/high/manual presets, and manual speed percentage.
* Optional silent manual-speed control for VENTO/TwinFresh devices.
* Heat recovery (oscillation), ventilation (forward), and air supply (reverse).
* Profile-dependent airflow selection, including Freshpoint/Breezy extract mode.
* Timer modes, device sensors, diagnostics, and supported configuration controls.
* Weekly schedules: edit the schedule entity through its more-info dialog.
* Configurable automatic clock synchronization and the `sync_device_clock` service.

See [protocol notes](protocol.md#home-assistant-control-and-clock-behavior) for
silent-mode, airflow, and clock-sync caveats; capabilities depend on the device profile.

# Changelog

## Version 1.2.31
* Keep Freshpoint/Breezy CO2 and fan RPM through three missed reads; clear on the fourth or invalid data (#104, #111).
* Add RECOM 4 SR air temperatures and a read-only setpoint; recognize its optional-row variant (fixture-verified, #109).
* Reload the config entry when RECOM 4 SR temperature probes appear after setup.
* Recognize VENTO inHome old / TwinFresh Atmo old optional-row rejections without a false Repair (#110).

## Version 1.2.30
* Accept Freshpoint/Breezy CO2 readings above 2000 ppm without changing writable threshold limits (#104).
* Recognize standard Freshpoint optional hardware without a false Repair (#107).
* Preserve final schedule times of either 00:00 or 23:59 and reject invalid end times (#102).

## Version 1.2.28
* Preserve Vento controls across partial polls and retry missing values (#100).
* Confirm controls and schedule changes from fresh reads; clear invalid or identity-stale values.
* Keep capability caches, lifecycle cleanup, and unknown alarms consistent after partial or malformed replies.

## Version 1.2.25
* Expose Freshpoint/Breezy extract airflow and label unknown airflow values clearly.
* Clarify that balanced two-fan percentage is a UI compromise, not measured speed.
* Recognize standard Freshpoint and older VENTO Expert optional hardware without false Repairs (#90, #94, #95, #97).
* Relearn capabilities and reload device metadata when firmware or unit type changes.
* Report failed commands instead of publishing optimistic control, schedule, or clock states.
* Preserve complete schedule days when reads return only some periods.
* Close connections after failed setup so retries do not leak transports.
* Reject invalid, duplicate, conflicting, or mismatched BGCP replies and write acknowledgments.
* Preserve parameter pages across batched commands, including clock writes.
* Restore Smart Wi-Fi / iFan availability when optional motion rows are rejected (#92).
* Match replies to the configured device while keeping broadcast discovery open.
* Retry bulk polling after temporary failures instead of permanently slowing polling.
* Reject batch writes containing unknown controls and refresh switches after successful writes.
* Report failed UDP sends and clock batches without accepting stale replies.
* Suppress standalone automatic clock correction in silent mode; explicit sync remains available.
* Reject malformed alarm lists rather than silently discarding trailing data.

## Version 1.2.24
* Keep Vento/TwinFresh available when individual control rows are omitted (#85).
* Include the integration version in hardware reports and add confirmed Flexit/Roomie discovery names (#86).

## Version 1.2.23
* Recognize older Vento A50 and DUO A30 optional-row variants without false Repairs (#78, #80, #82, #84).
* Make hardware Repair reports specific to each model, firmware, and rejected-register set.

## Version 1.2.21
* Stop polling explicitly unsupported optional Breezy/Freshpoint rows and hide their entities.
* Add hardware/profile Repairs with prefilled issue links and device diagnostics.

## Version 1.2.19
* Restore Freshpoint polling when optional sensor or feature rows remain unavailable (#74).
* Clear unsupported optional data, back off retries, and defer unavailable schedule reads.
* Log missing required and optional registers to make hardware reports actionable.
* Document recovery before downgrading migrated entries to 1.2.15 (see protocol notes).

## Version 1.2.18
* Restore standard Freshpoint 160-E setup when non-Pro CO2/VOC probes are absent.

## Version 1.2.17
* Add VENTS A21 Modbus TCP/RTU support, identity checks, clocks, schedules, and config-entry migration.

## Version 1.2.16
* Respect packet limits and retry omitted registers instead of accepting incomplete reads.
* Refresh Freshpoint humidity and built-in temperatures on quick polls.
* Map reported ECONOPRIME DF270 Connect devices to the tested VENTO profile.
* Add official Freshpoint variants and updated Freshpoint/A21 research sources.

## Version 1.2.15
* Add writable Off/Night/Party timer selection on supported devices.
* Prevent duplicate schedule frontend registration during concurrent setup.

## Version 1.2.14
* In silent mode, zero percentage keeps the unit on at zero manual speed instead of sending audible power-off.
* Allow the manual speed number to reach 0%.
* Keep silent presets effective when configurable preset setpoints are unavailable.

## Version 1.2.13
* Require synchronized host time for automatic clock writes on OS/Supervised installs.
* Avoid duplicate silent preset writes after Home Assistant restarts.
* Keep steady-state silent speed changes quiet; explicit airflow changes may still beep.

## Version 1.2.12
* Skip unchanged fan service calls to avoid unnecessary commands and refreshes.

## Version 1.2.11
* Fix silent-mode `turn_on` calls without an explicit speed or preset.

## Version 1.2.10
* Preserve customized entity IDs and repair only integration-generated legacy names.
* Keep IDs stable when labels become clearer, including analog-voltage entities.

## Version 1.2.9
* Avoid full schedule polls while scheduling is off; refresh edited days before saving.
* Add optional silent manual-speed control without changing auto-boost triggers.
* Fix batched manual-speed and clock commands.
* Make clock sync configurable and quieter, with explicit manual sync available.
* Turn devices on before applying airflow or heat-recovery changes.
* Group entity labels and clarify setup/reconfigure fields.
* Replace separate clock diagnostics with one RTC timestamp and migrate legacy entries.
* Label unknown airflow values instead of exposing a placeholder.

## Version 1.2.8
* Restore the weekly schedule switch and keep frontend hashing off the event loop.
* Restore the Device problem binary sensor alongside detailed alarm states.
* Expose manual speed and optional preset supply/exhaust configuration numbers.
* Use each profile's speed scale for setpoints while retaining native HA percentage controls.

## Version 1.2.7
* Add a localized weekly schedule editor and a single schedule summary entity.
* Save only changed schedule records.
* Correct VENTO schedule-speed diagnostics and keep unknown enum values stable.
* Add clock synchronization and remove stale schedule helper entities.

## Version 1.2.6
* Improve transport handling, bulk-read fallback, missing-battery handling, and four-byte filter countdown decoding.
* Add profile-aware Smart Wi-Fi/iFan, Breezy/Freshpoint, Freshbox/Micra, and Arc Smart/O2 Supreme support.
* Expand documented model aliases and search keywords.
* Expose only profile-supported entities and separate HA direction from protocol airflow.

## Version 1.2.5
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

## Version 1.2.4
* Merge pull request #40 from AndyNew2
  * added weekly_schedule_state on request
  * Add weekly schedule state to VentoSwitch

## Version 1.2.3
* Merge pull request #39 from AndyNew2/AndyNew2-Rework
  * v1.2.3 bugfix and stability improvement

## Version 1.2.2
* Beeper status error/write value of val varable
* fix for case, where HW returns unknown value for some statuses/states

## Version 1.2.1
* Merged @AndyNew2 pull request bugfix for initialization not using job executor and some config flow fixes #37

## Version 1.2.0
* Merged @AndyNew2 pull request v1.2.0 Rework ecovent library #36
  * this is a massive rework of your integration:
  * moved your library into the integration to avoid confusions ;-)
  * There was a massive bug in the binary_sensor multiplying the update rate by
    4 - 6. Therefore you had a real update rate around 10 seconds instead of the
    intended 1 minute ;-) This was on top of the double update before your last
    update ;-)
  * Added job executor to free HA timings. I checked UDP async IO but do not
    like it. Timeout handling is really difficult with it. Since we do the
    updates many less now, due to a few fixed, the overhead of an executor
    thread is fine. This allows now reenabling sleeps for retries. Works very
    well now.
  * Many bug fixes in the init and deinit code. Was no longer up to date for HA
    and would have created massive warnings soon. That is fixed now.
  * Few further fixes like not updating manual speed etc. Do not remember each
    of them, but there had been quite a lot of them.
  * Config flow has now update rate configurable and added reconfigure dialog.
    Set default update rate to 30 seconds (still is around 3x slower than before
    ;-))
  * Let me know, what you think about the changes. Runs a lot better than
    before. This unindented fast update created together with the fix of retries
    many HA issues. HA is not prepared to be blocked around 5 - 10 seconds...

## Version 1.1.1
* Fix typos

## Version 1.1.0
* Merged fixes from github contributors

## Version 1.0.9
* Bump pyyecoventv2 requirements to 0.9.23, remove beeper gueswork

## Version 1.0.8 / 1.0.7
* Bump pyyecoventv2 requirements to 0.9.22, still trying to fix 4 byte return of filter_timer_counter function

## Version 1.0.6
* Bump pyEcoventV2 requirements to 0.9.21, trying to resolve different lengths of returned value for filter_timer_counter

## Version 1.0.5
* Bump pyEcoventV2 requirements to 0.9.19

## Version 1.0.4


## Version 1.0.3
* Merge pull request #28 from SantaFox/main: Amended some sensors for better automations

## Version 1.0.2
* Fix for issue #25 VentoExpertFan does not set FanEntityFeature.TURN_OFF but implements the thurn_off method

## Version 1.0.1
* Values for humidity_threshold, analogV_threshold and boost ime read from device on initialization.

## Version 1.0.0
* some more name fixes
* fix code to be more compliant with latest HA
* some code cleanup

## Version 0.9.9
* more  entities names fixes.

## Version 0.9.8
* Fix number entities names.

## Version 0.9.7
* Updatet README.md

## Version 0.9.6
* Fix: Humidy Threshold creates errors trouble in newest HA #21
* humidity_treshold, analogV_treshold, boost_timer changed from sensor to number. Now they can be configured via HomeAssistant.

## Version 0.9.5
* Merged pull request for file "protocol.md" by @Styx85.

## Version 0.9.3
* bump requirements to pyEcoventV2==0.9.16 (fixed boost_status reading)

## Version 0.9.2
* fix name of sensor leaking to device name (hopefuly)

## Version 0.9.1
* replaced hass.config_entries.async_setup_platforms with await hass.config_entries.async_forward_entry_setups
* thanks to @berndulum for issue report

## Version 0.9.0
* Cleanup some definitions for HA checks

## Version 0.8.0
* Removed calling blocking sleep in event loop

## Version 0.7.0
* Fix manifest, to require correct pyEcovent version (0.9.14)

## Version 0.6.0
* Timeout Loop bailout

## Version 0.5.0
* Mainly fixes from autmated checks and hopefuly some latency improvements
  - Removed await coordinator in turn_on/turn_off and other interactive
    functions
  - Some cleanup in config_flow
  - Removed deprecated set_speed functions
  - Fix error if _battery_voltage is None

## Version 0.4.0
* Added broadcast devices search
  - hack, that searches on network, if string: `<broadcast>` is entered
    instead of IP address
  - this is not yer proper HomaAssistant Auto Discovery, but it seems to
    work on my network

## Version 0.2.0
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

* Added services
  - filter_timer_reset (Reset filter timer)
  - reset_alarms (Reset alarms)
* Changed:
  - From binary sensor to switch:
    - humidity_sensor_state
    - relay_sensor_state
    - analogV_sensor_state

## Version 0.1.0
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

## Version 0.0.5
* Added sensors:
  - Humidity
  - Fan1 speed
  - Fan2 speed
  - Airflow

* Changed
  - Update method to DataUpdateCoordinator for reduced request to FAN device
