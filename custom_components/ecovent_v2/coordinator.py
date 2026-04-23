"""VentoUpdateCoordinator class."""

# from __future__ import annotations
from datetime import time, timedelta
import logging

from .ecoventv2 import Fan
from .schedule_helpers import (
    SCHEDULE_DAY_LABELS,
    SCHEDULE_DAY_OPTIONS,
    SCHEDULE_DAY_TO_INDEX,
    SCHEDULE_OPTION_TO_SPEED,
    SCHEDULE_SPEED_TO_OPTION,
    WeeklyScheduleRecord,
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

from .const import DOMAIN

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
        self._schedule_records: dict[int, WeeklyScheduleRecord] = {}
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

        if self._fan.supports_parameter("weekly_schedule_setup") and (
            not self._schedule_records or self.updateCounter % 10 == 0
        ):
            await self.hass.async_add_executor_job(self._load_schedule_day)

        if self._fan.supports_parameter("rtc_time") and self._fan.supports_parameter(
            "rtc_date"
        ):
            await self._async_maybe_sync_clock()

    async def _async_post_init_setup(self) -> None:
        """Load slow one-off state after device discovery."""
        if self._fan.supports_parameter("weekly_schedule_setup"):
            await self.hass.async_add_executor_job(self._load_schedule_day)

    def _load_schedule_day(self) -> None:
        """Read and cache the current schedule day from the device."""
        self._schedule_records = self._fan.read_weekly_schedule_day(self._schedule_day)

    async def _async_maybe_sync_clock(self) -> None:
        """Keep documented RTC-capable devices close to HA local time."""
        now = dt_util.now()
        if self._last_clock_sync is not None and (
            now - self._last_clock_sync < timedelta(hours=12)
        ):
            return

        await self.hass.async_add_executor_job(
            self._fan.set_rtc_datetime,
            now.replace(tzinfo=None),
        )
        self._last_clock_sync = now

    @property
    def schedule_day_option(self) -> str:
        """Return the UI label of the selected schedule day."""
        return SCHEDULE_DAY_LABELS[self._schedule_day]

    @property
    def schedule_day_options(self) -> list[str]:
        """Return the allowed schedule day selector options."""
        return list(SCHEDULE_DAY_OPTIONS)

    def schedule_record(self, period: int) -> WeeklyScheduleRecord | None:
        """Return the cached record for a period."""
        return self._schedule_records.get(period)

    def schedule_period_speed_option(self, period: int) -> str | None:
        """Return the current UI speed label for a period."""
        record = self.schedule_record(period)
        if record is None:
            return None
        return SCHEDULE_SPEED_TO_OPTION.get(record.speed, record.speed)

    def schedule_period_end_time(self, period: int) -> time | None:
        """Return the end time for an editable schedule period."""
        record = self.schedule_record(period)
        if record is None:
            return None
        return record.end_time

    def schedule_summaries(self) -> dict[str, str]:
        """Return compact summaries for the selected schedule day."""
        start_hour = 0
        start_minute = 0
        summaries = {}
        for period in range(1, 5):
            record = self.schedule_record(period)
            if record is None:
                continue
            summaries[f"period_{period}"] = record.summary(start_hour, start_minute)
            start_hour = record.end_hour
            start_minute = record.end_minute
        return summaries

    async def async_select_schedule_day(self, option: str) -> None:
        """Switch the schedule editor to another weekday."""
        self._schedule_day = SCHEDULE_DAY_TO_INDEX[option]
        await self.hass.async_add_executor_job(self._load_schedule_day)
        self.async_update_listeners()

    async def async_set_schedule_period_speed(self, period: int, option: str) -> None:
        """Write a schedule period speed and refresh the current day cache."""
        current = self.schedule_record(period)
        if current is None:
            return

        updated = WeeklyScheduleRecord(
            day=current.day,
            period=current.period,
            speed=SCHEDULE_OPTION_TO_SPEED[option],
            end_hour=current.end_hour,
            end_minute=current.end_minute,
            reserved=current.reserved,
        )
        await self.hass.async_add_executor_job(
            self._fan.write_weekly_schedule_record,
            updated,
        )
        await self.hass.async_add_executor_job(self._load_schedule_day)
        self.async_update_listeners()

    async def async_set_schedule_period_end(self, period: int, value: time) -> None:
        """Write a schedule period end time and refresh the current day cache."""
        current = self.schedule_record(period)
        if current is None:
            return

        new_minutes = value.hour * 60 + value.minute
        previous_record = self.schedule_record(period - 1) if period > 1 else None
        next_record = self.schedule_record(period + 1)

        lower_bound = 0
        if previous_record is not None:
            lower_bound = previous_record.end_hour * 60 + previous_record.end_minute

        upper_bound = 24 * 60
        if next_record is not None:
            upper_bound = next_record.end_hour * 60 + next_record.end_minute

        if new_minutes <= lower_bound or new_minutes >= upper_bound:
            raise ValueError(
                "Schedule period end times must stay in chronological order"
            )

        updated = WeeklyScheduleRecord(
            day=current.day,
            period=current.period,
            speed=current.speed,
            end_hour=value.hour,
            end_minute=value.minute,
            reserved=current.reserved,
        )
        await self.hass.async_add_executor_job(
            self._fan.write_weekly_schedule_record,
            updated,
        )
        await self.hass.async_add_executor_job(self._load_schedule_day)
        self.async_update_listeners()

    async def async_sync_device_clock(self) -> None:
        """Synchronize the device RTC with HA local time immediately."""
        await self.hass.async_add_executor_job(
            self._fan.set_rtc_datetime,
            dt_util.now().replace(tzinfo=None),
        )
        self._last_clock_sync = dt_util.now()
        await self.async_refresh()
