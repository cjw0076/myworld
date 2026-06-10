---
contract_id: ASC-0199
slug: aios-session
status: withdrawn
goal: 현재 상태 알려줘
created: 2026-05-18T02:56:53+09:00
accepted:
closed:
origin: AIOS reviewed session promotion
session_envelope_ref: .aios/invocations/chat-6372babf0c9ebf88/session_envelope.json
promotion_receipt: .aios/promotions/promotion-1d0db7e1e829-20260518T025653/promotion.json
withdrawn: 2026-05-18 KST
withdrawn_reason: session-promotion misfire — the goal '현재 상태 알려줘' is a chat status query auto-promoted from a session envelope, not a unit of work; no contract scope (claude@myworld triage 2026-05-18)
---

# ASC-0199 Aios Session

## Why Now

This proposed contract was promoted from a reviewed AIOS session envelope.

- session_envelope: `.aios/invocations/chat-6372babf0c9ebf88/session_envelope.json`
- promotion_receipt: `.aios/promotions/promotion-1d0db7e1e829-20260518T025653/promotion.json`
- dispatch_preview: `.aios/invocations/chat-6372babf0c9ebf88/dispatch/packets.json`

Operator must assign the final ASC id, narrow scope, accept the contract, and
dispatch through `scripts/aios_dispatch.py` before any executor work starts.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0199-aios-session.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- provider auth files
- child repo implementation files unless explicitly assigned

## AIOS Role Evidence

### MemoryOS

- context_pack: `.aios/invocations/chat-6372babf0c9ebf88/memory/context_pack.md`
- retrieval_trace: `rtrace_f53782fbdde10b82`
- accepted_memory_ids: `["mem_940ad99fcc2ed445", "mem_3af960f629693170", "mem_4a44670b379ca4ea", "mem_d0b64430dd5da2a8", "mem_5012d57c2c4acbf6", "mem_e4a9c7fe7d342598", "mem_001f6d5191fb8e51", "mem_70c8edbf4c5c9c7b", "mem_4f390c90de100dbf", "mem_61910dd09950fc81"]`
- signal_coverage: `0.0`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `.aios/invocations/chat-6372babf0c9ebf88/capability/route.json`
- recommended_tools: `pending_or_not_required`
- fallback_plan: `pending_or_not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `.aios/invocations/chat-6372babf0c9ebf88/genesis/branches.json`
- assumption_mutations: `pending_or_not_required`
- semantic_alignment_notes: `pending_or_not_required`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `.aios/invocations/chat-6372babf0c9ebf88/hive/execution_plan.json`
- provider_route: `pending_after_acceptance`
- verification_receipt: `pending_after_execution`
- degraded_or_fallback_receipt: `pending_if_triggered`

### 5-Persona Use

- Hive / Wrapper: `pending_after_acceptance` provider route or single-provider justification required before execution
- MemoryOS / Retriever: retrieval_trace `rtrace_f53782fbdde10b82`, signal_coverage: `0.0`
- CapabilityOS / Router: route `.aios/invocations/chat-6372babf0c9ebf88/capability/route.json`
- GenesisOS / Philosophy: branch_set `.aios/invocations/chat-6372babf0c9ebf88/genesis/branches.json`
- MyWorld / Sovereign: promotion receipt and operator acceptance are required before dispatch


## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `scope_not_narrowed_before_dispatch`
- `accepted_contract_missing`
- `dispatch_packet_missing_envelope_ref`
- `executor_runs_without_dispatch_packet`
