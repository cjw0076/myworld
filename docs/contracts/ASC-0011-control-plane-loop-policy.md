---
contract_id: ASC-0011
slug: control-plane-loop-policy
status: accepted
goal: Decide which doc-radar candidates become accepted contracts and which remain held; codify the operator selection policy in a checkable script.
created: 2026-05-11 KST
accepted: 2026-05-11 KST by claude acting operator
closed: pending
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST.
origin: auto-proposed by `scripts/aios_doc_scout.py` as `ASC-0007-followup`; promoted to ASC-0011 ID for sequential numbering.
---

# ASC-0011 Control Plane Loop Policy

## Control Plane Position

myworld owns this contract. It does not modify child repo source. Once ASC-0008/0009/0010 land, the control plane will be receiving signals AND observations AND verdicts simultaneously. Without a policy, the operator pair could over-accept, over-defer, or oscillate. ASC-0011 fixes the loop's selection rule.

## Goal

Define and implement a `python scripts/aios_loop_policy.py --json` command that, given:
- the latest `docs/AIOS_TASK_RADAR.md` (ASC-0007),
- accumulated `CapabilityObservation`s (ASC-0009),
- semantic verdicts from `hive radar-review` (ASC-0010),
- and the current open contract count,

emits a ranked list of radar candidates with one of: `accept_now | hold_for_capacity | hold_for_capability | hold_for_operator | reject_out_of_scope`. The operator pair uses this output to drive the next contract acceptance turn instead of guessing.

V1 scope:
- Policy is rule-based, not learned. Rules encoded in code, justified in body Q1.
- Loop capacity cap: at most N open `accepted+pending+active` contracts at once. N = 4 in V1 (justifiable in Q3).
- Output is a ranked list with verdict and reason — not auto-acceptance.

Explicitly does **not**:
- auto-accept contracts.
- run any LLM/external call.
- replace founder's vision-level escalation rules.

## Open Design Questions

To be answered by `codex@myworld` (WP-0011-A):

- **Q1 — Selection rules**: enumerate the rule set. Recommended seed rules:
  - `accept_now` if (verdict==`executable` AND no capability gap AND open_count < N AND no `_from_desktop` path AND no `dain` path)
  - `hold_for_capacity` if (verdict==`executable` AND open_count >= N)
  - `hold_for_capability` if (verdict==`needs_capability`)
  - `hold_for_operator` if (path under `_from_desktop/`, `dain/`, `minyoung/`)
  - `reject_out_of_scope` if (verdict==`out_of_scope`)
  - `hold_for_operator` (default) for everything else
- **Q2 — Tie-breaking when multiple `accept_now`**: highest scout score wins, ties broken by domain priority `myworld > hivemind > memoryOS > CapabilityOS > others`. Justify.
- **Q3 — Capacity N**: V1 = 4. Operator pair can sustain ~4 parallel contracts based on this session's evidence (ASC-0007..0010 all in flight). Re-tune later.
- **Q4 — Privacy gating**: confirm `_from_desktop/` and `dain/`, `minyoung/` paths are always `hold_for_operator` (not `accept_now`). Include in stop conditions.
- **Q5 — Output schema**: `aios.loop_policy.v1` with `generated_at`, `open_contract_count`, `decisions[]` where each decision = `(contract_candidate_id, verdict, reason, sources[])`.

## Scope (stub — WP-0011-A fills)

- repos: `[myworld]`.
- allowed_files: _to be filled — at minimum `scripts/aios_loop_policy.py`, `tests/test_aios_loop_policy.py`, `docs/AIOS_WORK_DISPATCH.md` (document the policy)._
- forbidden_files: `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `_from_desktop/**`, `dain/**`, `minyoung/**`, `.runs/**`, raw exports, secrets, weights.

## Per-OS Responsibility (stub)

- **myworld.must_produce**: policy script, tests, doc update, sample output committed.
- **hive_mind / memoryos / capabilityos**: not in scope.
- **operator.must_produce**: closeout review; integrate policy output into the next acceptance turn.

## Verification Gate (stub)

```bash
cd /home/user/workspaces/jaewon/myworld
python -m pytest tests/test_aios_loop_policy.py -v
python scripts/aios_loop_policy.py --json
```

Expected evidence:
- pytest passes.
- output JSON has `schema_version: aios.loop_policy.v1`, `decisions[]` with each verdict and reason.
- no `_from_desktop/`/`dain/`/`minyoung/` candidate ever marked `accept_now`.

## Stop Conditions (stub)

- `auto_acceptance`: policy code calls anything that flips a contract status.
- `privacy_path_accept`: `_from_desktop/`/`dain/`/`minyoung/` candidate marked `accept_now`.
- `external_llm_call`: any external API call.
- `child_repo_source_edit`: this contract modifies child repo source.
- `oversize_decision_set`: output > 100 decisions (truncate or paginate before that).
- `unbounded_capacity`: capacity cap missing or negative.

## Receipts

_filled at closeout._

## Work Packets

### WP-0011-A — Codex@myworld implements loop policy

- target_agent: codex
- target_repo: myworld
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: ASC-0007 closed (radar exists), ASC-0010 closed (verdicts exist) — soft dependencies; can implement skeleton now and refine when ASC-0010 lands.
- brief: |
    Fill ASC-0011 stub sections and answer Q1–Q5. Implement
    `aios_loop_policy.py` + tests + doc update.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0007-workspace-doc-scout-task-radar.md
      4. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0010-hive-semantic-quality-gate.md
      5. /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md
      6. /home/user/workspaces/jaewon/myworld/scripts/aios_dispatch.py (state machine reference)

    Constraints:
    - Rule-based policy only — no learned model.
    - Operator-only paths (`_from_desktop`, `dain`, `minyoung`) NEVER `accept_now`.
    - No auto-acceptance — output is advisory only.
    - V1 capacity = 4 open contracts.

    After drafting + implementing:
    - Update WP-0011-A status, fill `result` with commit SHA.
    - Issue WP-0011-B for claude review.
- result: pending
