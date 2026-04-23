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
  }

  showDialog({ hass, entityId }) {
    this._hass = hass;
    this._entityId = entityId;
    this._draft = this._buildDraft();
    this._open = true;
    this._render();
  }

  closeDialog() {
    this._open = false;
    this._busy = false;
    this._dirty = false;
    this._draft = undefined;
    this._render();
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
    return day.slice(0, 3);
  }

  _copyTargetLabel(day) {
    return day ? day.toLowerCase() : "this day";
  }

  _timeLocale() {
    return this._hass.locale;
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

  _buildDraft() {
    const attrs = this._attrs();
    const days = Array.isArray(attrs.days) ? this._clone(attrs.days) : [];
    const selectedDay =
      attrs.selected_day ?? days[0]?.day ?? attrs.day_options?.[0] ?? "Monday";
    return {
      weekly_schedule_enabled: attrs.weekly_schedule_enabled === true,
      selected_day: selectedDay,
      days,
    };
  }

  _currentDay() {
    if (!this._draft) {
      return undefined;
    }
    return this._draft.days.find((day) => day.day === this._draft.selected_day);
  }

  _setSelectedDay(day) {
    if (!this._draft || this._busy) {
      return;
    }
    this._draft.selected_day = day;
    this._render();
  }

  _setWeeklyEnabled(enabled) {
    if (!this._draft || this._busy) {
      return;
    }
    this._draft.weekly_schedule_enabled = enabled;
    this._dirty = true;
    this._render();
  }

  _updatePeriod(periodNumber, patch) {
    if (!this._draft || this._busy) {
      return;
    }

    const day = this._currentDay();
    if (!day) {
      return;
    }

    const period = day.periods.find((item) => item.period === periodNumber);
    if (!period) {
      return;
    }

    Object.assign(period, patch);
    this._dirty = true;
    this._render();
  }

  _cloneCurrentDayPeriods() {
    return this._clone(this._currentDay()?.periods ?? []);
  }

  _applyCurrentDayTo(dayNames) {
    if (!this._draft || this._busy) {
      return;
    }

    const sourcePeriods = this._cloneCurrentDayPeriods();
    this._draft.days = this._draft.days.map((day) =>
      dayNames.includes(day.day) ? { ...day, periods: this._clone(sourcePeriods) } : day
    );
    this._dirty = true;
    this._render();
  }

  _savePayload() {
    return {
      selected_day: this._draft?.selected_day,
      weekly_schedule_enabled: this._draft?.weekly_schedule_enabled,
      days: this._draft?.days,
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

    if (
      merged.length === 1 &&
      merged[0].start === "00:00" &&
      (merged[0].end === "00:00" || merged[0].end === "24:00")
    ) {
      return `All day ${merged[0].speed}`;
    }

    return merged
      .map((item) => `${this._compactPeriodSummary(`${item.start}-${item.end} ${item.speed}`)}`)
      .join("  •  ");
  }

  _compactDaySummary(day) {
    return this._mergedDaySummary(day);
  }

  _groupedWeekRows(days) {
    const groups = [];

    for (const day of days || []) {
      const summary = this._compactDaySummary(day);
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
      return "All days";
    }
    if (days.join("|") === "Monday|Tuesday|Wednesday|Thursday|Friday") {
      return "Weekdays";
    }
    if (days.join("|") === "Saturday|Sunday") {
      return "Weekend";
    }
    if (days.length === 1) {
      return this._dayShort(days[0]);
    }
    return `${this._dayShort(days[0])}-${this._dayShort(days[days.length - 1])}`;
  }

  _weekGroupRow(group) {
    const active = group.days.includes(this._draft?.selected_day);
    const targetDay = active ? this._draft?.selected_day : group.days[0];
    return `
      <button
        class="week-row ${active ? "active" : ""}"
        data-day="${targetDay}"
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
    if (!this._hass || this._busy) {
      return;
    }
    this._busy = true;
    this._render();
    try {
      await this._hass.callService(DOMAIN, service, {
        entity_id: this._entityId,
        ...serviceData,
      });
      this._dirty = false;
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _save() {
    if (!this._draft) {
      return;
    }
    await this._callService("write_schedule", this._savePayload());
  }

  _summaryRow(day) {
    const selected = day.day === this._draft?.selected_day;
    return `
      <button
        class="week-row ${selected ? "active" : ""}"
        data-day="${day.day}"
        ${this._busy ? "disabled" : ""}
      >
        <div class="week-day">${this._dayShort(day.day)}</div>
        <div class="week-value">${this._compactDaySummary(day)}</div>
      </button>
    `;
  }

  _periodCard(periodData, speedOptions) {
    const summary = periodData.summary ?? "Unavailable";
    const period = periodData.period;

    return `
      <section class="period-card">
        <div class="period-layout">
          <div class="period-side">
            <div class="period-track"></div>
            <div class="period-marker">${period}</div>
          </div>
          <div class="period-main">
            <div class="period-summary">${summary}</div>
            <div class="editor-row">
              <label class="field">
                <span class="field-label">Until</span>
                ${
                  periodData.editable_end
                    ? `
                      <ha-selector
                        class="time-input"
                        data-end-input="${period}"
                      ></ha-selector>
                    `
                    : `<div class="control static">24:00</div>`
                }
              </label>
              <label class="field">
                <span class="field-label">Speed</span>
                <ha-control-select-menu
                  class="speed-control"
                  data-speed-select="${period}"
                  hide-label
                  show-arrow
                ></ha-control-select-menu>
              </label>
            </div>
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
    const title = stateObj.attributes.friendly_name ?? "Schedule";
    const groupedWeekRows = this._groupedWeekRows(draft.days);
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          position: fixed;
          inset: 0;
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

        .scrim {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.56);
        }

        .dialog {
          position: absolute;
          top: max(12px, env(safe-area-inset-top));
          left: max(24px, env(safe-area-inset-left));
          right: max(24px, env(safe-area-inset-right));
          width: min(760px, calc(100vw - 48px));
          max-height: min(920px, calc(100dvh - 12px));
          margin: auto;
          display: grid;
          grid-template-rows: auto minmax(0, 1fr) auto;
          background: var(--card-background-color, var(--ha-card-background));
          color: var(--primary-text-color);
          border-radius: 28px;
          border: 1px solid var(--divider-color);
          box-shadow: var(--dialog-box-shadow, 0 18px 48px rgba(0, 0, 0, 0.35));
          overflow: visible;
        }

        .header {
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          gap: 14px;
          align-items: center;
          padding: 16px 20px 8px;
        }

        .title-block {
          min-width: 0;
        }

        .eyebrow,
        .field-label,
        .meta-label,
        .week-summary-title {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          line-height: 1.2;
        }

        .subhead {
          margin-top: 4px;
          color: var(--secondary-text-color);
          font-size: 15px;
        }

        .icon-button {
          width: 40px;
          height: 40px;
          border: none;
          border-radius: 20px;
          background: transparent;
          color: var(--primary-text-color);
          cursor: pointer;
          font-size: 28px;
          line-height: 1;
        }

        .content {
          overflow: visible;
          padding: 0 20px 10px;
        }

        .top-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--secondary-background-color);
          padding: 12px 14px;
          margin-bottom: 8px;
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

        .toggle {
          position: relative;
          width: 52px;
          height: 32px;
        }

        .toggle input {
          position: absolute;
          inset: 0;
          opacity: 0;
        }

        .slider {
          position: absolute;
          inset: 0;
          border-radius: 999px;
          background: var(--disabled-color);
        }

        .slider::before {
          content: "";
          position: absolute;
          top: 4px;
          left: 4px;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background: white;
          transition: transform 0.2s ease;
        }

        .toggle input:checked + .slider {
          background: var(--primary-color);
        }

        .toggle input:checked + .slider::before {
          transform: translateX(20px);
        }

        .copy-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          align-items: center;
          margin-top: 10px;
        }

        .copy-label {
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

        .week-summary {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--ha-card-background, var(--card-background-color));
          padding: 6px;
          margin-bottom: 6px;
        }

        .day-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 8px;
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
          gap: 2px;
        }

        .week-row {
          display: grid;
          grid-template-columns: 34px minmax(0, 1fr);
          gap: 10px;
          align-items: start;
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
        }

        .periods {
          display: grid;
          gap: 4px;
          overflow: visible;
        }

        .period-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 10px 12px;
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
          display: grid;
          justify-items: center;
          gap: 4px;
        }

        .period-summary {
          min-height: 18px;
          color: var(--secondary-text-color);
          font-size: 13px;
          line-height: 1.35;
        }

        .period-main {
          display: grid;
          gap: 8px;
          min-width: 0;
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

        .period-track {
          width: 2px;
          height: 42px;
          background: var(--divider-color);
          border-radius: 999px;
        }

        .editor-row {
          display: grid;
          grid-template-columns: 128px minmax(0, 1fr);
          gap: 10px;
          align-items: end;
        }

        .field {
          display: grid;
          gap: 4px;
        }

        .control.static {
          display: flex;
          align-items: center;
          min-height: 44px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 10px 12px;
        }

        .time-input {
          display: block;
          width: 100%;
        }

        .speed-control {
          display: block;
          width: 100%;
          --control-select-menu-height: 44px;
          --control-select-menu-border-radius: 10px;
          --control-select-menu-background-color: var(--primary-color);
          --control-select-menu-background-opacity: 0.18;
          --control-select-menu-focus-color: var(--primary-color);
        }

        .footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 10px 20px max(10px, env(safe-area-inset-bottom));
          border-top: 1px solid var(--divider-color);
          background: var(--card-background-color, var(--ha-card-background));
        }

        .footer-note {
          color: var(--secondary-text-color);
          font-size: 13px;
        }

        .actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }

        .action {
          min-width: 96px;
          height: 40px;
          border-radius: 10px;
          border: 1px solid var(--divider-color);
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 0 16px;
          cursor: pointer;
        }

        .action.primary {
          border-color: var(--primary-color);
          background: var(--primary-color);
          color: var(--text-primary-color, white);
        }

        @media (max-width: 800px) {
          .dialog {
            top: env(safe-area-inset-top);
            left: env(safe-area-inset-left);
            right: env(safe-area-inset-right);
            width: 100%;
            height: 100dvh;
            max-width: none;
            max-height: none;
            border-radius: 0;
            overflow: hidden;
          }

          .content {
            overflow: auto;
          }

          .header,
          .content,
          .footer {
            padding-left: 16px;
            padding-right: 16px;
          }

          .header {
            padding-top: max(16px, env(safe-area-inset-top));
          }

          .period-card {
            padding: 10px;
          }

          .editor-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }

          .footer {
            align-items: stretch;
            flex-direction: column;
          }

          .actions {
            width: 100%;
          }

          .action {
            flex: 1 1 auto;
          }
        }
      </style>
      <div class="scrim" id="scrim"></div>
      <div class="dialog" role="dialog" aria-modal="true" aria-label="${title}">
        <div class="header">
          <button class="icon-button" id="close" aria-label="Close">×</button>
          <div class="title-block">
            <div class="eyebrow">EcoVent</div>
            <h2>${title}</h2>
            <div class="subhead">${draft.selected_day}</div>
          </div>
        </div>
        <div class="content">
          <div class="top-card">
            <div class="toggle-row">
              <div>
                <div class="meta-label">Weekly schedule</div>
                <div class="meta-value">${draft.weekly_schedule_enabled ? "Enabled" : "Disabled"}</div>
              </div>
              <label class="toggle">
                <input
                  id="weekly-toggle"
                  type="checkbox"
                  ${draft.weekly_schedule_enabled ? "checked" : ""}
                  ${this._busy ? "disabled" : ""}
                />
                <span class="slider"></span>
              </label>
            </div>
            <div class="copy-row">
              <span class="copy-label">Copy ${this._copyTargetLabel(draft.selected_day)} to</span>
              <button class="group-chip" data-apply="weekdays" ${this._busy ? "disabled" : ""}>weekdays</button>
              <button class="group-chip" data-apply="weekend" ${this._busy ? "disabled" : ""}>weekend</button>
              <button class="group-chip" data-apply="all" ${this._busy ? "disabled" : ""}>all days</button>
            </div>
          </div>
          <div class="day-strip">
            ${draft.days.map((day) => this._dayChip(day.day)).join("")}
          </div>
          <div class="week-summary">
            <div class="week-summary-title">Week overview</div>
            <div class="week-summary-grid">
              ${groupedWeekRows.map((group) => this._weekGroupRow(group)).join("")}
            </div>
          </div>
          <div class="periods">
            ${periods
              .map((periodData) => this._periodCard(periodData, speedOptions))
              .join("")}
          </div>
        </div>
        <div class="footer">
          <div class="footer-note">
            ${this._dirty ? "Unsaved changes" : "Changes are saved"}
          </div>
          <div class="actions">
            <button class="action" id="reset" ${this._busy ? "disabled" : ""}>Reset</button>
            <button class="action primary" id="save" ${
              this._busy || !this._dirty ? "disabled" : ""
            }>Save</button>
          </div>
        </div>
      </div>
    `;

    this.shadowRoot
      .getElementById("scrim")
      ?.addEventListener("click", () => this.closeDialog());
    this.shadowRoot
      .getElementById("close")
      ?.addEventListener("click", () => this.closeDialog());
    this.shadowRoot.getElementById("reset")?.addEventListener("click", () => {
      this._draft = this._buildDraft();
      this._dirty = false;
      this._render();
    });
    this.shadowRoot.getElementById("save")?.addEventListener("click", () => this._save());

    this.shadowRoot
      .getElementById("weekly-toggle")
      ?.addEventListener("change", (event) => {
        this._setWeeklyEnabled(event.target.checked);
      });

    this.shadowRoot.querySelectorAll("[data-end-input]").forEach((element) => {
      const period = Number(element.dataset.endInput);
      const periodData = periods.find((item) => item.period === period);
      element.hass = {
        ...this._hass,
        locale: this._timeLocale(),
      };
      element.selector = {
        time: {
          no_second: true,
        },
      };
      element.value = this._normalizeTimeValue(periodData?.end);
      element.disabled = this._busy;
    });

    this.shadowRoot.querySelectorAll("[data-speed-select]").forEach((element) => {
      const period = Number(element.dataset.speedSelect);
      const periodData = periods.find((item) => item.period === period);
      element.options = speedOptions.map((option) => ({
        value: option.value,
        label: option.label,
        iconPath: this._speedOptionPath(option.value),
      }));
      element.value = periodData?.speed ?? speedOptions[0]?.value;
      element.disabled = this._busy;
    });

    this.shadowRoot.querySelectorAll("[data-day]").forEach((button) => {
      button.addEventListener("click", () => this._setSelectedDay(button.dataset.day));
    });

    this.shadowRoot.querySelectorAll("[data-apply]").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.apply === "weekdays") {
          this._applyCurrentDayTo([
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
          ]);
        } else if (button.dataset.apply === "weekend") {
          this._applyCurrentDayTo(["Saturday", "Sunday"]);
        } else if (button.dataset.apply === "all") {
          this._applyCurrentDayTo([
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
          ]);
        }
      });
    });

    this.shadowRoot.querySelectorAll("[data-end-input]").forEach((input) => {
      input.addEventListener("value-changed", (event) => {
        const value = event.detail.value;
        input.value = value;
        if (!value) {
          return;
        }
        const normalized = this._normalizeTimeValue(value);
        this._updatePeriod(Number(input.dataset.endInput), {
          end: normalized,
        });
      });
    });

    this.shadowRoot.querySelectorAll("[data-speed-select]").forEach((input) => {
      input.addEventListener("value-changed", (event) => {
        const value = event.detail.value;
        if (!value) {
          return;
        }
        input.value = value;
        this._updatePeriod(Number(input.dataset.speedSelect), {
          speed: value,
        });
      });
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
