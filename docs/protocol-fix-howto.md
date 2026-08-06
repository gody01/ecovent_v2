# Protocol Fix How-To

Use this guide when fixing EcoVent reports about incomplete protocol responses,
unsupported registers, generated entities stuck as unavailable/unknown, noisy
writes, or hardware/profile mismatch Repairs.

## Triage

- Start from the issue log and the reporter's exact hardware tuple: brand,
  marketing name, unit type, firmware string, profile, host path, and the
  requested/received/missing/unsupported register sets.
- Check the last related PRs before editing. Regressions often sit around
  `protocol_profiles.py`, `fan_protocol.py`, `fan_capabilities.py`,
  `protocol_diagnostics.py`, `coordinator.py`, and the entity registry helpers.
- Separate liveness proof from nice-to-have data. A reachable fan should not go
  unavailable just because optional sensors, schedule rows, filter timers, or
  Pro-only feature rows are absent.
- Keep direct targeted reads strict. Optional-row tolerance is for automatic
  poll availability, not for pretending an explicit requested value exists.
- When a row is missing or returns `0xFD`, record whether it is required,
  optional-unavailable, unsupported, retried, backed off, or skipped. Tests
  should assert these sets, not just the final boolean.
- After fixing availability for unsupported optional rows, check the second
  user-facing surface: Repairs/diagnostics. Known firmware variants should not
  keep suggesting a new hardware/profile mismatch report for rows that are now
  documented as benign, while unknown extra unsupported rows should still keep
  the prefilled report path.

## Protocol And Documentation

- Treat manufacturer PDFs as parameter-map evidence, not as complete firmware
  contracts. Real devices in the Vento/TwinFresh, Breezy/Freshpoint, and
  Freshbox/Micra families can omit or reject documented rows.
- Before calling a PDF wrong, first check whether the issue is a variant split:
  standard vs Pro sensor packages, firmware `0.4` behavior, A21 Modbus vs BGCP,
  Vento-family rows shared across brands, or a row documented for one profile
  but observed working on another.
- Update `protocol.md` whenever a fix depends on this distinction. Capture the
  PDF expectation, observed device behavior, and integration policy in the
  "Spec and observed firmware differences" table.
- Do not add a runtime map solely from a catalogue or relabel relationship.
  Runtime mappings need either source documentation for that protocol or a
  reporter/live-device observation.

## Home Assistant Behavior

- Startup, reload, and discovery should be read-only unless a user explicitly
  calls a service or the code is batching into a write that would already happen.
- Avoid surprise beeps. For RTC sync, silent/manual speed, presets, and airflow
  mode changes, reread state first and skip unchanged or unsafe writes.
- Preserve entity registry identity. Migrations should keep customized entity
  IDs and names, migrate known legacy unique IDs, and hide unsupported generated
  entities instead of deleting them.
- Hiding unsupported entities is not the same as suppressing a Repair. When a
  hardware report becomes a known variant, update `protocol_diagnostics.py` and
  `coordinator.py` so the Repair is based only on still-reportable rows, and add
  tests for both the no-Repair known set and a different unsupported row that
  still asks for maintainer data.
- Frontend assets must not block Home Assistant startup. File hashing or reads
  that can touch disk during setup belong in executor work, and route changes
  need a browser or HTTP smoke when practical.

## PR Checklist

- If the PR is meant to resolve bug reports, add explicit closing references
  before publishing. Put each one on its own line as `Closes #NN` or
  `Closes owner/repo#NN`, and do not wrap the reference in backticks. After
  creating or editing the PR, read back GitHub's `closingIssuesReferences`;
  issue text that merely says "Fixes ..." or `Refs ...` is not done until GitHub
  shows the report under the PR's closing references.
- Before opening another PR for a new report, search the current open PRs for
  the same issue numbers, protocol family, and touched files. If an open PR
  already carries the same fix surface, update that PR or explicitly mark the
  older one as superseded; do not leave two mergeable PRs for the same
  availability or Repair behavior.
- When a mismatch Repair asks for hardware reports, make it clear whether the
  report is per config entry or per distinct model/firmware/register set. In a
  mixed installation, identical devices with identical firmware and rejected
  rows can share one issue, but different tuples should not be merged into one
  ambiguous hardware report.
- Keep version markers aligned in the same commit: `manifest.json`,
  `custom_components/ecovent_v2/ecoventv2.py`, and the README changelog section.
- Prefer focused PRs. If one PR carries closure for already-merged follow-ups,
  say that plainly in the PR body and keep the code delta limited to the missing
  regression/docs/release bookkeeping.
- Public PR text should distinguish validation that actually ran from validation
  that still needs reporter hardware. Never claim a live smoke test from a fake
  protocol test.
- Standard validation for Python-only fixes:
  `PYTHONPATH=tests pytest -q`, targeted regression tests, `ruff check
  custom_components/ecovent_v2 tests`, `python3 -m compileall -q
  custom_components/ecovent_v2 tests`, JSON parse checks for changed metadata or
  translations, and `git diff --check`.
