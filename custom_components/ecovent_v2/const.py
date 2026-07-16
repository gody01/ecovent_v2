"""Constants for the EcoVent_v2 integration."""

DOMAIN = "ecovent_v2"
UPDATE_INTERVAL = "update_interval"
CONF_AUTO_CLOCK_SYNC = "auto_clock_sync"
CONF_SILENT_MODE = "silent_mode"
CONF_TRANSPORT = "transport"
CONF_UNIT_ID = "unit_id"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_DEVICE_MODEL = "device_model"

TRANSPORT_BGCP_UDP = "bgcp_udp"
TRANSPORT_MODBUS_TCP = "modbus_tcp"
TRANSPORT_MODBUS_RTU = "modbus_rtu"
SUPPORTED_TRANSPORTS = (
    TRANSPORT_BGCP_UDP,
    TRANSPORT_MODBUS_TCP,
    TRANSPORT_MODBUS_RTU,
)
A21_BAUD_RATES = (9600, 14400, 19200, 38400, 57600, 115200)
A21_STOP_BITS = (1, 1.5, 2)

A21_DEVICE_MODELS = (
    "VENTS VUT 270 V5B EC A21",
    "ECONOPRIME DF 270 Connect",
    "ECONOPRIME Zephyr 240 S Connect",
    "ECONOPRIME Zephyr 270 V Connect R",
    "ECONOPRIME Zephyr 550 V PH Connect R",
    "Generic VENTS A21 controller",
)

SERVICE_FILTER_TIMER_RESET = "filter_timer_reset"
SERVICE_RESET_ALARMS = "reset_alarms"
SERVICE_SYNC_DEVICE_CLOCK = "sync_device_clock"
