"""VentoUpdateCoordinator class."""

# from __future__ import annotations
from datetime import timedelta
import logging

from .ecoventv2 import Fan
from .schedule_helpers import (
    SCHEDULE_DAY_LABELS,
    SCHEDULE_DAY_OPTIONS,
    SCHEDULE_DAY_TO_INDEX,
    WeeklyScheduleRecord,
    changed_schedule_records,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import CONF_AUTO_CLOCK_SYNC, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EcoVentCoordinator(DataUpdateCoordinator):
    """Class for Vento Fan Update Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        update_seconds: int = 30,
    ) -> None:
        """Initialize global Vento data updater."""
        self._fan = Fan(
            config.data[CONF_IP_ADDRESS],
            config.data[CONF_PASSWORD],
            # config.data[CONF_DEVICE_ID],
            "DEFAULT_DEVICEID",
            config.data[CONF_NAME],
            config.data[CONF_PORT],
        )
        # self._fan.init_device()  is a blocking call cannot be done in constructur ...
        self.fan_initialized = False  # flag to indicate if the fan has been initialized
        self.updateCounter = 0
        self._schedule_day = 1
        self._weekly_schedule: dict[int, dict[int, WeeklyScheduleRecord]] = {}
        self._auto_clock_sync = config.data.get(CONF_AUTO_CLOCK_SYNC, True)
        self._last_clock_sync = None
        _LOGGER.debug(
            "EcoVentCoordinator initialized with update rate: %d", update_seconds
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config,
            update_interval=timedelta(seconds=update_seconds),
        )

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint.

        The concept is, we have one common update rate and read all data into the fan object, then the entities read from that object. This way we can avoid multiple API calls and have a single source of truth for the data.
        """
        if not self.fan_initialized:
            _LOGGER.debug("EcoVentCoordinator: Initializing fan for the first time...")
            await self.hass.async_add_executor_job(self._fan.init_device)
            if self._fan.id is None or self._fan.id == "DEFAULT_DEVICEID":
                _LOGGER.error(
                    "EcoVentCoordinator: Failed to initialize fan, check connection and configuration."
                )
                raise ConnectionError(
                    "Failed to initialize fan, check connection and configuration."
                )
            self.fan_initialized = True
            await self._async_post_init_setup()

        self.updateCounter += 1
        if (self.updateCounter % 2 == 0) or (self.updateCounter < 4):
            # every 2nd update do a full update, otherwise a quick update to reduce load on the device
            _LOGGER.debug("EcoVentCoordinator: Starting full data update...")
            await self.hass.async_add_executor_job(self._fan.update)
        else:
            _LOGGER.debug("EcoVentCoordinator: Starting quick data update...")
            await self.hass.async_add_executor_job(self._fan.quick_update)

        if self._should_refresh_schedule_week():
            await self.hass.async_add_executor_job(self._load_schedule_week)

        if self._auto_clock_sync and self._supports_device_clock_sync():
            await self._async_maybe_sync_clock()

    async def _async_post_init_setup(self) -> None:
        """Load slow one-off state after device discovery."""
        if self._should_refresh_schedule_week():
            await self.hass.async_add_executor_job(self._load_schedule_week)

    def _should_refresh_schedule_week(self) -> bool:
        """Return whether full weekly schedule reads are useful right now."""
        return (
            self._fan.supports_parameter("weekly_schedule_setup")
            and self._fan.weekly_schedule_state == "on"
            and (not self._weekly_schedule or self.updateCounter % 10 == 0)
        )

    def _load_schedule_week(self) -> None:
        """Read and cache the full weekly schedule from the device."""
        self._load_schedule_days(range(1, 8))

    def _load_schedule_days(self, days) -> None:
        """Read and cache selected weekly schedule days from the device."""
        for day in sorted(set(days)):
            self._weekly_schedule[day] = self._fan.read_weekly_schedule_day(day)

    def _supports_device_clock_sync(self) -> bool:
        """Return whether this device exposes writable RTC date and time rows."""
        return self._fan.supports_parameter("rtc_time") and self._fan.supports_parameter(
            "rtc_date"
        )

    async def _async_maybe_sync_clock(self) -> None:
        """Keep documented RTC-capable devices close to HA local time."""
        now = self._device_clock_now()
        if self._last_clock_sync is not None and (
            now - self._last_clock_sync < timedelta(hours=12)
        ):
            return

        await self.hass.async_add_executor_job(self._fan.set_rtc_datetime, now)
        self._last_clock_sync = now

    def _device_clock_now(self):
        """Return the HA-local wall clock value the device RTC should store."""
        return dt_util.now()

    @property
    def schedule_day_option(self) -> str:
        """Return the default day label shown when the editor opens."""
        return SCHEDULE_DAY_LABELS[self._schedule_day]

    @property
    def schedule_day_options(self) -> list[str]:
        """Return the allowed schedule day selector options."""
        return list(SCHEDULE_DAY_OPTIONS)

    def schedule_day_records(self, day: int) -> dict[int, WeeklyScheduleRecord]:
        """Return cached schedule records for one day."""
        return self._weekly_schedule.get(day, {})

    def schedule_record(self, day: int, period: int) -> WeeklyScheduleRecord | None:
        """Return the cached record for one day/period."""
        return self.schedule_day_records(day).get(period)

    def schedule_day_payload(self, day: int) -> dict[str, object]:
        """Return one day's schedule as a frontend-friendly payload."""
        start_hour = 0
        start_minute = 0
        periods: list[dict[str, object]] = []
        for period in range(1, 5):
            record = self.schedule_record(day, period)
            if record is None:
                continue
            period_data = record.as_dict()
            period_data["summary"] = record.summary(start_hour, start_minute)
            periods.append(period_data)
            start_hour = record.end_hour
            start_minute = record.end_minute
        return {"day": SCHEDULE_DAY_LABELS[day], "periods": periods}

    def weekly_schedule_payload(self) -> list[dict[str, object]]:
        """Return the full weekly schedule for Home Assistant attributes."""
        return [self.schedule_day_payload(day) for day in range(1, 8)]

    async def async_write_schedule(
        self,
        *,
        selected_day: str | None = None,
        weekly_schedule_enabled: bool | None = None,
        days: list[dict[str, object]] | None = None,
    ) -> None:
        """Apply one schedule payload from the custom dialog."""
        if selected_day is not None:
            self._schedule_day = SCHEDULE_DAY_TO_INDEX[selected_day]

        if weekly_schedule_enabled is not None:
            target = "on" if weekly_schedule_enabled else "off"
            if self._fan.weekly_schedule_state != target:
                await self.hass.async_add_executor_job(
                    self._fan.set_param,
                    "weekly_schedule_state",
                    target,
                )

        if days:
            day_payloads = []
            for day_payload in days:
                day_label = str(day_payload["day"])
                day = SCHEDULE_DAY_TO_INDEX[day_label]
                day_payloads.append((day_label, day, day_payload))

            if self._fan.supports_parameter("weekly_schedule_setup"):
                await self.hass.async_add_executor_job(
                    self._load_schedule_days,
                    [day for _, day, _ in day_payloads],
                )

            for day_label, day, day_payload in day_payloads:
                current_records = self.schedule_day_records(day)
                records_to_write = changed_schedule_records(
                    day,
                    current_records,
                    day_payload.get("periods", []),
                )

                for record in records_to_write:
                    written = await self.hass.async_add_executor_job(
                        self._fan.write_weekly_schedule_record,
                        record,
                    )
                    if not written:
                        raise RuntimeError(
                            "Failed to write schedule record "
                            f"{day_label} period {record.period}"
                        )
                    self._weekly_schedule.setdefault(day, {})[record.period] = record

        self.async_update_listeners()

    async def async_sync_device_clock(self) -> None:
        """Synchronize the device RTC with HA local time immediately."""
        now = self._device_clock_now()
        await self.hass.async_add_executor_job(self._fan.set_rtc_datetime, now)
        self._last_clock_sync = now
        await self.async_refresh()
