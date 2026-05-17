# Uri Visual Fixture Contract Gap

- date: 2026-05-13 KST
- source repo: `myworld/uri`
- observed by: codex@uri
- related sprint: URI-055

## Observation

During production Playwright verification for Uri Sprint 052, Codex initially
seeded `/memory` with an obsolete localStorage key. The screenshot rendered a
valid page, but it showed the default `ulsan` memory state instead of the
intended `hanyang` fixture. The issue was caught by visual inspection and fixed
by using the current `uri.personal-agent-loop.v1` key and complete local state
shape.

## AIOS Improvement

AIOS visual verification should not require each executor to hand-write storage
fixtures. Provide a reusable fixture primitive that imports or mirrors app
state constants and emits valid app-state objects for Playwright.

## Suggested Contract

- `createUriVisualState({ schoolSlug, departmentId, traces, intents })`
- validates required `Trace`, `ExperienceIntent`, and `UserProfile` fields
- writes using the canonical `URI_STATE_KEY`
- returns a receipt with selected school, trace count, memory count, and storage
  key

## Why It Matters

Uri is becoming an app/platform with many local loops. A screenshot can look
healthy while proving the wrong school or wrong state. The fixture contract
should make that class of false positive harder to create.
