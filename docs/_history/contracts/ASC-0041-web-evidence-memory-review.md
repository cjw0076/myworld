---
contract_id: ASC-0041
slug: web-evidence-memory-review
status: closed
goal: Turn validated web evidence receipts into MemoryOS draft review candidates without auto-accepting web-derived facts.
created: 2026-05-12 18:41 KST
accepted: 2026-05-12 18:41 KST by codex acting operator
closed: 2026-05-12 18:55 KST
---

# ASC-0041 Web Evidence Memory Review

## Why Now

ASC-0030 made broad web research a CapabilityOS route and ASC-0031 produced a
validated cited receipt. The missing loop is memory review: useful public web
evidence should become MemoryOS review candidates, but external claims must not
be silently accepted as durable memory.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_51c40c8d3d1eabdd`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_web_research_route`, `cap_memoryos_import_run`,
  `cap_hivemind_execution_harness`, `cap_memoryos_context_build`, and
  `cap_capabilityos_recommendation`.
- Hive Mind dry-run:
  `run_20260512_184108_174c71`, `route_source=heuristic_fast`, prepared
  planner/executor/reviewer artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_web_evidence_memory_review.py`
- `scripts/aios_dispatch.py`
- `tests/test_aios_web_evidence_memory_review.py`
- `tests/test_aios_dispatch.py`
- `docs/evidence/ASC-0041-web-evidence-memory-candidates.json`
- `docs/evidence/ASC-0041-web-evidence-review-run/run_state.json`
- `docs/evidence/ASC-0041-web-evidence-review-run/memory_drafts.json`
- `docs/evidence/ASC-0041-web-evidence-review-run/transcript.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0041-web-evidence-memory-review.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths
- browser caches or downloaded web archives

## Responsibilities

### myworld.must_produce

- A converter that validates an existing `aios.web_research_receipt.v1`
  receipt before producing memory review candidates.
- A candidate JSON envelope with `auto_accept=false`,
  `memoryos_target_status=draft`, `review_required=true`, and source
  provenance for every candidate.
- A Hive-run-compatible bundle containing `run_state.json`,
  `memory_drafts.json`, and a synthetic `transcript.md` so MemoryOS
  `import-run --dry-run --json` can verify the draft path.
- Tests proving the candidates stay draft-only and MemoryOS can plan import
  without accepting them.

### memoryos.must_produce

- No source change. Existing `import-run --dry-run --json` is the verification
  authority for the generated bundle.

### capabilityos.must_produce

- No source change. Existing recommendation-only `web-route` and
  `recommend` surfaces remain the route authority.

### hive_mind.must_produce

- No source change. Hive dry-run provides planning evidence; generated
  `memory_drafts.json` is intentionally compatible with the Hive-run import
  bridge.

## Verification Gate

```bash
python -m py_compile scripts/aios_web_evidence_memory_review.py scripts/aios_web_research_receipt.py
python scripts/aios_web_evidence_memory_review.py --root . validate docs/evidence/ASC-0041-web-evidence-memory-candidates.json --json
cd memoryOS && python -m memoryos.cli --root /home/user/workspaces/jaewon/myworld import-run /home/user/workspaces/jaewon/myworld/docs/evidence/ASC-0041-web-evidence-review-run --dry-run --json
python -m unittest tests/test_aios_web_evidence_memory_review.py tests/test_aios_web_research_receipt.py
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Source receipt validation must pass before candidate generation.
- Every candidate remains `status=draft`, `evidence_state=unreviewed`,
  `review_required=true`, and `auto_accept=false`.
- Every candidate has source IDs that resolve back to public source metadata in
  the receipt.
- MemoryOS `import-run --dry-run --json` returns `status=dry_run_ok` and plans
  three draft memory objects without writing accepted memory.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `receipt_validation_failed`
- `web_claim_without_source`
- `auto_accept_requested`
- `candidate_without_provenance`
- `absolute_or_raw_private_ref`
- `memoryos_import_dry_run_failed`
- `child_repo_source_edit`
- `dispatch_policy_false_positive`
- `verification_gate_failed`

## Receipts

- implementation:
  - `scripts/aios_web_evidence_memory_review.py` builds and validates
    `aios.web_evidence_memory_review.v1`.
  - `tests/test_aios_web_evidence_memory_review.py` covers draft-only
    candidates and MemoryOS import-run dry-run compatibility.
  - `scripts/aios_dispatch.py` no longer treats the words `web` or `public`
    alone as external side effects; `tests/test_aios_dispatch.py` covers
    local web-evidence review dispatch without a checkpoint.
  - `docs/evidence/ASC-0041-web-evidence-memory-candidates.json` contains
    three review candidates derived from
    `docs/evidence/ASC-0031-web-evidence.json`.
  - `docs/evidence/ASC-0041-web-evidence-review-run/` contains the
    Hive-run-compatible import bundle.
- dispatch evidence:
  - `asc-0041` sent to `myworld`, watched, collected, and released with reason
    `asc_0041_web_evidence_memory_review_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0041.myworld.result.json`.
- verification:
  - focused tests passed 9/9.
  - MemoryOS `import-run --dry-run --json` returned `status=dry_run_ok` and
    planned three memory objects.
  - full myworld suite passed 79/79.
  - final `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.

## Work Packets

### WP-0041-A — Codex@myworld builds web-evidence review candidates

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0031
- brief: |
    Validate the existing ASC-0031 web evidence receipt, emit MemoryOS
    draft-only review candidates with provenance, generate an import-run
    compatible bundle, and verify MemoryOS dry-run compatibility. Do not edit
    child repo source and do not auto-accept any web-derived fact.
- result: `.aios/outbox/myworld/asc-0041.myworld.result.json`;
  `docs/evidence/ASC-0041-web-evidence-memory-candidates.json`;
  `docs/evidence/ASC-0041-web-evidence-review-run/`; full tests passed 79/79;
  monitor clear.
