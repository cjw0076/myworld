---
contract_id: ASC-0258
slug: serving-design-gate
status: closed
goal: Make the Product Design prerequisite for the first end-user serving surface machine-checkable before any apps/serving UI build starts.
created: 2026-06-13T19:21:00+09:00
accepted: 2026-06-13T19:21:00+09:00
closed: 2026-06-13T19:23:00+09:00
human_approved: true
origin: ASC-0253 is the next world-readiness action, but Product Design rules prohibit UI implementation until the product brief, visual target, and interactivity level are confirmed.
---

# ASC-0258 Serving Design Gate

## Why Now

AIOS world readiness still stops at:

```text
end_user_serving_readiness=partial
next_action=ASC-0253
```

ASC-0253 cannot be accepted as an implementation contract while the Product
Design brief is missing. This contract turns that missing context into a
machine-checkable gate, so future agents do not rely on chat memory or make up
a visual direction.

This contract does not implement `apps/serving/`, generate visuals, or start a
browser/server. It only defines and verifies the prerequisite artifact.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_serving_design_gate.py`
- `scripts/aios_world_readiness.py`
- `tests/test_aios_serving_design_gate.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0258-serving-design-gate.md`
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

## Required Work

1. Add a CLI that validates an AIOS serving design gate artifact.
2. The artifact must require:
   - product/workflow goal;
   - visual target type and source or explicit `needs_ideation`;
   - interactivity level;
   - user confirmation;
   - stop condition names.
3. Missing or incomplete artifacts must return `ready=false` in JSON mode.
4. Complete artifacts must return `ready=true` but must not mark world
   deployment ready by themselves.
5. World readiness should show the gate script as serving partial evidence.
6. Add focused tests.

## AIOS Role Evidence

### MemoryOS

- context_pack: ASC-0253 proposed scope and Product Design get-context
  preflight result (`user-context.md` missing).
- retrieval_trace: local repo and Product Design skill inspection.
- accepted_memory_ids: pending_or_not_required.
- draft_memory_policy: no memory acceptance in this contract.

### CapabilityOS

- route: myworld serving readiness gate.
- recommended_tools: unit tests, py_compile, world-readiness JSON, diff check.
- fallback_plan: if UI work is requested before gate readiness, hold at
  Product Design question mode.
- authority: execute_with_receipt inside allowed files.

### GenesisOS

- branch_set: "invent UI from prose" versus "make missing design context
  explicit".
- assumption_mutations: a confirmed brief is not a visual target; `needs_ideation`
  is a valid intermediate state.
- semantic_alignment_notes: a service product needs an inspectable user-facing
  design target before implementation.
- authority: advisory only.

### Hive Mind

- execution_plan: Codex implements a local gate and tests.
- provider_route: `codex@myworld` for control-plane readiness code.
- verification_receipt: unit tests, py_compile, readiness JSON, diff check.
- degraded_or_fallback_receipt: required if tests cannot run.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_serving_design_gate tests.test_aios_world_readiness -v
python3 -m py_compile scripts/aios_serving_design_gate.py scripts/aios_world_readiness.py
python3 scripts/aios_serving_design_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Stop Conditions

- `apps_serving_modified`
- `ui_built_without_visual_target`
- `design_gate_claims_world_ready`
- `private_design_reference_logged`

next: after the operator provides or confirms the serving design gate, ASC-0253
can proceed to ideation or implementation according to Product Design rules.

## Result Packet

schema_version: `aios.result_packet.v1`
contract_id: `ASC-0258`
dispatch_id: `asc-0258`
repo: `myworld`
agent: `codex@myworld`
status: `passed`

changed:

- `scripts/aios_serving_design_gate.py`
- `scripts/aios_world_readiness.py`
- `tests/test_aios_serving_design_gate.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0258-serving-design-gate.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

evidence:

- Product Design user-context preflight reported `exists=false`.
- `python3 -m unittest tests.test_aios_serving_design_gate tests.test_aios_world_readiness -v` passed 15/15.
- `python3 -m py_compile scripts/aios_serving_design_gate.py scripts/aios_world_readiness.py` passed.
- `python3 scripts/aios_serving_design_gate.py assess --root . --json` reports `ready=false`, `status=missing`, and `next_action=product_design_get_context`.
- `python3 scripts/aios_world_readiness.py --json` still reports `ready_for_world_deployment=false`, `met_count=7`, `partial_count=1`, and `next_action=ASC-0253`.
- `git diff --check` passed.

implemented:

- `aios.serving_design_gate.v1` assessment for product goal, visual target,
  interactivity level, user confirmation, build allowance, and stop conditions.
- JSON inspection returns exit 0 even when the gate is missing; text mode returns
  nonzero when not ready.
- World-readiness serving axis now lists the design gate script as partial
  evidence without allowing it to satisfy world readiness.

remaining_gaps:

- The actual `.aios/serving/design_gate.json` artifact is missing because the
  user has not confirmed the Product Design brief/visual target/interactivity
  level.
- `apps/serving/` and browser proof remain unimplemented by design.
