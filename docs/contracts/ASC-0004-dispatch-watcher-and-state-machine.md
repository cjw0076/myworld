---
contract_id: ASC-0004
slug: dispatch-watcher-and-state-machine
status: closed
goal: Add release/hold/retry/escalate state machine to aios_dispatch and a V1 watcher that auto-runs verification gates from inbox packets.
created: 2026-05-11 KST
accepted: 2026-05-11 KST
closed: 2026-05-11 KST
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST delegating routine acceptance to claude+codex pair.
closure_authority: claude@myworld (operator) after independent watcher-replay verification.
---

# ASC-0004 Dispatch Watcher And State Machine

## Control Plane Position

This contract was issued by `claude@myworld` per operator directive 2026-05-11 KST ("watcher / state machine부터 contract로") and accepted after the founder delegated routine acting-operator authority to the Codex/Claude pair. The control plane scope is myworld only — no child-repo source edits in this contract.

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

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_loop.py`
- `scripts/aios_monitor.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_loop.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/contracts/ASC-0004-dispatch-watcher-and-state-machine.md`
- `docs/contracts/README.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.runs/**`
- `raw_exports/**`
- `weights/**`
- `.env`
- `.env.*`
- `.aios/logs/**` committed or copied into docs
- arbitrary command strings outside contract `## Verification Gate`

ASC-0004 may invoke existing child-repo verification commands through the
watcher, but invocation is not ownership. No child repo source file is in
scope.

## Design Answers

### Q1 — State set and transition graph

The state set is append-only events:

`created -> sent -> running -> watched -> collected -> released`

The error and checkpoint branches are:

- `watched -> held` for missing evidence, missing verification commands, or
  review needs.
- `watched -> retried` when a failure is transient or a corrected packet should
  be attempted again.
- `watched -> escalated` when scope, privacy, ownership, or contract ambiguity
  exceeds acting-operator authority.
- `* -> stopped` for explicit cancellation/checkpoint.

`revised` is not an in-place state. A revision edits the contract or creates a
new dispatch, preserving the old dispatch as evidence.

### Q2 — Transition authority

- `created`, `sent`, `running`, `watched`, and `collected` are automatic
  control-plane transitions.
- `released` requires acting-operator judgment after result evidence exists.
  Human operator authority is delegated to Codex/Claude for routine releases by
  the 2026-05-11 instruction, but high-risk releases can still be escalated.
- `held` and `escalated` may be set by Codex, Claude, or the human operator.
- `retried` may be set by Codex/Claude after a bounded failure diagnosis.
- `stopped` is a terminal checkpoint/cancellation.

### Q3 — Watcher invocation model

V1 is on-demand only:

```bash
python scripts/aios_dispatch.py watch --repo <repo> --dispatch-id <id> --once
```

A daemon is out of scope because AIOS first needs auditable state semantics
before long-running process management. Daemon mode can be a later contract
after V1 packets and result schemas prove stable.

### Q4 — Per-packet command resolution

The watcher reads the packet's `contract_path`, extracts fenced `bash` blocks
under `## Verification Gate`, ignores the `Operational smoke equivalent`
subsection, and selects commands whose preceding `cd` path matches the target
repo. It only runs direct Python/pytest argv forms and rejects shell
metacharacter commands as `arbitrary_command_execution`.

ASC-0003 overlaps on richer packet enrichment. Since ASC-0004 landed first, it
contains a minimal extractor in `scripts/aios_dispatch.py`; ASC-0003 should
refactor to share or enrich this extractor instead of creating a second parser.

### Q5 — Failure semantics

- `passed`: every selected command returns exit code 0 and no stop condition is
  triggered.
- `failed`: a selected command returns nonzero; result includes
  `test_gate_failed`.
- `held`: no verification command is available or a command is unsafe.
- `retry`: not inferred automatically in V1; acting operators mark it with
  `python scripts/aios_dispatch.py retry --reason ...` after diagnosis.

### Q6 — Logging boundaries

The result packet contains bounded stdout/stderr summaries only. Full logs go to
`.aios/logs/<dispatch_id>.<repo>.log`, which is covered by `.gitignore` through
the `.aios/` runtime-state rule. Full logs must not be committed or pasted into
contract receipts if they may contain private data.

### Q7 — Coordination with ASC-0003

ASC-0004 owns execution of existing verification gates. ASC-0003 owns enriched
packet shape. When ASC-0003 is accepted, it should consume the watcher extractor
or move the shared parsing logic into a common helper without changing
`aios.dispatch.v1` required fields.

## Per-OS Responsibility

- **myworld (control plane).must_produce**: state machine commands, watcher V1,
  result packet writer, bounded log policy, regression tests, updated dispatch
  docs.
- **hive_mind.must_produce**: no source change. It may be invoked by watcher
  replay through existing ASC-0001 verification commands.
- **memoryos.must_produce**: no source change. It may be invoked by watcher
  replay through existing ASC-0001 verification commands.
- **capabilityos.must_produce**: no role in this contract.
- **operator.must_produce**: delegated acting-operator policy. Codex/Claude can
  release/hold/retry/escalate routine control-plane work; privacy, ownership,
  or scope conflicts escalate.

## Verification Gate

Unit gate:

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py

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
- State log shows transitions: `created -> sent -> running -> watched -> collected -> released`
- `.aios/logs/asc-0001-watcher-replay.<repo>.log` exists, is NOT staged for commit, contains stdout/stderr

## Stop Conditions

- `arbitrary_command_execution`: watcher runs a command not extracted from contract verification gate.
- `daemon_creep`: V1 demands a background daemon, autostart, or persistent process.
- `child_repo_source_edit`: ASC-0004 modifies any file under `hivemind/`, `memoryOS/`, `CapabilityOS/`.
- `state_explosion`: states added beyond the agreed set in Q1 without contract.
- `transition_authority_drift`: a transition that Q2 says requires operator becomes automatic.
- `log_privacy_leak`: full stdout/stderr logs written under a path that is committed (must be gitignored or in result-packet summary only).
- `breaking_change_without_version_bump`: dispatch-event schema field rename/removal without bumping `schema_version`.

## Receipts

Closed 2026-05-11 KST. Watcher V1 + state machine implemented by `codex@myworld` per WP-0004-A; independently re-verified by `claude@myworld` (operator).

- Acceptance commit (status proposed → accepted): part of the same closure commit (`a8c0164`+ successors).
- Implementation: `scripts/aios_dispatch.py` (state machine, watcher subcommand), `scripts/aios_loop.py`, `scripts/aios_monitor.py`, `tests/test_aios_dispatch.py`, `tests/test_aios_loop.py`, `tests/test_aios_monitor.py`.
- Unit verification: `python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py` -> 10 tests OK in 0.984s.
- **Watcher dogfood replay**: re-ran ASC-0001 closed-loop proof end-to-end through the new watcher (dispatch_id `asc-0001-watcher-replay`):
  - `aios_dispatch.py create … --force --dispatch-id asc-0001-watcher-replay` → ok
  - `aios_dispatch.py send --repo memoryOS …` → packet at `.aios/inbox/memoryOS/asc-0001-watcher-replay.memoryOS.json`
  - `aios_dispatch.py send --repo hivemind …` → packet at `.aios/inbox/hivemind/asc-0001-watcher-replay.hivemind.json`
  - `aios_dispatch.py watch --repo memoryOS --once` → status `passed`, result at `.aios/outbox/memoryOS/asc-0001-watcher-replay.memoryOS.result.json`
  - `aios_dispatch.py watch --repo hivemind --once` → status `passed`, result at `.aios/outbox/hivemind/asc-0001-watcher-replay.hivemind.result.json`
- **Significance**: this is the first session in which AIOS closed a verification gate **without manual pytest invocation by claude@myworld**. The watcher consumed the contract's `## Verification Gate` section, executed the extracted commands, and wrote result packets — exactly the gap surfaced by ASC-0001 dogfood.
- Stop conditions triggered: none.
- WP-0004-A status: done. WP-0004-B (claude review) is inlined as this
  Receipts entry because acting-operator authority covers read-only
  verification closeout.
- Ledger closeout entry: `docs/AIOS_AGENT_LEDGER.md` 2026-05-11 KST ASC-0004 closeout.

## Work Packets

### WP-0004-A — Codex drafts ASC-0004 body and implements

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 KST
- closed: 2026-05-11 KST
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

- result: implemented in `scripts/aios_dispatch.py` (state machine + watch
  subcommand), `scripts/aios_loop.py`, `scripts/aios_monitor.py`, and tests;
  unit + watcher-replay verification both pass; see Receipts section above.
