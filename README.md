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
  Freshpoint 160-E L055/L07/L1, Freshpoint 160-E Pro L055/L07/L1,
  Freshpoint 200, Freshpoint 200-E L055/L07/L1,
  Freshpoint 200-E Pro L055/L07/L1, Freshpoint Eco 160, Freshpoint Eco 200
* VENTS Arc Smart, Arc Smart white, Arc Smart black,
  Blauberg O2 Supreme, O2 Supreme white, O2 Supreme black

External relabels and OEM names tracked as evidence or candidates:

* OXXIFY.smart 50, Oxxify.smart 50, Oxxify smart 50,
  Oxxify.smart 30, oxxify.smart 50k, OXXIFY.pro 50, OXXIFY.eco 50
* SIKU RV, SIKU RV 50 W Pro WiFi V2, SIKU RV 50 W PRO WIFI V2,
  SIKU RV 30 DW Pro Duo WiFi V2, SIKU RV 30 DW PRO DUO WIFI V2,
  SIKU RV 25 W Pro WiFi V2
* Flexit Roomie One WiFi V2, Roomie One Wifi V2, Flexit Roomie Dual Wifi,
  Roomie Dual Wifi, Roomie Dual WiFi V2, Flexit Aura, Flexit Muto
* DUKA One, DUKA One S6W, DUKA One S6BW, DUKA One S4 Wi-Fi,
  DUKA One S6 Wi-Fi, DUKA One Pro 25 S Wi-Fi, DUKA One Pro 50 S Wi-Fi
* RL Raumklima, RL PRO-Serie, RL 50RVW, RL 30DVW, RL 25RVW
* Winzel V.2, Winzel Expert WiFi RW1-50 P,
  Blauberg Winzel Expert WiFi RW1-50 P
* NIBE DVC 10, NIBE DVC 10-50W, NIBE DVC 10-D30W
* ECONOPRIME DF270, ECONOPRIME DF270 Connect, and the reported seller spelling
  Econology DF270 Connect (`0x0100`, mapped to the tested VENTO protocol
  profile). VENTS VUT 270 V5B EC A21 is supported through the separate A21
  Modbus transport; this does not make it a confirmed DF270 relabel or prove
  BGCP compatibility.
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
* UI integration setup
* VENTS A21 Modbus TCP/RTU with an input-register `37 == 1` identity check
* turn_on/turn_off
* Preset modes:
  - low
  - medium
  - high
  - manual
* In manual mode speed percentage
* Timer mode selection on devices exposing `0x0007`
* Silent mode
  - optional configuration checkbox for VENTO/TwinFresh-style devices
  - keeps the device in manual speed mode and maps Home Assistant preset changes
    to manual speed percentages to avoid unnecessary confirmation beeps
  - preserves device-side humidity, relay, and analog-voltage auto-boost trigger
    settings while manual preset control is used, since those triggers may be
    intentionally configured
    above the configured thresholds
  - airflow/direction changes still use the device airflow command, but the
    integration batches the current manual speed state into the same write
* Oscillating
  - When on, Fans are in 'heat_recovery' airflow
* Direction
  - "forward" means 'ventilation' airflow
  - "reverse" means 'air_supply' airflow
* Weekly schedule support on devices exposing `0x0072` / `0x0077`
  - one visible schedule entity for the weekly schedule
  - open the schedule entity's more-info dialog to edit the weekly schedule
* Device clock synchronization
  - automatic sync is enabled by default and can be disabled in reconfigure
  - periodic sync checks every five minutes and writes only when the device
    clock differs from Home Assistant local time by more than a minute
  - on Home Assistant OS/Supervised installs, automatic clock writes require
    Supervisor to report the host clock as NTP synchronized
  - Home Assistant startup discovery stays read-only and defers standalone
    clock correction, so restarting HA does not make every fan beep
  - standalone periodic correction rereads the device RTC immediately before
    writing, and skips the write if the fresh RTC state is unavailable
  - device writes that would already beep also batch the RTC rows when the
    cached clock has drifted, avoiding a separate clock-only beep
  - the `sync_device_clock` fan service can be used for manual or automated sync

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

Version 1.2.1
* Merged @AndyNew2 pull request bugfix for initialization not using job executor and some config flow fixes #37

Version 1.2.2
* Beeper status error/write value of val varable
* fix for case, where HW returns unknown value for some statuses/states

