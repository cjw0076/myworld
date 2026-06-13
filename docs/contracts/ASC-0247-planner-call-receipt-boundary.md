---
contract_id: ASC-0247
slug: planner-call-receipt-boundary
status: accepted
goal: Make AIOS head planning auditable by recording planner-call receipts before parsed steps are trusted or executed.
created: 2026-06-13T14:45:00+09:00
accepted: 2026-06-13T14:45:00+09:00
human_approved: true
closed:
origin: `1.md` product-kernel review: plan generation currently happens outside the auditable runtime evidence chain.
---

# ASC-0247 Planner Call Receipt Boundary

## Why Now

`aios_head.compile_goal()` asks a planner for a JSON step list, parses it, and
then validates the resulting ContractObject. That means the model/procedure
that created the plan is currently outside the auditable evidence chain.

For service readiness, the first decision point must be visible:

- what goal was planned;
- which planner/provider label was used;
- what authority context was shown;
- whether parsing succeeded or failed;
- whether the raw body was stored, redacted, hashed, or omitted;
- which ContractObject received the resulting steps.

This contract delegates implementation to Claude. Codex must not patch the
implementation in this slice.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_head.py`
- `scripts/aios_adapters.py`
- `scripts/aios_contract_object.py`
- `tests/test_aios_head.py`
- `tests/test_aios_adapters.py`
- `tests/test_aios_contract_object.py`
- `docs/contracts/ASC-0247-planner-call-receipt-boundary.md`
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
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work For Claude

Implement a narrow planner-call receipt boundary for the `aios_head` path.

Minimum requirements:

1. `compile_goal()` or an adjacent helper must record a planner receipt on the
   returned ContractObject before the planned steps are treated as trusted.
2. The receipt must include:
   - schema version;
   - contract id;
   - planner label or source;
   - workspace root;
   - write paths and network flag shown to the planner;
   - recalled memory count, not raw memory bodies;
   - parse status;
   - step count when parse succeeds;
   - raw planner body hash and length, not the raw body by default.
3. Parse failures must still produce a receipt-like diagnostic or structured
   exception payload so failed planning is not invisible.
4. Tests must prove:
   - successful fake planner call produces an auditable planner receipt;
   - raw planner text is not stored in the ContractObject receipt by default;
   - parse failure preserves a hash/length diagnostic;
   - memory inputs are counted without copying raw memory bodies into the
     planner receipt.

Do not implement unified provider adapters, turn-loop default routing, or new
remote/live provider behavior in this contract.

## Plain-Language Framing

AIOS should not quietly ask a model for a plan and then pretend the first
auditable event happened later. The plan itself is a decision. It needs a
receipt.

## Assumptions

- Assumption 1: planner output can be summarized by hash/length without storing
  raw model text in shared artifacts.
- Assumption 2: ContractObject receipts/evidence can carry a planner boundary
  record without granting execution authority.
- Assumption 3: this slice is about auditability, not changing provider routing.

Negated checks:

- Do not store raw planner output in committed docs or shared dispatch packets.
- Do not treat a successful planner receipt as proof the plan is authorized.
- Do not broaden filesystem or network authority.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_head tests.test_aios_adapters tests.test_aios_contract_object -v
python3 -m py_compile scripts/aios_head.py scripts/aios_adapters.py scripts/aios_contract_object.py
git diff --check
```

Pass criteria:

- Focused tests pass.
- Planner success and planner parse failure both leave auditable evidence.
- Raw planner body is hash/length summarized by default.
- No unrelated dirty paths are modified.

## AIOS Role Evidence

### MemoryOS

- source_context: `1.md` reviewed this as the next product-kernel evidence gap.
- privacy: memory bodies are counted or referenced, not copied into planner
  receipts.

### CapabilityOS

- route: local MyWorld head/adapters path only.
- authority: no capability binding changes.

### GenesisOS

- challenge: the plan is itself a decision and must not be invisible.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements; watcher verifies through focused tests and
  result packet.

## Work Packets

### WP-0247-A — Claude planner-call receipt boundary

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Implement the Required Work For Claude section. Keep the slice
  tight. Return a result packet with changed files, tests run, receipt fields,
  and remaining provider/kernel gaps.
- result: pending

## Stop Conditions

- `raw_planner_body_stored`
- `planner_failure_invisible`
- `authority_scope_broadened`
- `test_gate_failed`
- `scope_violation`
- `privacy_violation`
