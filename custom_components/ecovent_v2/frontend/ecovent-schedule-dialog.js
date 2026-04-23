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

  _savePayload() {
    return {
      selected_day: this._draft?.selected_day,
      weekly_schedule_enabled: this._draft?.weekly_schedule_enabled,
      days: this._draft?.days,
    };
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

  _periodCard(periodData, speedOptions) {
    const summary = periodData.summary ?? "Unavailable";
    const endValue = periodData.end ?? "";
    const period = periodData.period;

    return `
      <section class="period-card">
        <div class="period-heading">
          <div>
            <div class="period-title">Period ${period}</div>
            <div class="period-summary">${summary}</div>
          </div>
          <div class="period-badge">${period}</div>
        </div>
        <div class="field-row">
          <label class="field">
            <span class="field-label">Until</span>
            ${
              periodData.editable_end
                ? `
                  <input
                    class="control"
                    type="time"
                    data-end-period="${period}"
                    value="${endValue}"
                    ${this._busy ? "disabled" : ""}
                  />
                `
                : `<div class="control static">24:00</div>`
            }
          </label>
          <label class="field">
            <span class="field-label">Speed</span>
            <select
              class="control"
              data-speed-period="${period}"
              ${this._busy ? "disabled" : ""}
            >
              ${speedOptions
                .map(
                  (option) => `
                    <option value="${option}" ${
                      option === periodData.speed ? "selected" : ""
                    }>${option}</option>
                  `
                )
                .join("")}
            </select>
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

    const dayOptions = Array.isArray(attrs.day_options) ? attrs.day_options : [];
    const speedOptions = Array.isArray(attrs.speed_options) ? attrs.speed_options : [];
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
          inset: max(24px, env(safe-area-inset-top))
            max(24px, env(safe-area-inset-right))
            max(24px, env(safe-area-inset-bottom))
            max(24px, env(safe-area-inset-left));
          max-width: 920px;
          max-height: calc(100dvh - 48px);
          margin: auto;
          display: grid;
          grid-template-rows: auto auto auto 1fr auto;
          background: var(--card-background-color, var(--ha-card-background));
          color: var(--primary-text-color);
          border-radius: 24px;
          border: 1px solid var(--divider-color);
          box-shadow: var(--dialog-box-shadow, 0 18px 48px rgba(0, 0, 0, 0.35));
          overflow: hidden;
        }

        .header {
          display: flex;
          align-items: start;
          justify-content: space-between;
          gap: 16px;
          padding: 20px 20px 12px;
        }

        .title-block {
          min-width: 0;
        }

        .eyebrow,
        .field-label,
        .meta-label {
          color: var(--secondary-text-color);
          font-size: 12px;
        }

        h2 {
          margin: 4px 0 0;
          font-size: 24px;
          line-height: 1.2;
        }

        .subhead {
          margin-top: 6px;
          color: var(--secondary-text-color);
        }

        .icon-button {
          width: 40px;
          height: 40px;
          border: 1px solid var(--divider-color);
          border-radius: 20px;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          cursor: pointer;
        }

        .meta {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
          padding: 0 20px 16px;
        }

        .meta-card {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 14px 16px;
          background: var(--secondary-background-color);
        }

        .meta-value {
          margin-top: 4px;
          font-size: 18px;
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

        .days {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          padding: 0 20px 16px;
        }

        .day {
          min-width: 56px;
          height: 40px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: var(--ha-card-background, var(--card-background-color));
          color: var(--primary-text-color);
          padding: 0 14px;
          cursor: pointer;
        }

        .day.active {
          border-color: var(--primary-color);
          background: color-mix(in srgb, var(--primary-color) 18%, transparent);
          color: var(--primary-text-color);
        }

        .content {
          overflow: auto;
          padding: 0 20px 20px;
        }

        .periods {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
        }

        .period-card {
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          padding: 16px;
          background: var(--ha-card-background, var(--card-background-color));
        }

        .period-heading {
          display: flex;
          justify-content: space-between;
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

        .period-badge {
          display: grid;
          place-items: center;
          min-width: 28px;
          height: 28px;
          border-radius: 14px;
          background: var(--secondary-background-color);
          color: var(--secondary-text-color);
          padding: 0 8px;
        }

        .field-row {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 12px;
          margin-top: 14px;
        }

        .field {
          display: grid;
          gap: 8px;
        }

        .control {
          width: 100%;
          min-height: 44px;
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
            inset: env(safe-area-inset-top) env(safe-area-inset-right)
              env(safe-area-inset-bottom) env(safe-area-inset-left);
            width: 100%;
            height: 100dvh;
            max-width: none;
            max-height: none;
            border-radius: 0;
            grid-template-rows: auto auto auto 1fr auto;
          }

          .header,
          .meta,
          .days,
          .content,
          .footer {
            padding-left: 16px;
            padding-right: 16px;
          }

          .header {
            padding-top: max(16px, env(safe-area-inset-top));
          }

          .meta,
          .periods,
          .field-row {
            grid-template-columns: 1fr;
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
          <div class="title-block">
            <div class="eyebrow">EcoVent</div>
            <h2>${title}</h2>
            <div class="subhead">Weekly schedule</div>
          </div>
          <button class="icon-button" id="close" aria-label="Close">×</button>
        </div>
        <div class="meta">
          <div class="meta-card">
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
          <div class="meta-card">
            <div>
              <div class="meta-label">Selected day</div>
              <div class="meta-value">${draft.selected_day}</div>
            </div>
          </div>
        </div>
        <div class="days">
          ${dayOptions
            .map(
              (day) => `
                <button
                  class="day ${day === draft.selected_day ? "active" : ""}"
                  data-day="${day}"
                  ${this._busy ? "disabled" : ""}
                >
                  ${day.slice(0, 3)}
                </button>
              `
            )
            .join("")}
        </div>
        <div class="content">
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

    this.shadowRoot.getElementById("scrim")?.addEventListener("click", () => this.closeDialog());
    this.shadowRoot.getElementById("close")?.addEventListener("click", () => this.closeDialog());
    this.shadowRoot.getElementById("reset")?.addEventListener("click", () => {
      this._draft = this._buildDraft();
      this._dirty = false;
      this._render();
    });
    this.shadowRoot.getElementById("save")?.addEventListener("click", () => this._save());

    this.shadowRoot.getElementById("weekly-toggle")?.addEventListener("change", (event) => {
      this._setWeeklyEnabled(event.target.checked);
    });

    this.shadowRoot.querySelectorAll("[data-day]").forEach((button) => {
      button.addEventListener("click", () => this._setSelectedDay(button.dataset.day));
    });

    this.shadowRoot.querySelectorAll("[data-speed-period]").forEach((select) => {
      select.addEventListener("change", () => {
        this._updatePeriod(Number(select.dataset.speedPeriod), {
          speed: select.value,
        });
      });
    });

    this.shadowRoot.querySelectorAll("[data-end-period]").forEach((input) => {
      input.addEventListener("change", () => {
        this._updatePeriod(Number(input.dataset.endPeriod), {
          end: input.value,
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
