---
contract_id: ASC-0200
slug: genesisos-aios-ui-ux-seed
status: closed
goal: GenesisOS가 지금 AIOS UI/UX에서 느껴야 할 불편함을 찾아줘. 단순 개선이 아니라 새로운 필요성과 발명 seed로 바꿔줘.
created: 2026-05-18T04:01:54+09:00
accepted: 2026-05-18T04:20:00+09:00
closed: 2026-05-18T04:29:00+09:00
praxis_required: true
praxis_ref: .aios/asks/ask-45b63b455d6d-20260518T040154/praxis.json
origin: AIOS ask ask-45b63b455d6d-20260518T040154
accepted_by: codex_delegated_operator
---

# ASC-0200 Genesisos Aios Ui Ux Seed

## Why Now

This proposed contract was generated from AIOS ask `ask-45b63b455d6d-20260518T040154`.

- ask_instruction: `.aios/asks/ask-45b63b455d6d-20260518T040154/instruction.md`
- praxis: `.aios/asks/ask-45b63b455d6d-20260518T040154/praxis.json`

The governed ask has been narrowed and accepted by the delegated operator.
This contract is advisory-first: GenesisOS must expose discomfort, alternate
worldlines, and invention candidates, but it must not implement UI changes or
claim final truth.

## Scope

repos:

- `GenesisOS`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0200-genesisos-aios-ui-ux-seed.md`
- `docs/AGENT_WORKLOG.md`
- `GenesisOS/docs/AGENT_WORKLOG.md`
- `GenesisOS/seeds/asc-0200-ui-ux-discomfort.json`
- `GenesisOS/seeds/asc-0200-ui-ux-branches.json`
- `GenesisOS/seeds/asc-0200-ui-ux-critique.json`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- `apps/control/app.js`
- `apps/control/styles.css`
- `apps/control/index.html`
- GenesisOS implementation files under `GenesisOS/genesisos/`
- GenesisOS tests under `GenesisOS/tests/`
- child repo implementation files unless explicitly assigned by a later
  accepted contract

## Responsibilities

### GenesisOS

must_produce:

- A semantic handshake with these terms distinguished:
  `discomfort_signal`, `named_need`, `invention_candidate`,
  `contract_seed`, `branch`, `risk`, and `advisory_only`.
- `GenesisOS/seeds/asc-0200-ui-ux-discomfort.json` from
  `python -m genesisos.cli discomfort --text ... --goal ... --json`, using
  the current Control Center evidence and the materialized ask as input.
- `GenesisOS/seeds/asc-0200-ui-ux-branches.json` from
  `python -m genesisos.cli diverge --goal ... --json`.
- `GenesisOS/seeds/asc-0200-ui-ux-critique.json` from
  `python -m genesisos.cli critique --goal ... --idea ... --json`.
- A repo-local worklog entry that names:
  - the strongest discomfort,
  - the missing user affordance,
  - at least two invention candidates,
  - risks and why they may be wrong,
  - the next MyWorld contract seed if one should be promoted.

must_not:

- Modify Control Center source files.
- Accept memories.
- Route tools.
- Launch provider CLIs.
- Treat a branch as implementation authority.

### myworld

must_produce:

- Dispatch packet to `GenesisOS` with the praxis envelope.
- Dispatch only with `--praxis .aios/asks/ask-45b63b455d6d-20260518T040154/praxis.json`.
- Collect the result packet from `.aios/outbox/GenesisOS/`.
- Review GenesisOS output before creating any implementation contract.

## AIOS Role Evidence

### MemoryOS

- context_pack: `.aios/invocations/ask-45b63b455d6d-20260518T040154/memory/context_pack.md`
- retrieval_trace: ask praxis evidence
- accepted_memory_ids: governed ask context only
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `.aios/invocations/ask-45b63b455d6d-20260518T040154/capability/route.json`
- recommended_tools: GenesisOS divergence, prompt-prison critic, Hive execution harness, MemoryOS context build, AIOS readiness scorer
- fallback_plan: use deterministic GenesisOS CLI surfaces if provider agent is unavailable
- authority: `recommendation_only`

### GenesisOS

- branch_set: `GenesisOS/seeds/asc-0200-ui-ux-branches.json`
- discomfort_payload: `GenesisOS/seeds/asc-0200-ui-ux-discomfort.json`
- critique_payload: `GenesisOS/seeds/asc-0200-ui-ux-critique.json`
- semantic_alignment_notes: repo-local worklog semantic handshake
- authority: `advisory_only`

### Hive Mind

- execution_plan: `.aios/invocations/ask-45b63b455d6d-20260518T040154/hive/execution_plan.json`
- provider_route: child watcher dispatch agent route
- verification_receipt: `.aios/outbox/GenesisOS/asc-0200.GenesisOS.result.json`
- degraded_or_fallback_receipt: `pending_if_triggered`


## Verification Gate

```bash
cd .
python scripts/aios_work_praxis.py validate .aios/asks/ask-45b63b455d6d-20260518T040154/praxis.json --json
python scripts/aios_dispatch.py create docs/contracts/ASC-0200-genesisos-aios-ui-ux-seed.md --dispatch-id asc-0200
python scripts/aios_dispatch.py send --repo GenesisOS --agent codex --dispatch-id asc-0200 --praxis .aios/asks/ask-45b63b455d6d-20260518T040154/praxis.json
scripts/aios_child_watcher.sh once --repo GenesisOS
python scripts/aios_dispatch.py collect --repo GenesisOS
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `genesis_output_claims_authority`
- `genesis_modifies_control_center_source`
- `genesis_launches_provider`
- `genesis_accepts_memory`
- `genesis_routes_tool`
- `discomfort_payload_missing`
- `branch_payload_missing`
- `critique_payload_missing`
- `scope_ambiguous`
- `praxis_invalid`
- `owner_repo_unclear`
- `verification_gate_missing`
- `monitor_blocking_finding`

## Receipts

- dispatch_packet: `.aios/inbox/GenesisOS/asc-0200.GenesisOS.json`
- dispatch_result: `.aios/outbox/GenesisOS/asc-0200.GenesisOS.result.json`
- provider_fallback_route: `.aios/logs/asc-0200.GenesisOS.fallback-1.provider_route.json`
- genesis_worklog: `GenesisOS/docs/AGENT_WORKLOG.md`
- discomfort_payload: `GenesisOS/seeds/asc-0200-ui-ux-discomfort.json`
- branch_payload: `GenesisOS/seeds/asc-0200-ui-ux-branches.json`
- critique_payload: `GenesisOS/seeds/asc-0200-ui-ux-critique.json`

Outcome:

- Codex provider failed first with `provider_access_denied`.
- CapabilityOS provider fallback selected a replacement route.
- Claude completed the GenesisOS advisory turn.
- GenesisOS identified `reactive_passivity` as the strongest discomfort and
  recommended an `AIOS Interaction Grammar Innovation` contract before adding
  more panels.
