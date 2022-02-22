# ecovent_v2
Home Assistant Integration for EcoVent VENTO Expert A50/80/100 V.2 Fans

Integration for newest fans with api version 2

Tested on:
* Blauberg VENTO Expert A50-1 W V.2

Currently supported:
* UI integration setup
* turn_on/turn_off
* Preset modes:
** low
** medium
** high
** manual
* In manual mode speed percentage
* Oscillating
* When on Fan are in 'heat_recovery' airflow
* Direction
** "forward" means 'ventilation' airflow
** "reverse" means 'air_supply' airflow

version 0.0.5:
* Added sensors:
** Humidity
** Fan1 speed
** Fan2 speed
** Airflow
** Changed
** Update method to DataUpdateCoordinator for reduced request to FAN device

versino 0.1.0:
* Added sensors:
** battery_voltage
** timer_counter
** humidity_treshold
** filter_timer_countdown
** boost_time
** machine_hours
** analogV
** analogV_treshold

All sensors are categorised and some are disabled by default.
