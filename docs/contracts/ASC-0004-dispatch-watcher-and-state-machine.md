---
contract_id: ASC-0004
slug: dispatch-watcher-and-state-machine
status: proposed
goal: Add release/hold/retry/escalate state machine to aios_dispatch and a V1 watcher that auto-runs verification gates from inbox packets.
created: 2026-05-11 KST
accepted: pending
closed: pending
supersedes: none
---

# ASC-0004 Dispatch Watcher And State Machine

## Control Plane Position

This stub is issued by `claude@myworld` per operator directive 2026-05-11 KST ("watcher / state machine부터 contract로"). Status `proposed`. Body deferred to WP-0004-A (codex@myworld). The control plane scope is myworld only — no child-repo source edits in this contract.

## Goal

The ASC-0001 dogfood pass surfaced two structural gaps in the AIOS control loop (per `project_aios_directing.md` memory and ledger 2026-05-11 entry):

1. **No watcher / auto-executor**: packets land in `.aios/inbox/<repo>/` but nothing runs them. The control plane (claude@myworld) had to manually shell out to pytest commands to close ASC-0001's verification gate. This is the largest gap from ASC-0001 dogfood findings.
2. **No state machine beyond stop**: `aios_dispatch.py` exposes only `create | send | collect | stop`. The operator's terminal-state vision (2026-05-11 chat) names five states — release, revise, retry, hold, escalate — none of which are first-class commands or state-log fields.

ASC-0004 fixes both, in one contract, because they are tightly coupled: a watcher that runs work needs to know transition semantics (when to retry vs hold vs escalate), and the state machine without a watcher is just bureaucracy.

ASC-0004 explicitly does **not**:
- run arbitrary commands. The watcher V1 must only execute verification commands extracted from the contract's `## Verification Gate` section.
- become a background daemon. V1 is on-demand (`aios_dispatch watch --once` or similar).
- modify child repo source. Watcher is myworld-only and shells out to existing child-repo test entry points.
- include CapabilityOS observation feedback (separate future contract).

## Open Design Questions

The drafter (codex@myworld via WP-0004-A) must answer in the contract body:

- **Q1 — State set + transition graph**: Operator's listed states are `release / revise / retry / hold / escalate`. Existing dispatch states are `created / sent / collected / stopped`. Recommendation: unify into one set: `created → sent → running → collected → {released|held|escalated|retried|stopped}`. `revised` triggers a new dispatch (does not transition the old one). Justify and draw the graph.
- **Q2 — Authority per transition**: Who can move state? Recommendation: `created/sent/running/collected` are control-plane automatic; `released` is operator-only; `held/escalated` are control-plane or operator; `retried` is control-plane (with operator override); `stopped` is operator. Document.
- **Q3 — Watcher invocation model**: V1 should be on-demand CLI (`aios_dispatch watch --repo <repo> --once`), not a daemon. Justify why a daemon is out of scope (deferred to V2 if needed).
- **Q4 — Per-packet command resolution**: How does the watcher know what to run for a given packet? Recommendation: read the contract referenced in the packet's `contract_path`, extract verification commands per Q2 of ASC-0003 (verification command extraction). If ASC-0003 has not landed yet, define a minimal extraction inline and refactor when ASC-0003 lands. Coordinate with ASC-0003.
- **Q5 — Failure semantics**: What is a "passed" vs "failed" vs "retry" outcome? Recommendation: passed = exit code 0 + no `stop_conditions_triggered` in result; failed = nonzero exit code; retry = explicit `retryable_failure` annotation in result (e.g. transient subprocess error). Document.
- **Q6 — Logging boundaries**: Watcher captures stdout/stderr from verification commands. Where does it go? Recommendation: short summary (first 20 lines + last 20 lines) into result packet; full log into `.aios/logs/<dispatch_id>.<repo>.log` (gitignored). Privacy stop condition: full logs MUST NOT be committed.
- **Q7 — Coordination with ASC-0003**: ASC-0003 (packet enrichment) overlaps on verification command extraction. If ASC-0003 lands first, ASC-0004 watcher consumes the enriched packet. If ASC-0004 lands first, ASC-0003 should refactor to share the extractor. Pick a coordination policy.

## Scope (stub — to be filled by WP-0004-A)

- repos: _to be filled — must be exactly `[myworld]`. ASC-0004 does not modify hivemind, memoryOS, or CapabilityOS source. (Watcher shells out to existing test entry points; that is invocation, not modification.)_
- allowed_files: _to be filled — at minimum:_
  - `scripts/aios_dispatch.py` (state machine commands + state field)
  - `scripts/aios_watcher.py` or `scripts/aios_dispatch.py` extension (watcher V1)
  - `tests/test_aios_dispatch.py` (state machine tests)
  - `tests/test_aios_watcher.py` (watcher tests)
  - `docs/AIOS_WORK_DISPATCH.md` (document state set, watcher behavior, log paths)
  - `.gitignore` (add `.aios/logs/`)
- forbidden_files: _to be filled — at minimum: contract files in `docs/contracts/` (ASC-0004 changes the dispatch surface, not the contracts), all child repo source paths, `.runs/`, raw exports, secrets, weights._

## Per-OS Responsibility (stub)

