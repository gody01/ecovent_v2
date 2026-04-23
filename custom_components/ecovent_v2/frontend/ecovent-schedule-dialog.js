const DOMAIN = "ecovent_v2";

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

  _hourOptions() {
    return Array.from({ length: 24 }, (_, hour) => `${hour}`.padStart(2, "0"));
  }

  _minuteOptions() {
    return Array.from({ length: 60 }, (_, minute) => `${minute}`.padStart(2, "0"));
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

  _compactDaySummary(day) {
    return (day.periods || [])
      .map((period) => this._compactPeriodSummary(period.summary))
      .join("  •  ");
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
    const endValue = periodData.end ?? "";
    const period = periodData.period;
    const [hourValue, minuteValue] = endValue ? endValue.split(":") : ["00", "00"];
    const hourOptions = this._hourOptions();
    const minuteOptions = this._minuteOptions();

    return `
      <section class="period-card">
        <div class="period-heading">
          <div class="period-track"></div>
          <div class="period-marker">${period}</div>
          <div>
            <div class="period-title">Period ${period}</div>
            <div class="period-summary">${summary}</div>
          </div>
        </div>
        <div class="editor-row">
          <label class="field">
            <span class="field-label">Until</span>
            ${
              periodData.editable_end
                ? `
                  <div class="time-control">
                    <div class="select-wrap">
                      <select
                        class="control time-part"
                        data-end-hour="${period}"
                        ${this._busy ? "disabled" : ""}
                      >
                        ${hourOptions
                          .map(
                            (option) => `
                              <option value="${option}" ${
                                option === hourValue ? "selected" : ""
                              }>${option}</option>
                            `
                          )
                          .join("")}
                      </select>
                      <ha-icon icon="mdi:chevron-down" class="select-arrow"></ha-icon>
                    </div>
                    <span class="time-separator">:</span>
                    <div class="select-wrap">
                      <select
                        class="control time-part"
                        data-end-minute="${period}"
                        ${this._busy ? "disabled" : ""}
                      >
                        ${minuteOptions
                          .map(
                            (option) => `
                              <option value="${option}" ${
                                option === minuteValue ? "selected" : ""
                              }>${option}</option>
                            `
                          )
                          .join("")}
                      </select>
                      <ha-icon icon="mdi:chevron-down" class="select-arrow"></ha-icon>
                    </div>
                  </div>
                `
                : `<div class="control static">24:00</div>`
            }
          </label>
          <label class="field">
            <span class="field-label">Speed</span>
            <div class="select-wrap">
              <select
                class="control"
                data-speed-select="${period}"
                ${this._busy ? "disabled" : ""}
              >
                ${speedOptions
                  .map(
                    (option) => `
                      <option value="${option.value}" ${
                        option.value === periodData.speed ? "selected" : ""
                      }>${option.label}</option>
                    `
                  )
                  .join("")}
              </select>
              <ha-icon icon="mdi:chevron-down" class="select-arrow"></ha-icon>
            </div>
          </label>
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
          top: max(24px, env(safe-area-inset-top));
          left: max(24px, env(safe-area-inset-left));
          right: max(24px, env(safe-area-inset-right));
          width: min(760px, calc(100vw - 48px));
          max-height: min(920px, calc(100dvh - 48px));
          margin: auto;
          display: grid;
          grid-template-rows: auto minmax(0, 1fr) auto;
          background: var(--card-background-color, var(--ha-card-background));
          color: var(--primary-text-color);
          border-radius: 28px;
          border: 1px solid var(--divider-color);
          box-shadow: var(--dialog-box-shadow, 0 18px 48px rgba(0, 0, 0, 0.35));
          overflow: hidden;
        }

        .header {
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          gap: 14px;
          align-items: center;
          padding: 18px 20px 10px;
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
          overflow: auto;
          padding: 0 20px 18px;
        }

        .top-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--secondary-background-color);
          padding: 14px 16px;
          margin-bottom: 14px;
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
          margin-top: 12px;
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
          padding: 8px;
          margin-bottom: 14px;
        }

        .week-summary-title {
          margin: 2px 4px 8px;
        }

        .week-summary-grid {
          display: grid;
          gap: 4px;
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
          padding: 8px;
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
          gap: 10px;
        }

        .period-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 16px;
          background: var(--ha-card-background, var(--card-background-color));
        }

        .period-heading {
          display: grid;
          grid-template-columns: 28px 28px minmax(0, 1fr);
          gap: 12px;
          align-items: start;
        }

        .period-title {
          font-size: 18px;
        }

        .period-summary {
          margin-top: 6px;
          color: var(--secondary-text-color);
          line-height: 1.35;
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
          height: 100%;
          justify-self: center;
          background: var(--divider-color);
          border-radius: 999px;
        }

        .editor-row {
          display: grid;
          grid-template-columns: minmax(0, 1.1fr) minmax(220px, 0.9fr);
          gap: 12px;
          margin-top: 14px;
          margin-left: 40px;
        }

        .field {
          display: grid;
          gap: 8px;
        }

        .time-control {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
          gap: 6px;
          align-items: center;
        }

        .time-part {
          text-align: center;
        }

        .time-separator {
          color: var(--secondary-text-color);
          font-weight: 600;
        }

        .control {
          width: 100%;
          min-height: 44px;
          appearance: none;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          padding: 10px 12px;
        }

        .control.static {
          display: flex;
          align-items: center;
        }

        .select-wrap {
          position: relative;
        }

        .select-arrow {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--secondary-text-color);
          pointer-events: none;
          --mdc-icon-size: 18px;
        }

        .footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 16px 20px max(16px, env(safe-area-inset-bottom));
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
            padding: 14px;
          }

          .editor-row {
            grid-template-columns: 1fr;
            margin-left: 40px;
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
          <div class="week-summary">
            <div class="week-summary-title">Week overview</div>
            <div class="week-summary-grid">
              ${draft.days.map((day) => this._summaryRow(day)).join("")}
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

    const syncPeriodTime = (period) => {
      const hour = this.shadowRoot.querySelector(`[data-end-hour="${period}"]`)?.value;
      const minute = this.shadowRoot.querySelector(`[data-end-minute="${period}"]`)?.value;
      if (hour == null || minute == null) {
        return;
      }
      this._updatePeriod(Number(period), {
        end: `${hour}:${minute}`,
      });
    };

    this.shadowRoot.querySelectorAll("[data-end-hour]").forEach((input) => {
      input.addEventListener("change", () => syncPeriodTime(input.dataset.endHour));
    });

    this.shadowRoot.querySelectorAll("[data-end-minute]").forEach((input) => {
      input.addEventListener("change", () => syncPeriodTime(input.dataset.endMinute));
    });

    this.shadowRoot.querySelectorAll("[data-speed-select]").forEach((input) => {
      input.addEventListener("change", () => {
        this._updatePeriod(Number(input.dataset.speedSelect), {
          speed: input.value,
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
