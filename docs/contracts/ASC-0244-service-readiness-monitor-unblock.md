---
contract_id: ASC-0244
slug: service-readiness-monitor-unblock
status: accepted
goal: Unblock AIOS service-readiness control loop by resolving monitor false blockers caused by fossil-quarantined contract paths, without weakening auditability.
created: 2026-06-13T05:24:00+09:00
accepted: 2026-06-13T05:24:00+09:00
closed:
human_approved: true
origin: operator directed Codex not to implement directly; Codex should prepare service readiness and delegate missing development to Claude.
---

# ASC-0244 Service Readiness Monitor Unblock

## Why Now

AIOS is alive, but the round controller is currently `control_only` and
`hold_for_monitor`. The latest monitor assessment reports many
`dispatch_contract_path_missing` blockers because older dispatch records still
point at `docs/contracts/ASC-0001...ASC-0049...` paths that were moved into
`docs/_history/contracts/` by the fossil quarantine.

That is a service-readiness blocker: product operation cannot depend on a
monitor that treats intentionally preserved historical moves as unresolved
missing artifacts.

This contract delegates the implementation to Claude. Codex must not patch the
implementation in this slice.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_monitor.py`
- `scripts/aios_dispatch.py`
- `tests/test_aios_monitor.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0244-service-readiness-monitor-unblock.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- sensitive vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `control_plane_monitor`
- owner_repo: `myworld`
- substrate_level: `primitive`
- surface_type: `contract`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `monitor_assessment_before_after`
  - `dispatch_contract_path_resolution_tests`
  - `focused_test_report`
  - `round_controller_status`

## Required Work For Claude

Claude should implement a narrow monitor/dispatch resolution so historical
dispatches that reference `docs/contracts/ASC-NNNN-*.md` are considered
resolved when the same filename exists under `docs/_history/contracts/`.

The implementation must preserve auditability:

- do not hide genuinely missing active contracts;
- do not treat arbitrary renamed files as valid;
- surface the resolved historical path in assessment output or diagnostics;
- keep current active-contract path checks strict;
- add regression tests for quarantined contract resolution and true missing
  contract detection.

## Plain-Language Framing

Old completed contracts were intentionally moved from the active shelf to an
archive shelf. The monitor is currently treating those archived contracts as if
they were lost. Claude's job is to teach the monitor the difference between
"archived but still present" and "actually missing."

## Assumptions

- Assumption 1: `docs/_history/contracts/<same filename>` is the canonical
  archive location for terminal historical contracts.
- Assumption 2: dispatch records that point to active `docs/contracts/*` paths
  may be resolved to history only when the same filename exists in the
  quarantine directory.
- Assumption 3: active or newly accepted contracts must not be silently
  redirected to unrelated files.

Negated checks:

- If history contains a different filename, the monitor must still report a
  missing contract.
- If both active and historical files exist, the active path wins.
- If a dispatch references a path outside the contract directories, no broad
  fallback is allowed.

## Counter-Branch

An alternative is to leave the monitor strict and instead rewrite every old
dispatch record. Reject that path for this contract: it risks mutating
append-only historical evidence. The selected branch preserves the old dispatch
record and adds an exact historical-resolution layer in the monitor.

## Cross-Domain Check

Use the geology strata analogy from the Genesis challenge: archive layers
preserve history. The implementation should read older layers without
flattening them into the active layer.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_monitor tests.test_aios_dispatch -v
python3 scripts/aios_monitor.py assess --json
python3 scripts/aios_round_controller.py status
git diff --check
```

Pass criteria:

- The high-volume fossil quarantine `dispatch_contract_path_missing` blockers
  no longer dominate `aios_monitor.py assess --json`.
- Truly missing contract paths still produce a high-severity finding.
- Round controller remains running.
- No unrelated dirty paths are staged or modified.

## AIOS Role Evidence

### MemoryOS

- draft_first: not required for this monitor-only implementation.
- privacy: no raw provider/private history reads are allowed.

### CapabilityOS

- route: local MyWorld monitor/dispatch code only.
- authority: recommendation not required; no external tool binding.

### GenesisOS

- challenge: avoid papering over audit failures; historical path resolution
  must be exact and test-backed.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements in MyWorld, then Codex/operator can verify.
- receipt: focused tests plus monitor assessment before/after.

## Work Packets

### WP-0244-A — Claude MyWorld monitor unblock

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Implement the Required Work For Claude section. Do not touch
  child repos, sensitive auth material, raw logs, `uri`, `artifacts`, `gemini`, or
  `gemini-cli`. Return a result packet with files changed, tests run, before/
  after monitor assessment summary, and any remaining blockers.
- result: pending

## Stop Conditions

- `scope_violation`
- `privacy_violation`
- `true_missing_contract_suppressed`
- `monitor_still_blocked_by_same_false_positive`
- `verification_gate_failed`
- `child_repo_source_edit`
