---
contract_id: ASC-0257
slug: dispatch-cancel-archive-reissue
status: closed
goal: Add an explicit cancel/archive/reissue primitive so wrong-agent dispatch packets can be replaced without rewriting packet or result evidence.
created: 2026-06-13T19:13:00+09:00
accepted: 2026-06-13T19:13:00+09:00
closed: 2026-06-13T19:18:00+09:00
human_approved: true
origin: ASC-0256 made existing inbox packet agent assignment immutable; serving-grade operation now needs an explicit way to cancel or reissue stale wrong-agent packets.
---

# ASC-0257 Dispatch Cancel Archive Reissue

## Why Now

ASC-0256 fixed the unsafe path: `send --force` can no longer turn a `codex`
packet into a `claude` packet. That is correct for auditability, but it leaves a
real operator need: if the wrong provider packet is already in the inbox, AIOS
needs an explicit, auditable way to move forward without editing history.

The serving-grade rule is:

```text
do not rewrite existing packet evidence
archive/cancel stale packet if safe
issue a new dispatch id for the intended provider
preserve result evidence if execution already happened
```

This contract is a control-plane lifecycle primitive. It does not build
`apps/serving/`, publish infrastructure, touch provider auth files, or edit
child repos.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0257-dispatch-cancel-archive-reissue.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/control/**`
- `apps/serving/**`
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work For Claude

Implement an auditable dispatch reissue path.

Minimum behavior:

1. Add a CLI command such as:

   ```bash
   python3 scripts/aios_dispatch.py reissue \
     --dispatch-id asc-0255 \
     --repo myworld \
     --agent claude \
     --new-dispatch-id asc-0255-claude \
     --reason wrong_agent_packet
   ```

2. The command must read the original `created` event and contract path.
3. The command must refuse if `--new-dispatch-id` already exists.
4. If an original inbox packet exists and no result evidence exists, archive it
   to `.aios/archive/inbox/<repo>/...` and append a `dispatch_packet_archived`
   or equivalent event.
5. If result evidence exists, do not delete or rewrite existing packet/result
   evidence; append a reissue event that cites the evidence.
6. The new dispatch must have its own `created` and `sent` events and a new
   inbox packet whose `agent` equals the requested worker name.
7. Add focused tests proving:
   - wrong-agent pending packet is archived and reissued to a new id;
   - result evidence is preserved and cited;
   - existing new id is refused;
   - no cross-provider packet overwrite occurs.

## AIOS Role Evidence

### MemoryOS

- context_pack: ASC-0256 closeout and dispatch route mismatch observation.
- retrieval_trace: pending_or_not_required for this narrow follow-up.
- accepted_memory_ids: pending_or_not_required.
- draft_memory_policy: no memory acceptance in this contract.

### CapabilityOS

- route: `cap_aios_child_watcher`, `cap_myworld_operator_control_plane`.
- recommended_tools: focused dispatch tests, py_compile, diff check.
- fallback_plan: if Claude cannot execute, Codex may implement this control
  primitive after recording a degraded provider receipt.
- authority: execute_with_receipt inside allowed files.

### GenesisOS

- branch_set: "mutable packet" versus "new dispatch lineage".
- assumption_mutations: a pending inbox file can already be observed by a
  watcher; treat it as evidence rather than a draft.
- semantic_alignment_notes: a service company needs dispatch reassignment as an
  incident/lifecycle primitive, not as an overwrite flag.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements bounded myworld dispatch lifecycle code.
- provider_route: `claude@myworld` through AIOS child watcher; fallback disabled
  for the first attempt so provider mismatch is visible.
- verification_receipt: unit tests, py_compile, diff check.
- degraded_or_fallback_receipt: required before Codex fallback.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_dispatch -v
python3 -m py_compile scripts/aios_dispatch.py
git diff --check
```

## Stop Conditions

- `existing_packet_rewritten_cross_provider`
- `result_evidence_deleted`
- `auth_files_touched`
- `apps_serving_modified`
- `child_repo_modified`

next: after reissue exists, future Claude-owned serving UI/runtime work can be
reissued cleanly if the first packet is stale or wrong-agent.

## Work Packets

### WP-0257-A — Claude first implementation attempt

- target_repo: `myworld`
- target_agent: `claude`
- status: held
- result: `.aios/outbox/myworld/asc-0257.myworld.result.json`
- stop_conditions_triggered: `pending_concurrent_work`
- note: fallback was disabled, so the Claude hold stayed visible instead of
  being silently converted to Codex work.

### WP-0257-B — Codex fallback implementation

- target_repo: `myworld`
- target_agent: `codex`
- status: passed
- reason: contract fallback clause allowed Codex after degraded Claude receipt.

## Result Packet

schema_version: `aios.result_packet.v1`
contract_id: `ASC-0257`
dispatch_id: `asc-0257`
repo: `myworld`
agent: `codex@myworld`
status: `passed_with_claude_hold`

changed:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0257-dispatch-cancel-archive-reissue.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

evidence:

- `python3 -m unittest tests.test_aios_dispatch -v` passed 55/55.
- `python3 -m py_compile scripts/aios_dispatch.py` passed.
- `git diff --check` passed.
- `asc-0257` Claude child-watcher attempt returned `status=held` with
  `stop_conditions_triggered=["pending_concurrent_work"]`.

implemented:

- `python3 scripts/aios_dispatch.py reissue --dispatch-id <old> --repo <repo> --agent <agent> --new-dispatch-id <new> --reason <reason>`
- pending source inbox packets are archived to `.aios/archive/inbox/<repo>/`
  before the new dispatch is sent.
- if source result evidence exists, the original packet/result evidence is not
  deleted or rewritten; the new packet cites `source_result_evidence`.
- `--new-dispatch-id` must be unused and distinct from the source dispatch id.

remaining_gaps:

- This is a local file lifecycle primitive. It does not yet expose a UI affordance
  or a hosted service API for operators/users to trigger reissue.