- **myworld (control plane).must_produce**: state machine commands + state-log field, watcher V1, regression tests, updated AIOS_WORK_DISPATCH.md, log path policy.
- **hive_mind, memoryos, capabilityos**: not in scope. (ASC-0001 verification gate commands still run inside their repos when watcher invokes them, but no source change.)
- **operator.must_produce**: acceptance decision; explicit policy for which transitions require operator approval (Q2).

## Verification Gate (stub)

_to be filled by WP-0004-A. Recommended target:_

```bash
cd /home/user/workspaces/jaewon/myworld
python -m pytest tests/test_aios_dispatch.py tests/test_aios_watcher.py -v

# Watcher V1 dogfood: re-run ASC-0001 closed-loop proof end-to-end through watcher
python scripts/aios_dispatch.py create docs/contracts/ASC-0001-memoryos-hivemind-loop.md --force --dispatch-id asc-0001-watcher-replay
python scripts/aios_dispatch.py send --repo memoryOS --agent codex --dispatch-id asc-0001-watcher-replay --force
python scripts/aios_dispatch.py send --repo hivemind --agent codex --dispatch-id asc-0001-watcher-replay --force
python scripts/aios_dispatch.py watch --repo memoryOS --once --dispatch-id asc-0001-watcher-replay
python scripts/aios_dispatch.py watch --repo hivemind --once --dispatch-id asc-0001-watcher-replay
python scripts/aios_dispatch.py status --json
```

Expected evidence:
- pytest passes for state machine + watcher tests
- Watcher writes result packets to `.aios/outbox/<repo>/` automatically
- Both repos collect status `passed` without manual pytest invocation
- State log shows transitions: `created → sent → running → collected → released` (or whatever Q1 graph defines)
- `.aios/logs/asc-0001-watcher-replay.<repo>.log` exists, is NOT staged for commit, contains stdout/stderr

## Stop Conditions (stub)

_to be filled by WP-0004-A — at minimum:_
- `arbitrary_command_execution`: watcher runs a command not extracted from contract verification gate.
- `daemon_creep`: V1 demands a background daemon, autostart, or persistent process.
- `child_repo_source_edit`: ASC-0004 modifies any file under `hivemind/`, `memoryOS/`, `CapabilityOS/`.
- `state_explosion`: states added beyond the agreed set in Q1 without contract.
- `transition_authority_drift`: a transition that Q2 says requires operator becomes automatic.
- `log_privacy_leak`: full stdout/stderr logs written under a path that is committed (must be gitignored or in result-packet summary only).
- `breaking_change_without_version_bump`: dispatch-event schema field rename/removal without bumping `schema_version`.

## Receipts

_filled at closeout._

## Work Packets

### WP-0004-A — Codex drafts ASC-0004 body and implements

- target_agent: codex
- target_repo: myworld
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: ASC-0001 closed (dogfood precedent), operator acceptance of ASC-0004
- brief: |
    This packet does TWO things in sequence:
    (1) Fill the stub sections of ASC-0004 (Scope, Per-OS Responsibility,
        Verification Gate, Stop Conditions) and answer Q1–Q7.
    (2) Implement state machine + watcher V1 in `scripts/aios_dispatch.py`
        (or a new `scripts/aios_watcher.py`), with regression tests.

    Required reading, in order:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0001-memoryos-hivemind-loop.md
         (the contract whose verification gate the watcher V1 must run)
      4. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0003-dispatch-packet-enrichment.md
         (verification command extraction overlaps; coordinate per Q7)
      5. /home/user/workspaces/jaewon/myworld/scripts/aios_dispatch.py
         (the file being extended)
      6. /home/user/workspaces/jaewon/myworld/tests/test_aios_dispatch.py
      7. /home/user/workspaces/jaewon/myworld/.aios/state/dispatches.jsonl
         (event log shape — extend, do not break)
      8. /home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_LEDGER.md
         (2026-05-11 ASC-0001 dogfood findings — five of those are this contract's targets)

    Constraints:
    - V1 watcher is on-demand only (`watch --once`). Do not add daemon mode.
    - Watcher must only execute commands extracted from the contract's
      `## Verification Gate` section. Reject unknown commands; do not
      execute arbitrary shell input.
    - State machine must keep `aios.dispatch.v1` schema backward compatible
      (add fields, do not rename/remove).
    - Privacy: full stdout/stderr logs land under `.aios/logs/` (gitignored);
      result packet summary is bounded.
    - Coordination with ASC-0003: if ASC-0003 lands first, consume its
      enriched packet. If ASC-0004 lands first, write a minimal extractor
      and refactor when ASC-0003 lands. Document the choice in body.

    If a stronger design surfaces (e.g. state machine and watcher are too
    different to bundle), add a `## Counter-Proposal` section recommending
    a split (e.g. ASC-0004 = state machine only, ASC-NNNN = watcher) and
    stop. Operator decides.

    After drafting + implementing:
    - Update WP-0004-A status `issued` → `done`, fill `closed`, fill
      `result` with commit SHA(s).
    - Issue WP-0004-B inline: target_agent claude, target_repo myworld,
      brief = "review filled ASC-0004 + implementation: state graph
      coherence, watcher safety (no arbitrary execution), privacy
      boundaries (logs gitignored), Q1–Q7 answer completeness, no scope
      creep into daemon or child-repo edits".
    - Run the ASC-0001 watcher replay as part of verification. If it
      passes end-to-end without manual pytest invocation, the watcher V1
      goal is met.
    - Do NOT append to AIOS_AGENT_LEDGER.md until ASC-0004 is closed.

- result: pending
