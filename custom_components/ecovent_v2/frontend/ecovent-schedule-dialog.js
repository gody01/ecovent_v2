const DOMAIN = "ecovent_v2";
const MDI_FAN_SPEED_1 =
  "M13 19C13 17.59 13.5 16.3 14.3 15.28C14.17 14.97 14.03 14.65 13.86 14.34C14.26 14 14.57 13.59 14.77 13.11C15.26 13.21 15.78 13.39 16.25 13.67C17.07 13.25 18 13 19 13C20.05 13 21.03 13.27 21.89 13.74C21.95 13.37 22 12.96 22 12.5C22 8.92 18.03 8.13 14.33 10.13C14 9.73 13.59 9.42 13.11 9.22C13.3 8.29 13.74 7.24 14.73 6.75C17.09 5.57 17 2 12.5 2C8.93 2 8.14 5.96 10.13 9.65C9.72 9.97 9.4 10.39 9.21 10.87C8.28 10.68 7.23 10.25 6.73 9.26C5.56 6.89 2 7 2 11.5C2 15.07 5.95 15.85 9.64 13.87C9.96 14.27 10.39 14.59 10.88 14.79C10.68 15.71 10.24 16.75 9.26 17.24C6.9 18.42 7 22 11.5 22C12.31 22 13 21.78 13.5 21.41C13.19 20.67 13 19.86 13 19M12 13C11.43 13 11 12.55 11 12S11.43 11 12 11C12.54 11 13 11.45 13 12S12.54 13 12 13M17 15V17H18V23H20V15H17Z";
const MDI_FAN_SPEED_2 =
  "M13 19C13 17.59 13.5 16.3 14.3 15.28C14.17 14.97 14.03 14.65 13.86 14.34C14.26 14 14.57 13.59 14.77 13.11C15.26 13.21 15.78 13.39 16.25 13.67C17.07 13.25 18 13 19 13C20.05 13 21.03 13.27 21.89 13.74C21.95 13.37 22 12.96 22 12.5C22 8.92 18.03 8.13 14.33 10.13C14 9.73 13.59 9.42 13.11 9.22C13.3 8.29 13.74 7.24 14.73 6.75C17.09 5.57 17 2 12.5 2C8.93 2 8.14 5.96 10.13 9.65C9.72 9.97 9.4 10.39 9.21 10.87C8.28 10.68 7.23 10.25 6.73 9.26C5.56 6.89 2 7 2 11.5C2 15.07 5.95 15.85 9.64 13.87C9.96 14.27 10.39 14.59 10.88 14.79C10.68 15.71 10.24 16.75 9.26 17.24C6.9 18.42 7 22 11.5 22C12.31 22 13 21.78 13.5 21.41C13.19 20.67 13 19.86 13 19M12 13C11.43 13 11 12.55 11 12S11.43 11 12 11C12.54 11 13 11.45 13 12S12.54 13 12 13M16 15V17H19V18H18C16.9 18 16 18.9 16 20V23H21V21H18V20H19C20.11 20 21 19.11 21 18V17C21 15.9 20.11 15 19 15H16Z";
const MDI_FAN_SPEED_3 =
  "M13 19C13 17.59 13.5 16.3 14.3 15.28C14.17 14.97 14.03 14.65 13.86 14.34C14.26 14 14.57 13.59 14.77 13.11C15.26 13.21 15.78 13.39 16.25 13.67C17.07 13.25 18 13 19 13C20.05 13 21.03 13.27 21.89 13.74C21.95 13.37 22 12.96 22 12.5C22 8.92 18.03 8.13 14.33 10.13C14 9.73 13.59 9.42 13.11 9.22C13.3 8.29 13.74 7.24 14.73 6.75C17.09 5.57 17 2 12.5 2C8.93 2 8.14 5.96 10.13 9.65C9.72 9.97 9.4 10.39 9.21 10.87C8.28 10.68 7.23 10.25 6.73 9.26C5.56 6.89 2 7 2 11.5C2 15.07 5.95 15.85 9.64 13.87C9.96 14.27 10.39 14.59 10.88 14.79C10.68 15.71 10.24 16.75 9.26 17.24C6.9 18.42 7 22 11.5 22C12.31 22 13 21.78 13.5 21.41C13.19 20.67 13 19.86 13 19M12 13C11.43 13 11 12.55 11 12S11.43 11 12 11C12.54 11 13 11.45 13 12S12.54 13 12 13M21 21V20.5C21 19.67 20.33 19 19.5 19C20.33 19 21 18.33 21 17.5V17C21 15.89 20.1 15 19 15H16V17H19V18H17V20H19V21H16V23H19C20.11 23 21 22.11 21 21";
const MDI_POWER_SLEEP =
  "M18.73,18C15.4,21.69 9.71,22 6,18.64C2.33,15.31 2.04,9.62 5.37,5.93C6.9,4.25 9,3.2 11.27,3C7.96,6.7 8.27,12.39 12,15.71C13.63,17.19 15.78,18 18,18C18.25,18 18.5,18 18.73,18Z";

