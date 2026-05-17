# Discovery — Uri Sprint Loop Receipt + Dev Server Lifecycle Gaps

- date: 2026-05-13 KST
- source repo: `uri`
- reporter: codex@uri as AIOS Executor
- status: improvement candidate

## Observation

During Uri `URI-036` Sprint 021 execution, two AIOS sprint-loop ticks were
marked complete inside the same second. The file-backed runner wrote both JSON
receipts to the same path:

`myworld/.aios/sprint_runs/uri/20260513T155951.json`

The sprint file still records both task completions, but the first JSON receipt
payload was overwritten by the second.

The same sprint also exposed a dev-server lifecycle gap: an old `next dev`
process from the same Uri repo was still listening on port 3000 and produced
broken HMR behavior during browser verification. A fresh server was required
for reliable visual checks.

## Why It Matters

AIOS is supposed to coordinate Codex/Claude/Hive execution through durable
evidence. Second-level receipt ids and unmanaged dev servers make verification
less deterministic than the product work itself.

## Proposed Fix

- give sprint-loop receipts monotonic ids: timestamp plus task index, pid, or
  random suffix
- add a server lifecycle primitive that can list, reuse, or intentionally stop
  repo-owned dev servers before browser verification
- surface stale server/HMR warnings in the operator-facing AIOS status output

## Evidence

- Uri sprint file: `uri/.aios/sprints/URI-036-sprint-021-pilot-p0-profile-setup.md`
- final screenshots: `uri/.aios/screenshots/sprint-021/`
- fresh verification passed after restarting `next dev` and disabling Next dev
  indicator via `next.config.ts`
