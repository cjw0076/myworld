---
contract_id: ASC-0020
slug: hive-worklog-gap-cleanup
status: closed
goal: Turn Hive worklog and gap-radar signals into one current executable Hive packet without re-opening closed work.
created: 2026-05-12 00:06 KST
accepted: 2026-05-12 00:06 KST by codex acting operator
closed: 2026-05-12 00:10 KST
supersedes: none
---

# ASC-0020 Hive Worklog Gap Cleanup

## Goal

The loop policy's top executable candidate is currently
`hivemind/docs/AGENT_WORKLOG.md`, with related high-signal sources in
`hivemind/docs/HIVE_MIND_GAPS.md` and `hivemind/docs/TODO.md`.

Those files mix completed sprint history, current unchecked tasks, and old gap
diagnosis. This contract asks Hive Mind to produce a current, bounded gap
triage artifact that selects exactly one next Hive implementation packet and
does not re-open already closed work.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/docs/HIVE_MIND_GAPS.md`
- `hivemind/docs/TODO.md`
- `hivemind/docs/RADAR_GAP_TRIAGE.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0020-hive-worklog-gap-cleanup.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/.runs/**`
- `hivemind/data/**`
- `hivemind/raw_exports/**`
- `hivemind/exports/**`
- `hivemind/logs/**`
- `hivemind/weights/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/**`
- `.runs/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **hive_mind.must_produce**: `docs/RADAR_GAP_TRIAGE.md` with:
  - source inventory for `docs/AGENT_WORKLOG.md`, `docs/HIVE_MIND_GAPS.md`,
    and `docs/TODO.md`;
  - completed/closed signals that must not be re-opened;
  - current unchecked Hive candidates;
  - one selected next implementation packet with owner, allowed files,
    forbidden files, verification gate, stop conditions, and expected result.
- **myworld.must_produce**: contract, dispatch packet, collect/release decision,
  ledger update, and monitor/readiness verification.
- **memoryos.must_produce**: no source change.
- **capabilityos.must_produce**: no source change.
- **operator.must_produce**: release only if the Hive triage artifact is
  specific enough to become ASC-0021 or a repo-local work packet.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_radar_review.py -v

cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Expected evidence:

- Hive writes one triage artifact, not a broad implementation patch.
- The artifact names exactly one next implementation packet.
- Closed work remains closed.
- Operator spot-check confirms `docs/RADAR_GAP_TRIAGE.md` contains
  `Selected Next Packet` and `Do Not Reopen` sections.
- No child repo outside `hivemind` changes.
- Monitor assessment remains clear or provides an actionable owner/action.

## Stop Conditions

- `implementation_scope_creep`: worker starts code implementation instead of
  triage.
- `closed_work_reopened`: completed TODO/worklog items are treated as new work
  without evidence.
- `capability_routing_needed`: selected packet depends on CapabilityOS evidence
  not yet available.
- `memoryos_source_edit`: worker edits MemoryOS instead of the Hive mirror.
- `private_runtime_commit`: `.runs/**`, raw exports, logs, secrets, or local
  runtime state would be staged.

## Receipts

Closed 2026-05-12 00:10 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0020.hivemind.json`
  - `.aios/outbox/hivemind/asc-0020.hivemind.result.json`
- Child watcher initially failed because the provider CLI returned access
  denied; Codex completed the same repo-local packet manually under the
  contract scope.
- `hivemind`: committed `540ae37` (`Add radar gap triage`) with:
  - `docs/RADAR_GAP_TRIAGE.md`
  - `.ai-runs/shared/comms_log.md`
- Verification:
  - `cd hivemind && python -m pytest tests/test_radar_review.py -v` passed
    2/2.
  - Operator spot-check confirmed `docs/RADAR_GAP_TRIAGE.md` contains
    `Selected Next Packet`, `Do Not Reopen`, and `ASC-0021`.
  - `git diff --check -- docs/RADAR_GAP_TRIAGE.md .ai-runs/shared/comms_log.md`
    passed.
  - `python scripts/aios_dispatch.py collect --repo hivemind` collected the
    result packet as `passed`.
  - `python scripts/aios_dispatch.py release --dispatch-id asc-0020 --reason
    asc_0020_hive_gap_triage_verified` succeeded.
- Selected next packet: `ASC-0021 — Hive Arrival Pack`.
- Stop conditions triggered: none.

## Work Packets

### WP-0020-A — Codex@hivemind creates current gap triage artifact

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 00:06 KST
- closed: 2026-05-12 00:10 KST
- depends_on: ASC-0018, ASC-0019
- brief: |
    Read `docs/AGENT_WORKLOG.md`, `docs/HIVE_MIND_GAPS.md`, and
    `docs/TODO.md`. Create `docs/RADAR_GAP_TRIAGE.md` that separates completed
    evidence from current unchecked Hive candidates and selects one next
    implementation packet. Do not implement that packet yet.
- result: committed `540ae37`; selected `ASC-0021 — Hive Arrival Pack`.

### WP-0020-B — Codex@myworld collects and releases Hive triage result

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 00:06 KST
- closed: 2026-05-12 00:10 KST
- depends_on: WP-0020-A
- brief: |
    Collect the Hive result packet, verify monitor/readiness, update ledger and
    contract index, then either release ASC-0020 or hold with the next required
    packet.
- result: dispatch collected and released; see Receipts.