class EcoventScheduleDialog extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._open = false;
    this._busy = false;
    this._dirty = false;
    this._entityId = "";
    this._hass = undefined;
    this._draft = undefined;
    this._savedDraft = undefined;
    this._confirmDiscard = false;
    this._error = "";
    this._savedMessage = "";
    this._savedMessageTimer = undefined;
    this._returnFocusTo = undefined;
    this._dialogWithListeners = undefined;
    this._boundDialogPointerDown = (event) => this._handleDialogPointerDown(event);
    this._boundDialogHide = (event) => this._handleDialogHide(event);
    this._boundDialogClosed = (event) => this._handleDialogClosed(event);
  }

  showDialog({ hass, entityId }) {
    this._returnFocusTo = document.activeElement;
    this._hass = hass;
    this._entityId = entityId;
    this._draft = this._buildDraft();
    this._savedDraft = this._clone(this._draft);
    this._confirmDiscard = false;
    this._error = "";
    this._savedMessage = "";
    this._open = true;
    this._render();
    requestAnimationFrame(() => {
      this.shadowRoot?.querySelector("ha-dialog")?.focus?.();
    });
  }

  closeDialog({ force = false } = {}) {
    if (!force && this._dirty) {
      this._confirmDiscard = true;
      this._render();
      return;
    }
    if (this._savedMessageTimer) {
      clearTimeout(this._savedMessageTimer);
      this._savedMessageTimer = undefined;
    }
    this._open = false;
    this._busy = false;
    this._dirty = false;
    this._confirmDiscard = false;
    this._error = "";
    this._savedMessage = "";
    this._draft = undefined;
    this._savedDraft = undefined;
    this._detachDialogListeners();
    this._render();
    this._returnFocusTo?.focus?.();
    this._returnFocusTo = undefined;
  }

  _eventComesFromDialogScrim(event) {
    const path = event.composedPath?.() ?? [];
    const first = path[0];
    if (
      typeof HTMLDialogElement !== "undefined" &&
      !(first instanceof HTMLDialogElement)
    ) {
      return false;
    }
    if (typeof HTMLDialogElement === "undefined" && first?.localName !== "dialog") {
      return false;
    }

    const rect = first.getBoundingClientRect?.();
    if (!rect) {
      return false;
    }
    return (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    );
  }

  _detachDialogListeners() {
    if (!this._dialogWithListeners) {
      return;
    }
    this._dialogWithListeners.removeEventListener(
      "pointerdown",
      this._boundDialogPointerDown,
      true
    );
    this._dialogWithListeners.removeEventListener("wa-hide", this._boundDialogHide);
    this._dialogWithListeners.removeEventListener("closed", this._boundDialogClosed);
    this._dialogWithListeners = undefined;
  }

  _attachDialogListeners(dialog) {
    if (this._dialogWithListeners === dialog) {
      return;
    }
    this._detachDialogListeners();
    dialog.addEventListener("pointerdown", this._boundDialogPointerDown, true);
    dialog.addEventListener("wa-hide", this._boundDialogHide);
    dialog.addEventListener("closed", this._boundDialogClosed);
    this._dialogWithListeners = dialog;
  }

  _handleDialogPointerDown(event) {
    if (!this._eventComesFromDialogScrim(event)) {
      return;
    }
    event.preventDefault?.();
    event.stopPropagation?.();
    this.closeDialog({ force: !this._dirty });
  }

  _handleDialogHide(event) {
    const dialog = this._dialogWithListeners;
    if (event.target !== dialog) {
      return;
    }
    if (!this._dirty) {
      this.closeDialog({ force: true });
      return;
    }
    event.preventDefault?.();
    event.stopPropagation?.();
    this.closeDialog();
  }

  _handleDialogClosed(event) {
    const dialog = this._dialogWithListeners;
    if (event.target !== dialog) {
      return;
    }
    if (this._dirty) {
      this.closeDialog();
      return;
    }
    if (this._open) {
      this.closeDialog({ force: true });
    }
  }

  _entity(entityId) {
    return this._hass?.states?.[entityId];
  }

  _stateObj() {
    return this._entity(this._entityId);
  }

  _attrs() {
    return this._stateObj()?.attributes ?? {};
  }

  _clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  _dayShort(day) {
    return new Intl.DateTimeFormat(this._localeTag(), { weekday: "short" }).format(
      this._dayDate(day)
    );
  }

  _dayLabel(day) {
    return new Intl.DateTimeFormat(this._localeTag(), { weekday: "long" }).format(
      this._dayDate(day)
    );
  }

  _dayDate(day) {
    const index = [
      "Monday",
      "Tuesday",
      "Wednesday",
      "Thursday",
      "Friday",
      "Saturday",
      "Sunday",
    ].indexOf(day);
    return new Date(Date.UTC(2024, 0, 1 + Math.max(index, 0)));
  }

  _localeTag() {
    return this._hass?.locale?.language || navigator.language || "en";
  }

  _t(key, fallback, replacements = {}) {
    const translated = this._hass?.localize?.(
      `component.${DOMAIN}.ui.schedule.${key}`
    );
    let value = translated || fallback;
    for (const [name, replacement] of Object.entries(replacements)) {
      value = value.replace(`{${name}}`, replacement);
    }
    return value;
  }

  _normalizeTimeValue(value) {
    if (!value) {
      return "00:00";
    }
    return value.slice(0, 5);
  }

  _speedOptionPath(value) {
    if (value === "Standby") {
      return MDI_POWER_SLEEP;
    }
    if (value === "Low") {
      return MDI_FAN_SPEED_1;
    }
    if (value === "Medium") {
      return MDI_FAN_SPEED_2;
    }
    if (value === "High") {
      return MDI_FAN_SPEED_3;
    }
    return MDI_FAN_SPEED_1;
  }

  _speedKey(label) {
    return `speed_${String(label || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_")}`;
  }

  _speedLabel(label) {
    return this._t(this._speedKey(label), label || "Unknown");
  }

  _buildDraft() {
    const attrs = this._attrs();
    const days = Array.isArray(attrs.days) ? this._clone(attrs.days) : [];
    const selectedDay =
      attrs.selected_day ?? days[0]?.day ?? attrs.day_options?.[0] ?? "Monday";
    return {
      weekly_schedule_enabled: attrs.weekly_schedule_enabled === true,
      selected_day: selectedDay,
      edit_scope: "day",
      days,
    };
  }

  _scopeDays(scope, selectedDay) {
    if (scope === "weekdays") {
      return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
    }
    if (scope === "weekend") {
      return ["Saturday", "Sunday"];
    }
    if (scope === "all") {
      return [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
      ];
    }
    return selectedDay ? [selectedDay] : [];
  }

  _currentScopeDays() {
    if (!this._draft) {
      return [];
    }
    return this._scopeDays(this._draft.edit_scope, this._draft.selected_day);
  }

  _effectiveSelectedDay() {
    const scopeDays = this._currentScopeDays();
    if (!scopeDays.length) {
      return this._draft?.selected_day;
    }
    if (scopeDays.includes(this._draft?.selected_day)) {
      return this._draft.selected_day;
    }
    return scopeDays[0];
  }

  _currentDay() {
    if (!this._draft) {
      return undefined;
    }
    const selectedDay = this._effectiveSelectedDay();
    return this._draft.days.find((day) => day.day === selectedDay);
  }

  _setSelectedDay(day) {
    if (!this._draft || this._busy) {
      return;
    }
    this._draft.edit_scope = "day";
    this._draft.selected_day = day;
    this._confirmDiscard = false;
    this._render();
  }

  _setEditScope(scope) {
    if (!this._draft || this._busy) {
      return;
    }
    this._draft.edit_scope = scope;
    const scopeDays = this._currentScopeDays();
    if (scopeDays.length && !scopeDays.includes(this._draft.selected_day)) {
      this._draft.selected_day = scopeDays[0];
    }
    this._confirmDiscard = false;
    this._render();
  }

  _setWeeklyEnabled(enabled) {
    if (!this._draft || this._busy) {
      return;
    }
    this._draft.weekly_schedule_enabled = enabled;
    this._error = "";
    this._savedMessage = "";
    this._dirty = this._hasPersistedChanges();
    this._render();
  }

  _updatePeriod(periodNumber, patch) {
    if (!this._draft || this._busy) {
      return;
    }

    let changed = false;

    for (const dayName of this._currentScopeDays()) {
      const day = this._draft.days.find((item) => item.day === dayName);
      if (!day) {
        continue;
      }

      const period = day.periods.find((item) => item.period === periodNumber);
      if (!period) {
        continue;
      }

      const hasDiff = Object.entries(patch).some(([key, value]) => period[key] !== value);
      if (!hasDiff) {
        continue;
      }

      Object.assign(period, patch);
      this._refreshDaySummaries(day);
      changed = true;
    }

    if (!changed) {
      return;
    }

    this._error = "";
    this._savedMessage = "";
    this._dirty = this._hasPersistedChanges();
    this._render();
  }

  _periodPayloadSignature(period) {
    const signature = {
      period: period?.period,
      speed: period?.speed,
    };
    if (period?.editable_end) {
      signature.end = this._normalizeTimeValue(period.end);
    }
    return signature;
  }

  _changedScheduleDays() {
    if (!this._draft) {
      return [];
    }

    if (!this._savedDraft) {
      return this._draft.days ?? [];
    }

    const savedDays = new Map(
      (this._savedDraft.days ?? []).map((day) => [day.day, day])
    );

    return (this._draft.days ?? [])
      .map((day) => {
        const savedPeriods = new Map(
          (savedDays.get(day.day)?.periods ?? []).map((period) => [
            period.period,
            period,
          ])
        );
        const periods = (day.periods ?? []).filter((period) => {
          return (
            JSON.stringify(this._periodPayloadSignature(period)) !==
            JSON.stringify(
              this._periodPayloadSignature(savedPeriods.get(period.period))
            )
          );
        });
        return {
          day: day.day,
          periods,
        };
      })
      .filter((day) => day.periods.length > 0);
  }

  _hasPersistedChanges() {
    if (!this._draft) {
      return false;
    }

    if (!this._savedDraft) {
      return true;
    }

    return (
      this._draft.weekly_schedule_enabled !==
        this._savedDraft.weekly_schedule_enabled ||
      this._changedScheduleDays().length > 0
    );
  }

  _savePayload() {
    const days = this._changedScheduleDays().map((day) => ({
      day: day.day,
      periods: day.periods.map((period) => {
        const payload = {
          period: period.period,
          speed: period.speed,
        };

        if (period.editable_end) {
          payload.end = this._normalizeTimeValue(period.end);
        }

        return payload;
      }),
    }));

    return {
      selected_day: this._draft?.selected_day,
      weekly_schedule_enabled: this._draft?.weekly_schedule_enabled,
      days,
    };
  }

  _compactPeriodSummary(summary) {
    if (!summary) {
      return "";
    }
    return summary
      .replace(/:00/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  _minutes(value) {
    const [hours, minutes] = this._normalizeTimeValue(value)
      .split(":")
      .map((part) => Number(part));
    return hours * 60 + minutes;
  }

  _formatError(error) {
    return error?.message || String(error || "Unknown error");
  }

  _setSavedMessage(message) {
    if (this._savedMessageTimer) {
      clearTimeout(this._savedMessageTimer);
    }
    this._savedMessage = message;
    this._savedMessageTimer = setTimeout(() => {
      this._savedMessage = "";
      this._render();
    }, 2400);
  }

  _validationErrors(day = this._currentDay()) {
    const errors = new Map();
    let previousEnd = 0;

    for (const period of day?.periods || []) {
      if (!period.editable_end) {
        continue;
      }

      const end = this._minutes(period.end);
      if (end <= previousEnd) {
        errors.set(
          period.period,
          this._t("end_after", "End time must be after {time}.", {
            time: this._formatDisplayMinutes(previousEnd),
          })
        );
      }
      previousEnd = end;
    }

    return errors;
  }

  _isDraftValid() {
    if (!this._draft) {
      return false;
    }
    return (this._draft.days || []).every(
      (day) => this._validationErrors(day).size === 0
    );
  }

  _currentValidationErrors() {
    return this._validationErrors(this._currentDay());
  }

  _formatTime(minutes) {
    const hour = Math.floor(minutes / 60);
    const minute = minutes % 60;
    return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  }

  _uses12HourTime() {
    // Native time inputs follow the browser/OS time picker, not Home Assistant's
    // frontend setting. Match the browser here so static period starts and
    // editable time fields never mix 24-hour and AM/PM display in one row.
    return (
      new Intl.DateTimeFormat(undefined, { hour: "numeric" })
        .resolvedOptions()
        .hour12 === true
    );
  }

  _formatDisplayMinutes(minutes) {
    return this._formatDisplayTime(this._formatTime(minutes));
  }

  _formatDisplayTime(value) {
    const normalized = this._normalizeTimeValue(value);
    if (!this._uses12HourTime()) {
      return normalized;
    }
    const [hour, minute] = normalized.split(":").map((part) => Number(part));
    return new Intl.DateTimeFormat(this._localeTag(), {
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(2024, 0, 1, hour, minute));
  }

  _periodBounds(period) {
    const summary = period.summary ?? "";
    const match = summary.match(/^(\d{2}:\d{2})-(\d{2}:\d{2})\s+(.+)$/);
    if (match) {
      return {
        start: match[1],
        end: match[2],
        speed: match[3],
      };
    }

    const fallbackEnd = period.editable_end ? period.end ?? "00:00" : "00:00";
    return {
      start: "00:00",
      end: fallbackEnd,
      speed: period.speed ?? "Unknown",
    };
  }

  _refreshDaySummaries(day) {
    let start = "00:00";

    for (const period of day.periods || []) {
      const end = period.editable_end ? this._normalizeTimeValue(period.end) : "00:00";
      const speed = period.speed ?? "Unknown";
      period.summary = `${start}-${end} ${speed}`;
      if (period.editable_end) {
        start = end;
      }
    }
  }

  _mergedDaySummary(day) {
    const merged = [];

    for (const period of day.periods || []) {
      const current = this._periodBounds(period);
      const previous = merged[merged.length - 1];

      if (previous && previous.speed === current.speed && previous.end === current.start) {
        previous.end = current.end;
      } else {
        merged.push({ ...current });
      }
    }

    if (merged.length === 1 && merged[0].start === "00:00") {
      return this._t("all_day", "{speed} all day", {
        speed: this._speedLabel(merged[0].speed),
      });
    }

    if (
      merged.length === 2 &&
      merged[0].start === "00:00" &&
      merged[1].end === "00:00"
    ) {
      return this._t("until_then", "{speed} until {time}, then {next_speed}", {
        speed: this._speedLabel(merged[0].speed),
        time: this._formatDisplayTime(merged[0].end),
        next_speed: this._speedLabel(merged[1].speed),
      });
    }

    return merged
      .map((item) => {
        if (item.end === "00:00") {
          return this._t("rest_of_day", "{speed} rest of day", {
            speed: this._speedLabel(item.speed),
          });
        }
        return this._t("time_range", "{speed} {start}-{end}", {
          speed: this._speedLabel(item.speed),
          start: this._formatDisplayTime(item.start),
          end: this._formatDisplayTime(item.end),
        });
      })
      .join(", ");
  }

  _groupedWeekRows(days) {
    const groups = [];

    for (const day of days || []) {
      const summary = this._mergedDaySummary(day);
      const previous = groups[groups.length - 1];

      if (previous && previous.summary === summary) {
        previous.days.push(day.day);
      } else {
        groups.push({ days: [day.day], summary });
      }
    }

    return groups;
  }

  _groupedDayLabel(days) {
    if (!days.length) {
      return "";
    }
    if (days.length === 7) {
      return this._t("scope_all", "Every day");
    }
    if (days.join("|") === "Monday|Tuesday|Wednesday|Thursday|Friday") {
      return this._t("scope_weekdays", "Weekdays");
    }
    if (days.join("|") === "Saturday|Sunday") {
      return this._t("scope_weekend", "Weekend");
    }
    if (days.length === 1) {
      return this._dayShort(days[0]);
    }
    return `${this._dayShort(days[0])}-${this._dayShort(days[days.length - 1])}`;
  }

  _scopeLabel(scope) {
    if (scope === "weekdays") {
      return this._t("scope_weekdays", "Weekdays").toLowerCase();
    }
    if (scope === "weekend") {
      return this._t("scope_weekend", "Weekend").toLowerCase();
    }
    if (scope === "all") {
      return this._t("scope_all", "Every day").toLowerCase();
    }
    return this._t("scope_day", "This day").toLowerCase();
  }

  _scopeControlLabel(scope) {
    if (scope === "day") {
      return this._t("scope_day", "This day");
    }
    if (scope === "weekdays") {
      return this._t("scope_weekdays", "Weekdays");
    }
    if (scope === "weekend") {
      return this._t("scope_weekend", "Weekend");
    }
    if (scope === "all") {
      return this._t("scope_all", "Every day");
    }
    return this._scopeLabel(scope);
  }

  _scopeHelperText() {
    const scope = this._draft?.edit_scope ?? "day";
    if (scope === "weekdays") {
      return this._t("helper_weekdays", "Changes will be applied to Mon-Fri.");
    }
    if (scope === "weekend") {
      return this._t("helper_weekend", "Changes will be applied to Sat-Sun.");
    }
    if (scope === "all") {
      return this._t("helper_all", "Changes will be applied to every day.");
    }
    return this._t(
      "helper_day",
      "Changes will be applied only to the selected day."
    );
  }

  _editingSubhead() {
    const scope = this._draft?.edit_scope ?? "day";
    if (scope === "day") {
      return this._t("editing_day", "Editing {day}", {
        day: this._dayLabel(this._draft?.selected_day ?? "Monday"),
      });
    }
    return this._t(`editing_${scope === "all" ? "all" : scope}`, `Editing ${this._scopeLabel(scope)}`);
  }

  _scopeKeyForDays(days) {
    if (days.length === 7) {
      return "all";
    }
    if (days.join("|") === "Monday|Tuesday|Wednesday|Thursday|Friday") {
      return "weekdays";
    }
    if (days.join("|") === "Saturday|Sunday") {
      return "weekend";
    }
    if (days.length === 1) {
      return "day";
    }
    return null;
  }

  _weekGroupRow(group) {
    const activeScope = this._currentScopeDays();
    const active =
      activeScope.length === group.days.length &&
      activeScope.every((day, index) => day === group.days[index]);
    const scopeKey = this._scopeKeyForDays(group.days);
    const targetDay = group.days[0];
    return `
      <button
        class="week-row ${active ? "active" : ""}"
        data-day="${targetDay}"
        ${scopeKey ? `data-edit-scope="${scopeKey}"` : ""}
        ${this._busy ? "disabled" : ""}
      >
        <div class="week-day">${this._groupedDayLabel(group.days)}</div>
        <div class="week-value">${group.summary}</div>
      </button>
    `;
  }

  _dayChip(day) {
    const active = day === this._draft?.selected_day;
    return `
      <button
        class="day-chip ${active ? "active" : ""}"
        data-day="${day}"
        ${this._busy ? "disabled" : ""}
      >
        ${this._dayShort(day)}
      </button>
    `;
  }

  async _callService(service, serviceData) {
    if (!this._hass) {
      return;
    }
    await this._hass.callService(DOMAIN, service, {
      entity_id: this._entityId,
      ...serviceData,
    });
  }

  async _save() {
    if (!this._draft || !this._dirty || this._busy) {
      return;
    }
    if (!this._isDraftValid()) {
      this._error = this._t(
        "invalid_order",
        "Periods must be in chronological order."
      );
      this._render();
      return;
    }
    const payload = this._savePayload();
    const weeklyChanged =
      this._savedDraft &&
      this._draft.weekly_schedule_enabled !==
        this._savedDraft.weekly_schedule_enabled;
    if (!weeklyChanged && payload.days.length === 0) {
      this._dirty = false;
      this._render();
      return;
    }
    this._busy = true;
    this._error = "";
    this._savedMessage = "";
    this._render();
    try {
      await this._callService("write_schedule", payload);
      this._savedDraft = this._clone(this._draft);
      this._dirty = false;
      this._confirmDiscard = false;
      this._setSavedMessage(this._t("saved", "Saved"));
    } catch (error) {
      this._error = `${this._t(
        "could_not_save",
        "Could not save schedule."
      )} ${this._formatError(error)}`;
      this._dirty = true;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _periodCard(periodData, speedOptions) {
    const bounds = this._periodBounds(periodData);
    const period = periodData.period;
    const error = this._currentValidationErrors().get(period);

    return `
      <section class="period-card">
        <div class="period-layout">
          <div class="period-side">
            <div class="period-marker">${period}</div>
          </div>
          <div class="period-main">
            <div class="period-start">
              <span class="field-label">${this._t("starts", "Starts")}</span>
              <span class="start-time">${this._formatDisplayTime(bounds.start)}</span>
            </div>
            <label class="field field-time">
              <span class="field-label">${this._t("until", "Until")}</span>
              ${
                periodData.editable_end
                  ? `
                    <input
                      type="time"
                      class="time-input"
                      data-end-input="${period}"
                      value="${this._normalizeTimeValue(periodData.end)}"
                      ${this._busy ? "disabled" : ""}
                    />
                    ${error ? `<span class="field-error">${error}</span>` : ""}
                  `
                  : `<div class="end-of-day">${this._t("end_of_day", "End of day")}</div>`
              }
            </label>
            <label class="field speed-field">
              <span class="field-label">${this._t("speed", "Speed")}</span>
              <ha-control-select-menu
                class="speed-control"
                data-speed-select="${period}"
                value="${periodData.speed ?? speedOptions[0]?.value ?? ""}"
                label="${this._t("speed", "Speed")}"
                show-arrow
              ></ha-control-select-menu>
              <span class="speed-value" aria-hidden="true">
                ${this._speedLabel(periodData.speed ?? speedOptions[0]?.value)}
              </span>
            </label>
          </div>
        </div>
      </section>
    `;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const stateObj = this._stateObj();
    const attrs = this._attrs();
    const draft = this._draft;

    if (!this._open || !stateObj || !draft) {
      this.shadowRoot.innerHTML = "";
      return;
    }

    const speedOptions = Array.isArray(attrs.speed_option_meta)
      ? attrs.speed_option_meta
      : [];
    const currentDay = this._currentDay();
    const periods = Array.isArray(currentDay?.periods) ? currentDay.periods : [];
    const title = this._t("title", "Weekly schedule");
    const subtitle = stateObj.attributes.friendly_name ?? "Schedule";
    const groupedWeekRows = this._groupedWeekRows(draft.days);
    const isValid = this._isDraftValid();
    const rendered = `
      <style>
        :host {
          display: contents;
          z-index: 10000;
        }

        * {
          box-sizing: border-box;
          font: inherit;
        }

        button,
        input,
        select {
          font: inherit;
        }

        .eyebrow,
        .field-label,
        .meta-label,
        .week-summary-title {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        ha-dialog {
          --ha-dialog-width-lg: 820px;
          --ha-dialog-max-height: min(860px, calc(100dvh - 20px));
          --ha-dialog-border-radius: 28px;
          --dialog-content-padding: 0 20px 8px;
        }

        .content {
          display: grid;
          gap: 0;
        }

        .top-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--secondary-background-color);
          padding: 9px 14px;
          margin-bottom: 6px;
        }

        .toggle-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }

        .meta-value {
          margin-top: 4px;
          font-size: 17px;
        }

        .schedule-toggle {
          --switch-checked-button-color: var(--primary-color);
          --switch-checked-track-color: color-mix(
            in srgb,
            var(--primary-color) 32%,
            transparent
          );
        }

        .scope-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
          margin-top: 7px;
        }

        .scope-helper {
          color: var(--secondary-text-color);
          font-size: 12px;
          margin-top: 6px;
        }

        .scope-label {
          color: var(--secondary-text-color);
          font-size: 13px;
          margin-right: 4px;
        }

        .group-chip {
          min-height: 32px;
          border-radius: 16px;
          border: 1px solid var(--divider-color);
          background: var(--ha-card-background, var(--card-background-color));
          color: var(--primary-text-color);
          padding: 0 12px;
          cursor: pointer;
          white-space: nowrap;
          font-size: 13px;
        }

        .group-chip:hover {
          border-color: var(--primary-color);
        }

        .group-chip.active {
          border-color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }

        .group-chip:disabled {
          opacity: 0.6;
          cursor: default;
        }

        .week-summary {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--ha-card-background, var(--card-background-color));
          padding: 5px;
          margin-bottom: 5px;
        }

        .day-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 7px;
          margin-bottom: 7px;
        }

        .day-chip {
          min-width: 44px;
          min-height: 34px;
          border-radius: 17px;
          border: 1px solid var(--divider-color);
          background: var(--ha-card-background, var(--card-background-color));
          color: var(--primary-text-color);
          padding: 0 12px;
          cursor: pointer;
        }

        .day-chip.active {
          border-color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 16%, transparent);
        }

        .week-summary-title {
          margin: 2px 6px 6px;
        }

        .week-summary-grid {
          display: grid;
          gap: 1px;
        }

        .week-row {
          display: grid;
          grid-template-columns: 72px minmax(0, 1fr);
          gap: 10px;
          align-items: center;
          width: 100%;
          border: none;
          border-radius: 10px;
          background: transparent;
          padding: 6px 8px;
          text-align: left;
          cursor: pointer;
          font-size: 12px;
          line-height: 1.35;
          color: var(--secondary-text-color);
        }

        .week-row.active {
          color: var(--primary-text-color);
          background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        }

        .week-day {
          font-weight: 600;
        }

        .week-value {
          min-width: 0;
          white-space: normal;
          overflow: visible;
          text-overflow: clip;
        }

        .periods {
          display: grid;
          gap: 4px;
          overflow: visible;
        }

        .periods-header {
          display: grid;
          grid-template-columns: 28px 92px 192px minmax(240px, 1fr);
          gap: 12px;
          align-items: end;
          padding: 0 12px 2px;
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        .period-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 6px 12px;
          background: var(--ha-card-background, var(--card-background-color));
          overflow: visible;
        }

        .period-layout {
          display: grid;
          grid-template-columns: 28px minmax(0, 1fr);
          gap: 12px;
          align-items: start;
        }

        .period-side {
          display: flex;
          justify-items: center;
          align-items: center;
          justify-content: center;
          min-height: 44px;
        }

        .period-main {
          display: grid;
          grid-template-columns: 92px 192px minmax(240px, 1fr);
          gap: 12px;
          align-items: center;
          min-width: 0;
        }

        .period-start {
          min-width: 0;
          display: grid;
          gap: 3px;
        }

        .start-time {
          color: var(--primary-text-color);
          font-size: 14px;
          line-height: 1.3;
        }

        .period-marker {
          display: grid;
          place-items: center;
          width: 28px;
          height: 28px;
          border-radius: 14px;
          background: color-mix(in srgb, var(--primary-color) 18%, transparent);
          color: var(--primary-text-color);
          border: 1px solid color-mix(in srgb, var(--primary-color) 55%, transparent);
        }

        .field {
          display: grid;
          gap: 0;
          min-width: 0;
        }

        .field-label {
          display: none;
        }

        .field-time {
          width: 192px;
        }

        .end-of-day {
          color: var(--secondary-text-color);
          line-height: 44px;
          min-height: 44px;
        }

        .time-input {
          display: block;
          width: 100%;
          min-height: 44px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 0 12px;
          color-scheme: light dark;
        }

        .field-error {
          color: var(--error-color);
          font-size: 12px;
          line-height: 1.3;
          margin-top: 4px;
        }

        .speed-control {
          display: block;
          width: 100%;
          --control-select-menu-height: 44px;
          --control-select-menu-border-radius: 10px;
          --control-select-menu-background-color: var(--secondary-background-color);
          --control-select-menu-background-opacity: 1;
          --control-select-menu-focus-color: var(--primary-color);
        }

        .speed-field {
          position: relative;
        }

        .speed-value {
          position: absolute;
          top: 50%;
          left: 52px;
          right: 38px;
          transform: translateY(-50%);
          color: var(--primary-text-color);
          font-size: 14px;
          line-height: 1.2;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          pointer-events: none;
        }

        .error-box,
        .discard-box {
          border-radius: 12px;
          margin-bottom: 8px;
          padding: 10px 12px;
          font-size: 13px;
          line-height: 1.35;
        }

        .error-box {
          border: 1px solid color-mix(in srgb, var(--error-color) 60%, transparent);
          color: var(--error-color);
          background: color-mix(in srgb, var(--error-color) 10%, transparent);
        }

        .discard-box {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          align-items: center;
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
        }

        .footer-shell {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          width: 100%;
        }

        .footer-note {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .actions,
        ha-dialog-footer {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        ha-button.action {
          --ha-button-border-radius: 10px;
          min-width: 96px;
        }

        @media (max-width: 800px) {
          ha-dialog {
            --dialog-content-padding: 0 16px 8px;
          }

          .period-card {
            padding: 10px;
          }

          .periods-header {
            display: none;
          }

          .week-row {
            grid-template-columns: 72px minmax(0, 1fr);
            align-items: start;
          }

          .week-value {
            white-space: normal;
            overflow: visible;
            text-overflow: clip;
          }

          .period-main {
            grid-template-columns: 1fr;
            gap: 8px;
            align-items: start;
          }

          .period-start {
            grid-template-columns: auto minmax(0, 1fr);
            align-items: baseline;
            gap: 8px;
          }

          .field {
            gap: 4px;
          }

          .field-label {
            display: block;
          }

          .field-time {
            width: auto;
          }

          .discard-box {
            align-items: stretch;
            flex-direction: column;
          }

          .footer-shell {
            align-items: stretch;
            flex-direction: column;
          }

          ha-dialog-footer,
          .actions {
            width: 100%;
          }

          ha-button.action {
            flex: 1 1 auto;
          }
        }
      </style>
      <ha-dialog
        width="large"
        prevent-scrim-close
        header-title="${title}"
        header-subtitle="${subtitle} · ${this._editingSubhead()}"
      >
        <div class="content">
          ${this._error ? `<div class="error-box">${this._error}</div>` : ""}
          ${
            this._confirmDiscard
              ? `
                <div class="discard-box">
                  <div>${this._t("discard_prompt", "Discard unsaved changes?")}</div>
                  <div class="actions">
                    <ha-button appearance="plain" variant="neutral" class="action" id="keep-editing">${this._t("keep_editing", "Keep editing")}</ha-button>
                    <ha-button appearance="plain" variant="danger" class="action" id="discard-close">${this._t("discard", "Discard")}</ha-button>
                  </div>
                </div>
              `
              : ""
          }
          <div class="top-card">
            <div class="toggle-row">
              <div>
                <div class="meta-label">${this._t("weekly_schedule", "Weekly schedule")}</div>
                <div class="meta-value">${draft.weekly_schedule_enabled ? this._t("enabled", "Enabled") : this._t("disabled", "Disabled")}</div>
                <div class="scope-helper">${this._t("disabled_helper", "When disabled, the device ignores this weekly schedule.")}</div>
              </div>
              <ha-switch
                class="schedule-toggle"
                aria-label="${this._t("weekly_schedule", "Weekly schedule")}"
                id="weekly-toggle"
                ${this._busy ? "disabled" : ""}
              ></ha-switch>
            </div>
            <div class="scope-row">
              <span class="scope-label">${this._t("editing", "Editing")}</span>
              ${["day", "weekdays", "weekend", "all"]
                .map(
                  (scope) => `
                    <button
                      class="group-chip ${draft.edit_scope === scope ? "active" : ""}"
                      data-edit-scope="${scope}"
                      ${this._busy ? "disabled" : ""}
                    >${this._scopeControlLabel(scope)}</button>
                  `
                )
                .join("")}
            </div>
            <div class="scope-helper">${this._scopeHelperText()}</div>
          </div>
          <div class="day-strip">
            ${draft.days.map((day) => this._dayChip(day.day)).join("")}
          </div>
          <div class="week-summary">
            <div class="week-summary-title">${this._t("week_overview", "Week overview")}</div>
            <div class="week-summary-grid">
              ${groupedWeekRows.map((group) => this._weekGroupRow(group)).join("")}
            </div>
          </div>
          <div class="periods">
            <div class="periods-header" aria-hidden="true">
              <div></div>
              <div>${this._t("starts", "Starts")}</div>
              <div>${this._t("until", "Until")}</div>
              <div>${this._t("speed", "Speed")}</div>
            </div>
            ${periods
              .map((periodData) => this._periodCard(periodData, speedOptions))
              .join("")}
          </div>
        </div>
        <div class="footer-shell" slot="footer">
          <div class="footer-note">
            ${
              this._busy
                ? this._t("saving_changes", "Saving changes...")
                : this._dirty
                  ? this._t("unsaved_changes", "Unsaved changes")
                  : this._savedMessage
            }
          </div>
          <ha-dialog-footer>
            <ha-button
              appearance="plain"
              variant="neutral"
              class="action"
              id="discard"
              slot="secondaryAction"
              ${this._busy || !this._dirty ? "disabled" : ""}
            >${this._t("discard_changes", "Discard changes")}</ha-button>
            <ha-button
              variant="brand"
              class="action"
              id="save"
              slot="primaryAction"
              ${this._busy || !this._dirty || !isValid ? "disabled" : ""}
              ${this._busy ? "loading" : ""}
            >${this._busy ? this._t("saving", "Saving...") : this._t("save_schedule", "Save schedule")}</ha-button>
          </ha-dialog-footer>
        </div>
      </ha-dialog>
    `;

    const existingDialog = this.shadowRoot.querySelector("ha-dialog");
    if (existingDialog) {
      const template = document.createElement("template");
      template.innerHTML = rendered;
      const nextDialog = template.content.querySelector("ha-dialog");
      if (nextDialog) {
        existingDialog.replaceChildren(...Array.from(nextDialog.childNodes));
        for (const attr of Array.from(existingDialog.attributes)) {
          existingDialog.removeAttribute(attr.name);
        }
        for (const attr of Array.from(nextDialog.attributes)) {
          existingDialog.setAttribute(attr.name, attr.value);
        }
      }
    } else {
      this.shadowRoot.innerHTML = rendered;
    }

    const dialog = this.shadowRoot.querySelector("ha-dialog");
    if (dialog) {
      this._attachDialogListeners(dialog);
      dialog.open = true;
    }
    this.shadowRoot.getElementById("keep-editing")?.addEventListener("click", () => {
      this._confirmDiscard = false;
      this._render();
    });
    this.shadowRoot.getElementById("discard-close")?.addEventListener("click", () => {
      this.closeDialog({ force: true });
    });
    this.shadowRoot.getElementById("discard")?.addEventListener("click", () => {
      const currentSelectedDay = this._draft?.selected_day;
      const currentEditScope = this._draft?.edit_scope;
      this._draft = this._savedDraft ? this._clone(this._savedDraft) : this._buildDraft();
      if (
        currentSelectedDay &&
        this._draft?.days?.some((day) => day.day === currentSelectedDay)
      ) {
        this._draft.selected_day = currentSelectedDay;
      }
      if (currentEditScope) {
        this._draft.edit_scope = currentEditScope;
      }
      this._dirty = false;
      this._confirmDiscard = false;
      this._error = "";
      this._savedMessage = "";
      this._render();
    });
    this.shadowRoot.getElementById("save")?.addEventListener("click", () => {
      this._save().catch((error) => {
        this._error = `${this._t(
          "could_not_save",
          "Could not save schedule."
        )} ${this._formatError(error)}`;
        this._dirty = true;
        this._busy = false;
        this._render();
      });
    });

    const weeklyToggle = this.shadowRoot.getElementById("weekly-toggle");
    if (weeklyToggle) {
      weeklyToggle.checked = draft.weekly_schedule_enabled;
      weeklyToggle.addEventListener("change", (event) => {
        this._setWeeklyEnabled(event.target.checked);
      });
    }

    this.shadowRoot.querySelectorAll("[data-speed-select]").forEach((element) => {
      const period = Number(element.dataset.speedSelect);
      const periodData = periods.find((item) => item.period === period);
      element.options = speedOptions.map((option) => ({
        value: option.value,
        label: this._speedLabel(option.label),
        iconPath: this._speedOptionPath(option.value),
      }));
      element.value = periodData?.speed ?? speedOptions[0]?.value;
      element.disabled = this._busy;
    });

    this.shadowRoot.querySelectorAll(".day-chip[data-day]").forEach((button) => {
      button.addEventListener("click", () => this._setSelectedDay(button.dataset.day));
    });

    this.shadowRoot.querySelectorAll("[data-edit-scope]").forEach((button) => {
      button.addEventListener("click", () => {
        const scope = button.dataset.editScope;
        if (scope === "day" && button.dataset.day) {
          this._setSelectedDay(button.dataset.day);
          return;
        }
        this._setEditScope(scope);
        if (button.dataset.day) {
          this._draft.selected_day = button.dataset.day;
          this._render();
        }
      });
    });

    this.shadowRoot.querySelectorAll(".week-row[data-day]").forEach((button) => {
      if (button.dataset.editScope) {
        return;
      }
      button.addEventListener("click", () => this._setSelectedDay(button.dataset.day));
    });

    this.shadowRoot.querySelectorAll("[data-speed-select]").forEach((input) => {
      input.addEventListener("wa-select", (event) => {
        const value = event.detail?.item?.value;
        if (!value) {
          return;
        }
        input.value = value;
        this._updatePeriod(Number(input.dataset.speedSelect), {
          speed: value,
        });
      });
    });

    this.shadowRoot.querySelectorAll("[data-end-input]").forEach((input) => {
      const handleTimeInput = (event) => {
        const value = event.currentTarget?.value;
        if (!value) {
          return;
        }
        this._updatePeriod(Number(input.dataset.endInput), {
          end: this._normalizeTimeValue(value),
        });
      };
      input.addEventListener("input", handleTimeInput);
      input.addEventListener("change", handleTimeInput);
    });
  }
}

customElements.define("ecovent-schedule-dialog", EcoventScheduleDialog);

const ensureDialog = () => {
  let dialog = document.querySelector("ecovent-schedule-dialog");
  if (!dialog) {
    dialog = document.createElement("ecovent-schedule-dialog");
    document.body.appendChild(dialog);
  }
  return dialog;
};

const getHass = () => document.querySelector("home-assistant")?.hass;

window.addEventListener(
  "keydown",
  (event) => {
    if (event.key === "Escape") {
      document.querySelector("ecovent-schedule-dialog")?.closeDialog();
    }
  },
  true
);

window.addEventListener(
  "hass-more-info",
  (event) => {
    const entityId = event.detail?.entityId;
    const hass = getHass();
    const stateObj = entityId ? hass?.states?.[entityId] : undefined;
    if (!stateObj || stateObj.attributes?.editor !== "ecovent_schedule") {
      return;
    }

    event.stopImmediatePropagation();
    event.stopPropagation();
    if (event.preventDefault) {
      event.preventDefault();
    }

    ensureDialog().showDialog({ hass, entityId });
  },
  true
);
