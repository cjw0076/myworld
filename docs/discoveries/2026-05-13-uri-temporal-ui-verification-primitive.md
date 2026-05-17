# Uri Temporal UI Verification Primitive

- date: 2026-05-13 KST
- source repo: `/home/user/workspaces/jaewon/myworld/uri`
- sprint: URI-041 Season Reward cross-surface banner

## Observation

Visual verification of calendar-sensitive UI needs a first-class time-travel
primitive. Directly monkeypatching `Date` in Playwright caused a Next hydration
overlay because the server rendered the real current date while the client
rendered the mocked date.

## Local Patch

Uri added `uri.debug.today` through `src/lib/use-uri-today.ts`. Tests can set
that localStorage key before navigation; the page hydrates normally and then
updates the temporal UI after mount.

## AIOS Improvement Candidate

CapabilityOS should expose a standard temporal browser verification capability:

- set local deterministic app time
- avoid hydration mismatch
- record the mocked time in the receipt
- clear the override after the run

This should become a reusable AIOS primitive for any repo with D-day, calendar,
seasonal, trial, payment, or scheduling UI.
