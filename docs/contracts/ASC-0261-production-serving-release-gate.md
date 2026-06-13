---
contract_id: ASC-0261
slug: production-serving-release-gate
status: closed
goal: Add a machine-checkable production-serving release gate for the nine ASC-0260 slices so AIOS cannot become world-ready from prototype markers alone.
created: 2026-06-13T20:18:00+09:00
accepted: 2026-06-13T20:18:00+09:00
closed: 2026-06-13T20:18:00+09:00
human_approved: true
origin: ASC-0260 produced the owner-bound production-serving slice plan, but the world-readiness CLI still needed a release gate that evaluates those slices as evidence.
---

# ASC-0261 Production Serving Release Gate

## Decision

ASC-0260 is now executable as a gate, not just a planning record. A new
`scripts/aios_serving_release_gate.py` command evaluates the nine production
serving slices:

1. Product Design visual target.
2. End-user serving UI prototype.
3. `end_user_serving` runtime/session boundary.
4. Hivemind worker queue/resume.
5. MemoryOS per-user memory lifecycle.
6. CapabilityOS provider-access/rate/consent routing.
7. Observability/support redaction.
8. Release readiness gate.
9. GenesisOS pre-launch challenge.

`scripts/aios_world_readiness.py` now requires this release gate to be ready
before the `end_user_serving_readiness` axis can become `met`.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_serving_release_gate.py`
- `scripts/aios_world_readiness.py`
- `tests/test_aios_serving_release_gate.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0261-production-serving-release-gate.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/serving/**`
- child repo implementation files
- `CapabilityOS/**`
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Counter Branch

Counter-default option: add more marker paths directly to
`aios_world_readiness.py`.

Rejected. Plain marker expansion can be spoofed by a static prototype. The
release gate keeps each production slice named, owned, stop-conditioned, and
visible in JSON output.

## AIOS Role Evidence

### MemoryOS

- retrieval trace: `rtrace_d976099a83abec3d`
- relevant memory: production praxis should require explicit MemoryOS context
  and closeout evidence.

### CapabilityOS

- route: MyWorld operator control-plane gate; browser verification route remains
  future evidence for the UI slice.

### GenesisOS

- critique: prose-only closure is insufficient; use a machine-checkable schema
  and keep a counter-branch.

### Hive Mind

- no child execution in this contract. Hivemind owns a future worker queue and
  resume slice.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_serving_release_gate tests.test_aios_world_readiness -v
python3 -m py_compile scripts/aios_serving_release_gate.py scripts/aios_world_readiness.py
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected current state:

- production serving release gate is not ready;
- Product Design slice is partial because the visual target still needs
  ideation and `build_allowed=false`;
- world readiness remains `false`;
- no `apps/serving/**` implementation is created.

## Stop Conditions

- `prototype_claimed_as_world_ready`
- `infra_markers_sufficient_for_world_ready`
- `ui_implementation_before_visual_target`
- `child_repo_implementation_without_owner_contract`
- `raw_user_content_in_support_view`
- `provider_access_value_in_doc_prompt_or_log`