Version 1.2.3
* Merge pull request #39 from AndyNew2/AndyNew2-Rework
  * v1.2.3 bugfix and stability improvement

Version 1.2.4
* Merge pull request #40 from AndyNew2
  * added weekly_schedule_state on request
  * Add weekly schedule state to VentoSwitch

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
* Restore the visible weekly schedule switch and keep the schedule frontend file
  digest out of the Home Assistant event loop.
* Restore `alarm_status` as a Home Assistant `Device problem` binary sensor
  while keeping the enum alarm sensor for `no` / `warning` / `alarm` detail.
* Expose manual speed as a visible configuration number so it can be adjusted
  without using the live fan speed control.
* Add disabled-by-default configuration numbers for preset supply/exhaust speed
  setpoints on VENTO/TwinFresh, Breezy/Freshpoint, and Freshbox/Micra profiles.
* Encode speed setpoint writes with the active protocol profile's percent scale,
  while keeping live fan percentage control Home Assistant-native.

Version 1.2.9
* Stop polling the full weekly schedule setup while the schedule switch is off;
  normal updates now read only the lightweight schedule enabled state.
* Refresh edited schedule days from the device before diffing and saving.
* Add optional silent manual-speed mode for VENTO/TwinFresh-style devices:
  Home Assistant presets are mapped to manual speed writes, while humidity,
  relay, and analog-voltage boost triggers are preserved.
* Encode batched multi-parameter writes through the same protocol path as single
  parameter writes, so silent/manual speed and RTC batches send the intended
  rows.
* Make device clock synchronization configurable and quieter: HA local time is
  used, periodic correction only writes for drift over a minute, RTC rows are
  reread before standalone correction, RTC rows are batched into already-noisy
  writes when possible, startup discovery defers standalone clock correction,
  and the manual
  `sync_device_clock` service remains available.
* Turn the unit on before applying Home Assistant airflow direction or heat
  recovery changes, so Freshpoint/Breezy ventilation mode starts reliably from
  an off state.
* Relabel entities and preset translations into sort-friendly `Boost`, `Speed`,
  `Mode`, `Trigger`, `Airflow`, and `Weekly schedule` groups.
* Add human-readable labels for the setup and reconfigure form fields, including
  update interval, automatic clock sync, and silent manual-speed mode.
* Replace separate RTC date/time diagnostic entity specs with one
  `RTC timestamp` sensor and remove stale legacy RTC date/time registry entries
  during setup migration.
* Stop exposing the old `Airflow: something` placeholder for protocol airflow
  enum value `3`; unknown airflow values now use `Unknown airflow <value>`.

Version 1.2.10
* Preserve user-customized entity ids during legacy entity id migration, while
  still repairing known intermediate integration-generated names so regenerated
  names survive integration reloads and Home Assistant restarts, including
  analog voltage sensor/status variants.
* Use the same stable object-id suffixes for newly created entities and legacy
  migrations, keeping readable UI labels without changing entity ids just
  because labels gained clearer prefixes.

Version 1.2.11
* Fix Home Assistant fan `turn_on` calls without an explicit speed or preset in
  silent manual-speed mode, so `preset_mode` is not passed as an unsupported
  executor keyword argument.

Version 1.2.12
* Skip unchanged Home Assistant fan service calls before scheduling executor
  work or refreshing the device, so repeated automations do not trigger extra
  EcoVent commands when the fan is already off, already at the requested
  preset, or already at the requested percentage.

Version 1.2.13
* On Home Assistant OS/Supervised installs, automatic device clock writes now
  require Supervisor to report the host clock as NTP synchronized. Core and
  container installs keep the previous behavior because no Supervisor clock
  quality signal is available there.
* In silent manual-speed mode, treat an already-on fan with the requested manual
  speed as an unchanged preset even after Home Assistant restarts and loses the
  in-memory preset facade. The facade is restored in HA state without sending a
  duplicate device write.
* Keep steady-state silent manual-speed changes to the only observed quiet
  write: the manual speed register. Entering silent mode may still switch the
  fan into manual mode once, and opportunistic RTC rows may be batched there
  because that packet already writes an audible mode register.
* Add an internal audible-write counter so tests can assert that silent-mode
  paths do not leak device-acknowledged writes.
