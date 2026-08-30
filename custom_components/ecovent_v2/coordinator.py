"""VentoUpdateCoordinator class."""

# from __future__ import annotations
from datetime import datetime, timedelta
import logging

from .device_factory import create_device
from .schedule_helpers import (
    SCHEDULE_DAY_LABELS,
    SCHEDULE_DAY_OPTIONS,
    SCHEDULE_DAY_TO_INDEX,
    WeeklyScheduleRecord,
    changed_schedule_records,
    validate_schedule_day,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

try:
    from homeassistant.components.hassio.coordinator import get_host_info
    from homeassistant.helpers.hassio import is_hassio
except ImportError:
    get_host_info = None

    def is_hassio(hass):
        """Return false when HA has no Supervisor helper available."""
        return False


from .const import CONF_AUTO_CLOCK_SYNC, CONF_SILENT_MODE, DOMAIN
from .protocol_diagnostics import (
    hardware_profile_mismatch_state,
    hardware_profile_mismatch_issue_url,
    unsupported_optional_poll_parameter_summary,
)

_LOGGER = logging.getLogger(__name__)
CLOCK_SYNC_DRIFT = timedelta(minutes=1)
CLOCK_SYNC_INTERVAL = timedelta(minutes=5)


def hardware_profile_mismatch_issue_id(entry_id: str) -> str:
    """Return the per-entry Repairs issue id for hardware profile mismatches."""
    return f"hardware_profile_mismatch_{entry_id}"


def async_delete_hardware_profile_mismatch_issue(
    hass: HomeAssistant, entry_id: str
) -> None:
    """Delete the hardware profile mismatch Repairs issue for one entry."""
    try:
        from homeassistant.helpers import issue_registry as ir
    except ImportError:
        return

    ir.async_delete_issue(hass, DOMAIN, hardware_profile_mismatch_issue_id(entry_id))


class EcoVentCoordinator(DataUpdateCoordinator):
    """Class for Vento Fan Update Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        update_seconds: int = 30,
    ) -> None:
        """Initialize global Vento data updater."""
        self._fan = create_device(config.data, unique_id=config.unique_id)
        # self._fan.init_device()  is a blocking call cannot be done in constructur ...
        self.fan_initialized = False  # flag to indicate if the fan has been initialized
        self.updateCounter = 0
        self._schedule_day = 1
        self._weekly_schedule: dict[int, dict[int, WeeklyScheduleRecord]] = {}
        self._auto_clock_sync = config.data.get(CONF_AUTO_CLOCK_SYNC, True)
        self._silent_mode = config.data.get(CONF_SILENT_MODE, False)
        self._silent_preset_mode: str | None = None
        self._last_clock_sync = None
        self._last_clock_sync_check = None
        self._pending_clock_sync = None
        self._reported_hardware_profile_mismatch_state = None
        self._fan.extra_write_parameters_callback = self._clock_sync_params_if_needed
        self._fan.extra_write_parameters_result_callback = (
            self._clock_sync_write_completed
        )
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
            initialized = await self.hass.async_add_executor_job(self._fan.init_device)
            if (
                not initialized
                or self._fan.id is None
                or self._fan.id == "DEFAULT_DEVICEID"
            ):
                _LOGGER.error(
                    "EcoVentCoordinator: Failed to initialize fan, check connection and configuration."
                )
                raise ConnectionError(
                    "Failed to initialize fan, check connection and configuration."
                )
            self.fan_initialized = True
            await self._async_post_init_setup()
            self._defer_startup_clock_sync()

        self.updateCounter += 1
        if (self.updateCounter % 2 == 0) or (self.updateCounter < 4):
            # every 2nd update do a full update, otherwise a quick update to reduce load on the device
            _LOGGER.debug("EcoVentCoordinator: Starting full data update...")
            update_complete = await self.hass.async_add_executor_job(self._fan.update)
        else:
            _LOGGER.debug("EcoVentCoordinator: Starting quick data update...")
            update_complete = await self.hass.async_add_executor_job(
                self._fan.quick_update
            )

        if not update_complete:
            raise UpdateFailed(
                f"Incomplete protocol response from EcoVent device {self._fan.name}"
            )

        self._update_hardware_profile_mismatch_repair_issue()

        if self._should_refresh_schedule_week():
            await self.hass.async_add_executor_job(self._load_schedule_week)

        if self._auto_clock_sync and self._supports_device_clock_sync():
            await self._async_maybe_sync_clock()

    async def _async_post_init_setup(self) -> None:
        """Load slow one-off state after device discovery."""
        self._update_hardware_profile_mismatch_repair_issue()
        if self._should_refresh_schedule_week():
            await self.hass.async_add_executor_job(self._load_schedule_week)

    def _hardware_profile_mismatch_issue_id(self) -> str:
        """Return the per-entry Repairs issue id for hardware profile mismatches."""
        return hardware_profile_mismatch_issue_id(self.config_entry.entry_id)

    def _update_hardware_profile_mismatch_repair_issue(self) -> None:
        """Show a Repairs issue when this hardware omits profile-declared rows."""
        mismatch_state = hardware_profile_mismatch_state(self._fan)
        if mismatch_state == self._reported_hardware_profile_mismatch_state:
            return

        unsupported = mismatch_state[-1]

        try:
            from homeassistant.helpers import issue_registry as ir
        except ImportError:
            _LOGGER.debug(
                "EcoVentCoordinator: Repairs issue registry unavailable; "
                "skipping hardware profile mismatch issue"
            )
            return

        issue_id = self._hardware_profile_mismatch_issue_id()
        try:
            if not unsupported:
                async_delete_hardware_profile_mismatch_issue(
                    self.hass, self.config_entry.entry_id
                )
            else:
                unsupported_params = unsupported_optional_poll_parameter_summary(
                    self._fan, unsupported
                )
                issue_url = hardware_profile_mismatch_issue_url(self._fan, unsupported)
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    issue_id,
                    is_fixable=False,
                    is_persistent=True,
                    learn_more_url=issue_url,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="hardware_profile_mismatch",
                    translation_placeholders={
                        "name": self._fan.name,
                        "unit_type": self._fan.unit_type or "unknown",
                        "profile": self._fan.profile_key,
                        "unsupported_params": unsupported_params,
                    },
                    data={
                        "entry_id": self.config_entry.entry_id,
                        "profile": self._fan.profile_key,
                        "unit_type": self._fan.unit_type,
                        "unit_type_id": getattr(self._fan, "_unit_type_id", None),
                        "unsupported_optional_params": unsupported_params,
                        "github_issue_url": issue_url,
                    },
                )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning(
                "Unable to update EcoVent V2 hardware profile Repair for %s: %s",
                self._fan.name,
                err,
                exc_info=True,
            )
            return

        self._reported_hardware_profile_mismatch_state = mismatch_state

    def _defer_startup_clock_sync(self) -> None:
        """Avoid clock-only writes during Home Assistant startup discovery."""
        if not self._auto_clock_sync or not self._supports_device_clock_sync():
            return

        now = self._device_clock_now()
        self._last_clock_sync_check = now
        _LOGGER.debug(
            "EcoVentCoordinator: deferring startup clock sync check for %s",
            self._fan.name,
        )

    def _should_refresh_schedule_week(self) -> bool:
        """Return whether full weekly schedule reads are useful right now."""
        if not self._fan.profile_supports_parameter("weekly_schedule_setup"):
            return False

        state = self._fan.weekly_schedule_state
        if state not in ("on", "off"):
            _LOGGER.debug(
                "EcoVentCoordinator: skipping weekly schedule read for %s "
                "because schedule state is unavailable",
                self._fan.name,
            )
            return False

        return not self._weekly_schedule or (
            state == "on" and self.updateCounter % 10 == 0
        )

    def _load_schedule_week(self) -> None:
        """Read and cache the full weekly schedule from the device."""
        self._load_schedule_days(range(1, 8))

    def _load_schedule_days(self, days) -> set[int]:
        """Read selected schedule days and return those confirmed as fresh."""
        loaded_days: set[int] = set()
        for day in sorted(set(days)):
            try:
                records = self._fan.read_weekly_schedule_day(day)
            except OSError as err:
                _LOGGER.warning(
                    "EcoVentCoordinator: preserving cached schedule for %s day %s "
                    "after a read error: %s",
                    self._fan.name,
                    day,
                    err,
                )
                continue
            if not records or set(records) != {1, 2, 3, 4}:
                _LOGGER.warning(
                    "EcoVentCoordinator: preserving cached schedule for %s day %s "
                    "after an incomplete read (%s/4 periods)",
                    self._fan.name,
                    day,
                    len(records or {}),
                )
                continue
            try:
                validate_schedule_day([records[period] for period in range(1, 5)])
            except ValueError as err:
                _LOGGER.warning(
                    "EcoVentCoordinator: preserving cached schedule for %s day %s "
                    "after invalid readback: %s",
                    self._fan.name,
                    day,
                    err,
                )
                continue
            self._weekly_schedule[day] = records
            loaded_days.add(day)

        return loaded_days

    def _supports_device_clock_sync(self) -> bool:
        """Return whether this device exposes writable RTC date and time rows."""
        return self._fan.supports_parameter(
            "rtc_time"
        ) and self._fan.supports_parameter("rtc_date")

    async def _async_maybe_sync_clock(self) -> None:
        """Keep documented RTC-capable devices close to HA local time."""
        now = self._device_clock_now()
        if not self._clock_sync_check_due(now):
            return
        self._last_clock_sync_check = now

        if self._silent_mode:
            _LOGGER.debug(
                "EcoVentCoordinator: skipping standalone clock sync because "
                "silent manual-speed mode is enabled"
            )
            return

        if self._recently_synced_clock(now):
            return

        if not self._host_clock_synchronized():
            _LOGGER.debug(
                "EcoVentCoordinator: skipping standalone clock sync because "
                "Home Assistant host time is not NTP synchronized"
            )
            return

        try:
            clock_read = await self.hass.async_add_executor_job(
                self._refresh_device_clock_state
            )
        except OSError as err:
            _LOGGER.debug(
                "EcoVentCoordinator: skipping standalone clock sync after "
                "RTC read error for %s: %s",
                self._fan.name,
                err,
            )
            return
        if not clock_read:
            _LOGGER.debug(
                "EcoVentCoordinator: skipping standalone clock sync because "
                "fresh RTC read failed for %s",
                self._fan.name,
            )
            return

        now = self._device_clock_now()
        if self._device_clock_datetime() is None:
            _LOGGER.debug(
                "EcoVentCoordinator: skipping standalone clock sync because "
                "fresh RTC state is unavailable for %s",
                self._fan.name,
            )
            return

        if not self._clock_sync_needed(now):
            return

        written = await self.hass.async_add_executor_job(
            self._fan.set_rtc_datetime, now
        )
        if not written:
            _LOGGER.warning(
                "EcoVentCoordinator: failed to synchronize device clock for %s",
                self._fan.name,
            )
            return
        confirmed = await self.hass.async_add_executor_job(
            self._confirm_device_clock_sync, now
        )
        if not confirmed:
            _LOGGER.warning(
                "EcoVentCoordinator: device did not confirm synchronized clock for %s",
                self._fan.name,
            )
            return
        self._record_clock_sync(now)

    def _refresh_device_clock_state(self) -> bool:
        """Read RTC rows before a standalone clock correction write."""
        time_read = self._fan.get_param("rtc_time")
        date_read = self._fan.get_param("rtc_date")
        return time_read and date_read

    def _host_clock_synchronized(self) -> bool:
        """Return whether HA has a trustworthy host clock signal."""
        if not is_hassio(self.hass):
            return True

        if get_host_info is None:
            return False

        host_info = get_host_info(self.hass)
        if host_info is None:
            return False

        return host_info.get("dt_synchronized") is True

    def _clock_sync_params_if_needed(self) -> dict[str, str]:
        """Return RTC rows to batch into an already noisy device write."""
        if not self._auto_clock_sync or not self._supports_device_clock_sync():
            return {}

        if not self._host_clock_synchronized():
            return {}

        now = self._device_clock_now()
        if self._recently_synced_clock(now):
            return {}

        if not self._clock_sync_needed(now):
            return {}

        self._pending_clock_sync = now
        return self._fan.rtc_datetime_params(now)

    def _clock_sync_write_completed(self, success: bool) -> None:
        """Record an opportunistic RTC write only after fresh device readback."""
        pending = self._pending_clock_sync
        self._pending_clock_sync = None
        if (
            success
            and pending is not None
            and self._confirm_device_clock_sync(pending)
        ):
            self._record_clock_sync(pending)

    def _confirm_device_clock_sync(self, expected) -> bool:
        """Read back the device RTC and compare it with the requested wall clock."""
        try:
            refreshed = self._refresh_device_clock_state()
        except OSError as err:
            _LOGGER.warning(
                "EcoVentCoordinator: failed to read back device clock for %s: %s",
                self._fan.name,
                err,
            )
            return False
        if not refreshed:
            return False
        return self._clock_sync_confirmed(expected)

    def _device_clock_now(self):
        """Return the HA-local wall clock value the device RTC should store."""
        return dt_util.now()

    def _device_clock_datetime(self) -> datetime | None:
        """Return the device RTC as a naive local wall-clock datetime."""
        if self._fan.rtc_date is None or self._fan.rtc_time is None:
            return None

        try:
            return datetime.fromisoformat(f"{self._fan.rtc_date}T{self._fan.rtc_time}")
        except ValueError:
            _LOGGER.debug(
                "EcoVentCoordinator: cannot parse device RTC date/time: %s %s",
                self._fan.rtc_date,
                self._fan.rtc_time,
            )
            return None

    def _local_wall_clock(self, value) -> datetime:
        """Drop timezone metadata after converting to HA's local wall-clock fields."""
        return datetime(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
        )

    def _clock_sync_check_due(self, now) -> bool:
        """Return whether the periodic RTC correction window is open."""
        return self._last_clock_sync_check is None or (
            now - self._last_clock_sync_check >= CLOCK_SYNC_INTERVAL
        )

    def _clock_sync_needed(self, now) -> bool:
        """Return whether the cached RTC state is far enough away to write."""
        device_now = self._device_clock_datetime()
        if device_now is None:
            _LOGGER.debug(
                "EcoVentCoordinator: syncing device clock because RTC state is missing"
            )
            return True

        drift = abs(self._local_wall_clock(now) - device_now)
        if drift <= CLOCK_SYNC_DRIFT:
            return False

        _LOGGER.info(
            "EcoVentCoordinator: syncing device clock for %s drift",
            drift,
        )
        return True

    def _record_clock_sync(self, now) -> None:
        """Remember a successful clock write from periodic or batched sync."""
        self._last_clock_sync = now

    def _recently_synced_clock(self, now) -> bool:
        """Avoid duplicate RTC writes before a fresh read confirms the new value."""
        return self._last_clock_sync is not None and (
            now - self._last_clock_sync < CLOCK_SYNC_INTERVAL
        )

    @property
    def silent_mode_enabled(self) -> bool:
        """Return whether HA should avoid beeping fan mode writes."""
        return self._silent_mode

    @property
    def silent_preset_mode(self) -> str | None:
        """Return the virtual preset shown while silent mode keeps manual speed."""
        return self._silent_preset_mode

    def set_silent_preset_mode(self, preset_mode: str | None) -> None:
        """Remember the HA-facing preset when the device stays in manual mode."""
        self._silent_preset_mode = preset_mode

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

    async def _async_reconcile_schedule_day(self, day: int):
        """Read one complete day after writes and expose only confirmed state."""
        try:
            confirmed_records = await self.hass.async_add_executor_job(
                self._fan.read_weekly_schedule_day,
                day,
            )
        except Exception as err:  # noqa: BLE001
            self._weekly_schedule.pop(day, None)
            _LOGGER.warning(
                "Failed to read schedule day %d after a write for %s: %s",
                day,
                self._fan.name,
                err,
            )
            return None

        if set(confirmed_records) != {1, 2, 3, 4}:
            self._weekly_schedule.pop(day, None)
            return None
        try:
            validate_schedule_day(
                [confirmed_records[period] for period in range(1, 5)]
            )
        except ValueError:
            self._weekly_schedule.pop(day, None)
            return None
        self._weekly_schedule[day] = confirmed_records
        return confirmed_records

    async def async_write_schedule(
        self,
        *,
        selected_day: str | None = None,
        weekly_schedule_enabled: bool | None = None,
        days: list[dict[str, object]] | None = None,
    ) -> None:
        """Apply one schedule payload from the custom dialog."""
        selected_day_index = (
            SCHEDULE_DAY_TO_INDEX[selected_day] if selected_day is not None else None
        )

        if (
            weekly_schedule_enabled is not None or days
        ) and not self._fan.profile_supports_parameter("weekly_schedule_setup"):
            raise RuntimeError(
                f"Weekly schedules are not supported by {self._fan.name}"
            )

        day_payloads = []
        prepared_day_writes = []
        requested_days: set[int] = set()

        def prepare_day_writes():
            working_records_by_day = {}
            prepared = []
            for day_label, day, day_payload in day_payloads:
                current_records = working_records_by_day.get(day)
                if current_records is None:
                    current_records = self.schedule_day_records(day)
                records_to_write = changed_schedule_records(
                    day,
                    current_records,
                    day_payload.get("periods", []),
                )
                invalid_speeds = []
                if records_to_write:
                    allowed_speeds = set(self._fan.device_profile.schedule_speed_modes)
                    invalid_speeds = sorted(
                        record.speed
                        for record in records_to_write
                        if record.speed not in allowed_speeds
                    )
                if invalid_speeds:
                    raise ValueError(
                        "Schedule speeds are not supported by "
                        f"{self._fan.name}: {invalid_speeds}"
                    )
                expected_records = dict(current_records)
                for record in records_to_write:
                    expected_records[record.period] = record
                if getattr(self._fan, "transport", None) == "bgcp_udp":
                    final_period = expected_records[4]
                    if (final_period.end_hour, final_period.end_minute) != (0, 0):
                        raise ValueError(
                            "BGCP schedule period 4 must end at midnight"
                        )
                working_records_by_day[day] = expected_records
                prepared.append((day_label, day, records_to_write, expected_records))
            return prepared

        if days:
            for day_payload in days:
                day_label = str(day_payload["day"])
                day = SCHEDULE_DAY_TO_INDEX[day_label]
                day_payloads.append((day_label, day, day_payload))

            requested_days = {day for _, day, _ in day_payloads}
            if self._fan.profile_supports_parameter("weekly_schedule_setup"):
                refreshed_days = await self.hass.async_add_executor_job(
                    self._load_schedule_days,
                    requested_days,
                )
                if refreshed_days != requested_days:
                    failed_days = sorted(requested_days - refreshed_days)
                    raise RuntimeError(
                        "Failed to refresh weekly schedule before writing "
                        f"days {failed_days} for {self._fan.name}"
                    )

            prepared_day_writes = prepare_day_writes()

        schedule_state_changed = False
        if weekly_schedule_enabled is not None:
            target = "on" if weekly_schedule_enabled else "off"
            if self._fan.weekly_schedule_state != target:
                written = await self.hass.async_add_executor_job(
                    self._fan.set_param,
                    "weekly_schedule_state",
                    target,
                )
                if not written:
                    raise RuntimeError(
                        "Failed to write weekly schedule state "
                        f"{target!r} for {self._fan.name}"
                    )
                # Confirm the new state through the normal coordinator path before
                # listeners render the schedule summary.
                await self.async_refresh()
                if (
                    not self.last_update_success
                    or self._fan.weekly_schedule_state != target
                ):
                    raise RuntimeError(
                        "Device did not confirm weekly schedule state "
                        f"{target!r} for {self._fan.name}"
                    )
                schedule_state_changed = True

        if schedule_state_changed and day_payloads:
            refreshed_days = await self.hass.async_add_executor_job(
                self._load_schedule_days,
                requested_days,
            )
            if refreshed_days != requested_days:
                failed_days = sorted(requested_days - refreshed_days)
                raise RuntimeError(
                    "Failed to refresh weekly schedule after changing its state "
                    f"for days {failed_days} on {self._fan.name}"
                )
            prepared_day_writes = prepare_day_writes()

        if prepared_day_writes:
            for (
                day_label,
                day,
                records_to_write,
                expected_records,
            ) in prepared_day_writes:
                for record in records_to_write:
                    written = await self.hass.async_add_executor_job(
                        self._fan.write_weekly_schedule_record,
                        record,
                    )
                    if not written:
                        await self._async_reconcile_schedule_day(day)
                        self.async_update_listeners()
                        raise RuntimeError(
                            "Failed to write schedule record "
                            f"{day_label} period {record.period}"
                        )

                if records_to_write:
                    confirmed_records = await self._async_reconcile_schedule_day(day)
                    if confirmed_records is None:
                        self.async_update_listeners()
                        raise RuntimeError(
                            "Incomplete schedule readback after writing "
                            f"{day_label} for {self._fan.name}"
                        )
                    if any(
                        confirmed_records.get(record.period)
                        != expected_records[record.period]
                        for record in records_to_write
                    ):
                        self.async_update_listeners()
                        raise RuntimeError(
                            "Device did not confirm schedule write for "
                            f"{day_label} on {self._fan.name}"
                        )

        if selected_day_index is not None:
            self._schedule_day = selected_day_index
        self.async_update_listeners()

    async def async_sync_device_clock(self) -> None:
        """Synchronize the device RTC with HA local time immediately."""
        now = self._device_clock_now()
        written = await self.hass.async_add_executor_job(
            self._fan.set_rtc_datetime, now
        )
        if not written:
            raise RuntimeError(
                f"Failed to synchronize device clock for {self._fan.name}"
            )
        await self.async_refresh()
        if not self.last_update_success:
            raise RuntimeError(
                f"Failed to confirm synchronized device clock for {self._fan.name}"
            )
        if not self._clock_sync_confirmed(now):
            raise RuntimeError(
                f"Device clock did not match synchronized time for {self._fan.name}"
            )
        self._record_clock_sync(now)

    def _clock_sync_confirmed(self, expected) -> bool:
        """Compare cached RTC state from the latest coordinator refresh."""
        device_now = self._device_clock_datetime()
        if device_now is None:
            return False
        return abs(self._local_wall_clock(expected) - device_now) <= CLOCK_SYNC_DRIFT

    async def async_refresh_confirmed(self) -> None:
        """Refresh entities and fail when Home Assistant swallowed the read error."""
        await self.async_refresh()
        if not self.last_update_success:
            raise RuntimeError(
                f"Failed to confirm updated state for {self._fan.name}"
            )
