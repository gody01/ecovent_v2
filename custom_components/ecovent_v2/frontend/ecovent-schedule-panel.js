class EcoventSchedulePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._selectedDevice = "";
    this._busy = false;
  }

  set hass(hass) {
    this._hass = hass;
    const devices = this._getDevices();
    if (!devices.length) {
      this._selectedDevice = "";
      this._render();
      return;
    }

    if (!devices.some((device) => device.base === this._selectedDevice)) {
      this._selectedDevice = devices[0].base;
    }

    this._render();
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._render();
  }

  set panel(panel) {
    this._panel = panel;
    this._render();
  }

  _getDevices() {
    if (!this._hass) {
      return [];
    }

    return Object.keys(this._hass.states)
      .filter(
        (entityId) =>
          entityId.startsWith("select.") && entityId.endsWith("_schedule_day")
      )
      .map((entityId) => {
        const base = entityId.slice("select.".length, -"_schedule_day".length);
        const fanEntityId = `fan.${base}`;
        const dayState = this._hass.states[entityId];
        const fanState = this._hass.states[fanEntityId];
        const name =
          fanState?.attributes?.friendly_name ??
          dayState?.attributes?.friendly_name?.replace(/ Schedule day$/, "") ??
          base.replaceAll("_", " ");

        const summary = {};
        for (let index = 1; index <= 4; index += 1) {
          summary[index] = dayState?.attributes?.[`period_${index}`] ?? "Unavailable";
        }

        return {
          base,
          name,
          fanEntityId,
          weeklyScheduleEntityId: `switch.${base}_weekly_schedule`,
          dayEntityId: entityId,
          periodSpeedEntityIds: {
            1: `select.${base}_schedule_period_1_speed`,
            2: `select.${base}_schedule_period_2_speed`,
            3: `select.${base}_schedule_period_3_speed`,
            4: `select.${base}_schedule_period_4_speed`,
          },
          periodEndEntityIds: {
            1: `time.${base}_schedule_period_1_end`,
            2: `time.${base}_schedule_period_2_end`,
            3: `time.${base}_schedule_period_3_end`,
          },
          summary,
        };
      })
      .sort((left, right) => left.name.localeCompare(right.name));
  }

  _getActiveDevice() {
    return this._getDevices().find((device) => device.base === this._selectedDevice);
  }

  _entity(entityId) {
    return this._hass?.states?.[entityId];
  }

  async _callService(domain, service, serviceData) {
    if (!this._hass || this._busy) {
      return;
    }

    this._busy = true;
    this._render();
    try {
      await this._hass.callService(domain, service, serviceData);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _setDay(option) {
    const device = this._getActiveDevice();
    if (!device) {
      return;
    }

    await this._callService("select", "select_option", {
      entity_id: device.dayEntityId,
      option,
    });
  }

  async _setWeeklySchedule(enabled) {
    const device = this._getActiveDevice();
    if (!device) {
      return;
    }

    await this._callService("switch", enabled ? "turn_on" : "turn_off", {
      entity_id: device.weeklyScheduleEntityId,
    });
  }

  async _setSpeed(period, option) {
    const device = this._getActiveDevice();
    if (!device) {
      return;
    }

    await this._callService("select", "select_option", {
      entity_id: device.periodSpeedEntityIds[period],
      option,
    });
  }

  async _setTime(period, value) {
    const device = this._getActiveDevice();
    if (!device) {
      return;
    }

    await this._callService("time", "set_value", {
      entity_id: device.periodEndEntityIds[period],
      time: `${value}:00`,
    });
  }

  _formatTime(entityId) {
    const state = this._entity(entityId)?.state;
    if (!state || state === "unknown" || state === "unavailable") {
      return "";
    }

    return state.slice(0, 5);
  }

  _periodEditor(device, period) {
    const speedEntity = this._entity(device.periodSpeedEntityIds[period]);
    const endEntityId = device.periodEndEntityIds[period];
    const endEntity = endEntityId ? this._entity(endEntityId) : null;
    const speedValue = speedEntity?.state ?? "";
    const options = speedEntity?.attributes?.options ?? [];
    const summary = device.summary[period];
    const endValue = endEntity ? this._formatTime(endEntity.entity_id) : "00:00";
    const disabled = !speedEntity || speedEntity.state === "unavailable";

    return `
      <section class="period-card">
        <div class="period-top">
          <div>
            <div class="period-title">Period ${period}</div>
            <div class="period-summary">${summary}</div>
          </div>
          <div class="period-number">${period}</div>
        </div>
        <div class="editor-grid">
          ${
            endEntity
              ? `
                <label class="field">
                  <span class="label">Until</span>
                  <input
                    class="time-input"
                    type="time"
                    value="${endValue}"
                    data-period-time="${period}"
                    ${this._busy ? "disabled" : ""}
                  />
                </label>
              `
              : `
                <div class="field static-field">
                  <span class="label">Until</span>
                  <div class="static-value">00:00</div>
                </div>
              `
          }
          <label class="field">
            <span class="label">Speed</span>
            <select
              class="select-input"
              data-period-speed="${period}"
              ${disabled || this._busy ? "disabled" : ""}
            >
              ${options
                .map(
                  (option) => `
                    <option value="${option}" ${
                      option === speedValue ? "selected" : ""
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

    const devices = this._getDevices();
    const device = this._getActiveDevice();

    if (!devices.length) {
      this.shadowRoot.innerHTML = `
        <style>${this._styles()}</style>
        <div class="page">
          <div class="empty">
            <h2>No schedule-capable EcoVent devices found</h2>
            <p>This panel appears when an EcoVent device exposes a weekly schedule editor.</p>
          </div>
        </div>
      `;
      return;
    }

    const dayEntity = device ? this._entity(device.dayEntityId) : null;
    const weeklyScheduleEntity = device
      ? this._entity(device.weeklyScheduleEntityId)
      : null;
    const dayOptions = dayEntity?.attributes?.options ?? [];
    const selectedDay = dayEntity?.state ?? "";
    const weeklyEnabled = weeklyScheduleEntity?.state === "on";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <div class="page">
        <div class="shell">
          <header class="hero">
            <div>
              <div class="eyebrow">EcoVent</div>
              <h1>Weekly schedule</h1>
              <p>Use the real schedule editor instead of the raw entity stack.</p>
            </div>
            <label class="device-picker">
              <span class="label">Device</span>
              <select id="device-select" class="select-input" ${this._busy ? "disabled" : ""}>
                ${devices
                  .map(
                    (item) => `
                      <option value="${item.base}" ${
                        item.base === this._selectedDevice ? "selected" : ""
                      }>${item.name}</option>
                    `
                  )
                  .join("")}
              </select>
            </label>
          </header>

          <section class="top-grid">
            <div class="status-card">
              <div class="status-meta">
                <span class="status-label">Weekly schedule</span>
                <label class="switch">
                  <input type="checkbox" id="weekly-toggle" ${
                    weeklyEnabled ? "checked" : ""
                  } ${this._busy ? "disabled" : ""}>
                  <span class="slider"></span>
                </label>
              </div>
              <div class="status-text">${
                weeklyEnabled ? "Enabled" : "Disabled"
              }</div>
            </div>
            <div class="status-card">
              <div class="status-label">Fan mode</div>
              <div class="status-text">${
                this._entity(device.fanEntityId)?.attributes?.preset_mode ?? "Unknown"
              }</div>
            </div>
          </section>

          <section class="day-strip">
            ${dayOptions
              .map(
                (option) => `
                  <button
                    class="day-pill ${option === selectedDay ? "active" : ""}"
                    data-day="${option}"
                    ${this._busy ? "disabled" : ""}
                  >
                    ${option.slice(0, 3)}
                  </button>
                `
              )
              .join("")}
          </section>

          <section class="summary-grid">
            ${[1, 2, 3, 4]
              .map(
                (period) => `
                  <div class="summary-card">
                    <div class="summary-title">Period ${period}</div>
                    <div class="summary-body">${device.summary[period]}</div>
                  </div>
                `
              )
              .join("")}
          </section>

          <section class="period-grid">
            ${[1, 2, 3, 4].map((period) => this._periodEditor(device, period)).join("")}
          </section>
        </div>
      </div>
    `;

    this.shadowRoot.getElementById("device-select")?.addEventListener("change", (event) => {
      this._selectedDevice = event.target.value;
      this._render();
    });

    this.shadowRoot.getElementById("weekly-toggle")?.addEventListener("change", (event) => {
      this._setWeeklySchedule(event.target.checked);
    });

    this.shadowRoot.querySelectorAll("[data-day]").forEach((button) => {
      button.addEventListener("click", () => this._setDay(button.dataset.day));
    });

    this.shadowRoot.querySelectorAll("[data-period-speed]").forEach((select) => {
      select.addEventListener("change", () =>
        this._setSpeed(Number(select.dataset.periodSpeed), select.value)
      );
    });

    this.shadowRoot.querySelectorAll("[data-period-time]").forEach((input) => {
      input.addEventListener("change", () =>
        this._setTime(Number(input.dataset.periodTime), input.value)
      );
    });
  }

  _styles() {
    return `
      :host {
        display: block;
        min-height: 100%;
        color: var(--primary-text-color);
        background:
          radial-gradient(circle at top left, rgba(72, 164, 255, 0.18), transparent 28%),
          radial-gradient(circle at top right, rgba(60, 205, 142, 0.14), transparent 24%),
          var(--primary-background-color);
      }

      * {
        box-sizing: border-box;
        font: inherit;
      }

      .page {
        padding: 24px;
      }

      .shell {
        max-width: 1160px;
        margin: 0 auto;
        display: grid;
        gap: 18px;
      }

      .hero,
      .status-card,
      .summary-card,
      .period-card {
        border: 1px solid var(--divider-color);
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: 8px;
        box-shadow: var(--ha-card-box-shadow, none);
      }

      .hero {
        padding: 24px;
        display: grid;
        gap: 16px;
        grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
        align-items: end;
      }

      .eyebrow {
        color: var(--secondary-text-color);
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 0.04em;
        margin-bottom: 6px;
      }

      h1 {
        margin: 0;
        font-size: 32px;
        line-height: 1.1;
      }

      p {
        margin: 8px 0 0;
        color: var(--secondary-text-color);
      }

      .top-grid,
      .summary-grid,
      .period-grid {
        display: grid;
        gap: 16px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .summary-grid,
      .period-grid {
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      }

      .status-card,
      .summary-card,
      .period-card {
        padding: 18px;
      }

      .status-meta,
      .period-top {
        display: flex;
        justify-content: space-between;
        align-items: start;
        gap: 12px;
      }

      .status-label,
      .label,
      .summary-title {
        font-size: 12px;
        text-transform: uppercase;
        color: var(--secondary-text-color);
        letter-spacing: 0.04em;
      }

      .status-text {
        margin-top: 8px;
        font-size: 24px;
      }

      .day-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
      }

      .day-pill {
        border: 1px solid var(--divider-color);
        background: var(--ha-card-background, var(--card-background-color));
        color: var(--primary-text-color);
        border-radius: 999px;
        padding: 10px 16px;
        min-width: 64px;
        cursor: pointer;
      }

      .day-pill.active {
        background: var(--rgb-primary-color, var(--primary-color));
        color: white;
        border-color: transparent;
      }

      .summary-body,
      .period-summary,
      .static-value {
        margin-top: 6px;
        font-size: 15px;
        line-height: 1.4;
      }

      .period-title {
        font-size: 20px;
      }

      .period-number {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        color: white;
        background: var(--primary-color);
        font-size: 16px;
      }

      .editor-grid {
        margin-top: 18px;
        display: grid;
        gap: 14px;
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .field {
        display: grid;
        gap: 8px;
      }

      .select-input,
      .time-input,
      .static-value {
        width: 100%;
        min-height: 44px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--secondary-background-color);
        color: var(--primary-text-color);
        padding: 10px 12px;
      }

      .static-field {
        align-content: end;
      }

      .device-picker {
        display: grid;
        gap: 8px;
      }

      .switch {
        position: relative;
        display: inline-flex;
        width: 52px;
        height: 30px;
      }

      .switch input {
        opacity: 0;
        width: 0;
        height: 0;
      }

      .slider {
        position: absolute;
        inset: 0;
        border-radius: 999px;
        background: var(--disabled-color);
        transition: background 0.2s ease;
      }

      .slider::before {
        content: "";
        position: absolute;
        width: 22px;
        height: 22px;
        left: 4px;
        top: 4px;
        border-radius: 50%;
        background: white;
        transition: transform 0.2s ease;
      }

      .switch input:checked + .slider {
        background: var(--primary-color);
      }

      .switch input:checked + .slider::before {
        transform: translateX(22px);
      }

      .empty {
        max-width: 720px;
        margin: 48px auto;
        padding: 32px;
        border-radius: 8px;
        border: 1px solid var(--divider-color);
        background: var(--ha-card-background, var(--card-background-color));
      }

      @media (max-width: 900px) {
        .page {
          padding: 16px;
        }

        .hero,
        .top-grid,
        .editor-grid {
          grid-template-columns: 1fr;
        }
      }
    `;
  }
}

customElements.define("ecovent-schedule-panel", EcoventSchedulePanel);
