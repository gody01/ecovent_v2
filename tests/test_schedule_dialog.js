/* Behavioral regression checks for the schedule dialog's terminal period. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.HTMLElement = class {};
global.customElements = { define() {} };
global.window = { addEventListener() {} };
global.document = {
  querySelector() {
    return null;
  },
  createElement() {
    return {};
  },
};

const source = fs
  .readFileSync(
    path.join(
      __dirname,
      "..",
      "custom_components",
      "ecovent_v2",
      "frontend",
      "ecovent-schedule-dialog.js"
    ),
    "utf8"
  )
  .replace(
    "class EcoventScheduleDialog extends HTMLElement",
    "globalThis.EcoventScheduleDialog = class EcoventScheduleDialog extends HTMLElement"
  );
eval(source);

function dayWithTerminalEnd(end) {
  return {
    day: "Monday",
    periods: [
      { period: 1, speed: "Low", editable_end: true, end: "06:00" },
      { period: 2, speed: "Low", editable_end: true, end: "09:00" },
      { period: 3, speed: "Low", editable_end: true, end: "19:00" },
      { period: 4, speed: "Low", editable_end: false, end },
    ],
  };
}

for (const end of ["00:00", "23:59"]) {
  const dialog = Object.create(EcoventScheduleDialog.prototype);
  const day = dayWithTerminalEnd(end);
  dialog._refreshDaySummaries(day);

  assert.equal(day.periods[3].summary, `19:00-${end} Low`);
  assert.deepEqual(dialog._periodBounds(day.periods[3]), {
    start: "19:00",
    end,
    speed: "Low",
  });

  dialog._draft = { selected_day: "Monday", weekly_schedule_enabled: true, days: [day] };
  dialog._savedDraft = JSON.parse(JSON.stringify(dialog._draft));
  assert.deepEqual(dialog._savePayload().days, []);

  dialog._updatePeriod = EcoventScheduleDialog.prototype._updatePeriod;
  dialog._currentScopeDays = () => ["Monday"];
  dialog._hasPersistedChanges = () => true;
  dialog._render = () => {};
  dialog._busy = false;
  dialog._updatePeriod(4, { speed: "High" });
  assert.equal(day.periods[3].summary, `19:00-${end} High`);
  assert.deepEqual(dialog._savePayload().days, [
    { day: "Monday", periods: [{ period: 4, speed: "High" }] },
  ]);
}