* Guard the Home Assistant fan facade with behavior tests: silent preset and
  percentage changes may only send the manual speed register while already in
  manual mode. Explicit direction or heat-recovery/airflow commands still need
  the device airflow register and are allowed as audible writes, without
  opportunistic RTC rows while the fan is already in manual mode.

Version 1.2.14
* In silent manual-speed mode, map Home Assistant `percentage: 0` to an on,
  manual, zero-speed state instead of turning the EcoVent unit off. This lets
  quiet-home automations reduce airflow with the quiet manual-speed register
  rather than using audible power or preset writes.
* Allow the visible manual speed number to be set to `0%`, matching the silent
  zero-speed control path.
* In silent manual-speed mode, keep preset changes effective even when a device
  does not report configurable preset speed setpoints, by falling back to
  deterministic low/medium/high manual-speed percentages instead of reusing the
  current manual speed.

Version 1.2.15
* Expose `timer_mode` as a writable select on devices that support the
  documented `0x0007` timer mode parameter, allowing Home Assistant to select
  Off, Night, or Party mode.
* Guard schedule frontend registration before the first await, preventing
  duplicate static route registration when multiple EcoVent config entries are
  set up concurrently.

Version 1.2.16
* Keep protocol reads inside the documented 256-byte packet limit and verify
  that every requested register was present in a valid bulk response. Registers
  omitted by an otherwise valid reply are retried individually, and the parser
  now preserves the protocol high-byte page across following parameters. A
  refresh remains failed if an omitted register cannot be recovered, preventing
  Home Assistant from accepting a stale cycle as complete.
* Refresh Freshpoint humidity and all four built-in temperature registers on
  quick updates. The non-Pro model has no VOC/CO2eq sensor, so those optional
  readings may correctly remain unavailable.
* Map reported device type `256` / parser key `0x0100` to ECONOPRIME DF270
  Connect with the tested VENTO profile, while keeping the reported VENTS A21
  OEM relationship explicitly unconfirmed.
* Add official Freshpoint 160/200 standard and Pro length variants, current
  Freshpoint specification/manual links, and the current VENTS VUT V5B EC A21
  datasheet, product manual, Modbus table, and control manual as research
  sources.

Version 1.2.17
* Add separate VENTS A21 Modbus TCP and RTU transports with a read-only
  controller identity check, the complete published register table, RTC and
  weekly schedule support, and legacy BGCP config-entry migration.

Version 1.2.18
* Restore setup for standard Freshpoint 160-E devices whose non-Pro CO2/VOC
  probes are legitimately absent. Missing optional variant registers are still
  retried, while humidity and all four documented temperature registers remain
  required for a successful Freshpoint refresh.

Version 1.2.19
* Restore Freshpoint 160-E polling when sensor/feature rows remain unavailable
  after retry. Older 1.2.15 polling silently tolerated those omitted rows, while
  1.2.16/1.2.17 made any omission fatal. Breezy/Freshpoint polls now require
  only `0x0001` state, `0x0002` speed, and `0x0044` manual speed to prove the
  device itself is reachable.
* Treat explicit `0xFD` unsupported-register markers as unavailable data rather
  than fresh values. Missing or unsupported optional rows are cleared, backed off
  for ten poll cycles, and exposed as unknown/unavailable instead of stale or
  false HA states.
* Skip automatic full weekly-schedule cache reads while the lightweight
  `0x0072` schedule-state row is unavailable, avoiding setup/reload delays on
  Freshpoint variants that do not answer the optional schedule rows.
* Add debug logging for incomplete BGCP/UDP refreshes after individual register
  retries. The log now lists the missing required register addresses and any
  non-critical poll registers that stayed unavailable or unsupported, making
  Freshpoint hardware reports actionable without a local test device.
* Note for HACS downgrades: entries migrated by 1.2.16/1.2.17 use config-entry
  version 2. Home Assistant cannot load those entries with older 1.2.15 code;
  delete and re-add the integration entries or restore a full Home Assistant
  backup before downgrading to 1.2.15.

Version 1.2.21
* Remember optional Breezy/Freshpoint poll registers that the device explicitly
  reports as unsupported and stop requesting them in later automatic polls.
  Required fan availability rows still fail the update when absent or
  unsupported, while permanently unsupported optional sensors stay unknown
  without making the fan entity unavailable again.
