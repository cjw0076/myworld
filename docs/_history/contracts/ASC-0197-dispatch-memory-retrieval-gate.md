---
contract_id: ASC-0197
slug: dispatch-memory-retrieval-gate
status: closed
goal: Make MemoryOS retrieval trace evidence mandatory and visible for dispatch work that declares it required.
created: 2026-05-18 01:20 KST
accepted: 2026-05-18 KST
closed: 2026-05-18 01:22 KST
acceptance_authority: codex@myworld acting operator under continuous AIOS completion goal; triggered by persona audit retriever_score=0.0.
session_envelope_required: true
memory_retrieval_required: true
proposed_by: codex@myworld
---

# ASC-0197 Dispatch Memory Retrieval Gate

## Why

The monitor's 5-persona advisory repeatedly reported:

- `retriever_score: 0.0`
- recommendation: cite a MemoryOS `rtrace_...` and positive
  `signal_coverage` before execution.

AIOS already had `aios_invoke.py` and session envelopes, but dispatch did not
enforce them. That meant contracts could say "use MemoryOS" while packets
still reached executors without a concrete MemoryOS retrieval trace.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0197-dispatch-memory-retrieval-gate.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- raw exports
- private runtime auth files
- child repo implementation files

## AIOS Role Evidence

### MemoryOS

- context_pack:
  `.aios/invocations/inv-454672af7ad3-20260518T012019/memory/context_pack.md`
- retrieval_trace: `rtrace_b70da6ffc87b1f90`
- accepted_memory_ids:
  `["mem_5012d57c2c4acbf6", "mem_d0b64430dd5da2a8", "mem_e4a9c7fe7d342598", "mem_3af960f629693170", "mem_4a44670b379ca4ea", "mem_561d7633490e0f56", "mem_0c3b41fd22b1d801", "mem_4ec54ac7409828c8", "mem_940ad99fcc2ed445", "mem_001f6d5191fb8e51"]`
- signal_coverage: `1.0`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `.aios/invocations/inv-454672af7ad3-20260518T012019/capability/route.json`
- top route: `cap_memoryos_context_build`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `.aios/invocations/inv-454672af7ad3-20260518T012019/genesis/branches.json`
- authority: `advisory_only`

### Hive Mind

- execution_plan:
  `.aios/invocations/inv-454672af7ad3-20260518T012019/hive/execution_plan.json`
- provider_route: `single-provider implementation in myworld dispatch code; child execution not required`
- verification_receipt: local unit tests

## Implementation

`scripts/aios_dispatch.py` now supports two frontmatter gates:

- `session_envelope_required: true`
- `memory_retrieval_required: true`

When enabled:

- dispatch without a session envelope is held with
  `session_envelope_required_missing`;
- degraded session-envelope roles are held with
  `session_envelope_role_degraded`;
- missing or non-positive MemoryOS retrieval evidence is held with
  `memory_retrieval_required_missing`;
- sent packets include `session_envelope.memory_context` with
  `context_pack`, `retrieval_trace`, and `signal_coverage`.
- `scripts/aios_persona_audit.py` now recognizes Markdown-backticked
  signal coverage evidence so the monitor sees the trace evidence
  contracts already contain.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py
python -m unittest tests.test_aios_dispatch -v
python -m py_compile scripts/aios_persona_audit.py
python -m unittest tests.test_aios_persona_audit -v
git diff --check -- scripts/aios_dispatch.py tests/test_aios_dispatch.py
```

Pass criteria:

- A contract with `session_envelope_required: true` cannot send without an
  envelope.
- A contract with `memory_retrieval_required: true` sends only when the
  envelope's MemoryOS context pack contains `trace_id: rtrace_...` and positive
  `signal_coverage`.
- The resulting packet exposes the trace evidence to downstream workers.

## Stop Conditions

- Dispatch can still send a memory-required contract without `rtrace_...`.
- Dispatch can still send when `signal_coverage` is missing or zero.
- The implementation reads outside `.aios/invocations`.
- Existing dispatch tests regress.

## Result

Closed. Verification passed:

- `python -m py_compile scripts/aios_dispatch.py`
- `python -m unittest tests.test_aios_dispatch -v` -> 26 passed
- `python -m py_compile scripts/aios_persona_audit.py`
- `python -m unittest tests.test_aios_persona_audit -v` -> 4 passed
- persona audit recheck: ASC-0197 now scores `retriever_score=1.0`
- `git diff --check -- scripts/aios_dispatch.py tests/test_aios_dispatch.py`
