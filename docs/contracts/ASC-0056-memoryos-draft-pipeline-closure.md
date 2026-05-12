---
contract_id: ASC-0056
slug: memoryos-draft-pipeline-closure
status: accepted
goal: Close the three open gaps in MemoryOS draft pipeline so accepted memory actually flows back into AIOS context: (a) memory_pulse can ingest current scout JSON, (b) drafts get auto-reviewed by local LLM proposal + operator approve, (c) accepted memory is verified to surface in next contract's required_reading.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated, founder directive "Gap 해소 다음 작업으로 잡아")
closed:
acceptance_authority: claude@myworld (operator) per founder request to issue all gap-fix contracts.
origin: claude diagnostic 2026-05-13 KST showing 34 drafts stuck in queue since 2026-05-11, memory_pulse warnings=4 (format mismatch), no draft→accepted transitions in 1.5 days.
---

# ASC-0056 MemoryOS Draft Pipeline Closure

## Why Now

Founder asked whether MemoryOS+CapabilityOS are actually working. Diagnosis:
CapabilityOS = working (31 observations, Beta confidence). MemoryOS = partial:
schema/draft queue intact (34 drafts) but three gaps:

1. `memory_pulse.sh` warnings=4 means scout output (`top_tasks` JSON) isn't
   properly converted to `ingest-doc-radar` input. New imports stuck at 0.
2. 34 drafts have been in `status: draft` for 1.5 days. Zero
   draft→accepted transitions. No review automation = pipeline dead-ends.
3. Even if drafts were accepted, no test verifies that accepted memory
   actually surfaces in the next contract's `required_reading` or
   MemoryOS context build.

## Scope

repos:

- `myworld`
- `memoryOS`

allowed_files:

- `scripts/aios_coevolution/memory_pulse.sh`
- `scripts/aios_memory_review_proposer.py`
- `tests/test_aios_memory_review_proposer.py`
- `tests/test_aios_accepted_memory_surfaces.py`
- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/importers.py`
- `memoryOS/tests/test_doc_radar_ingest.py`
- `docs/AIOS_MEMORY_REVIEW.md`
- `docs/contracts/ASC-0056-memoryos-draft-pipeline-closure.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `CapabilityOS/**`
- `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.aios/logs/**`, `.env`

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_coevolution/memory_pulse.sh` updated so scout `top_tasks` JSON
  is correctly fed into `ingest-doc-radar`. Pulse summary line now reports
  `imported>0` for fresh runs.
- `scripts/aios_memory_review_proposer.py` — reads N drafts from MemoryOS
  review queue, calls a LOCAL LLM (Ollama Qwen 2.5 7B if available, fallback
  to deterministic heuristic if not), proposes `accept | reject | needs_more_evidence`
  per draft with rationale ≤ 200 chars. **NEVER auto-applies**. Writes
  proposals to `.aios/memory_review_proposals/<batch_id>.json`. Operator
  approves/rejects via existing memoryos `drafts approve/reject` CLI.
- `tests/test_aios_memory_review_proposer.py` covers: proposer respects
  recommendation-only (never calls memoryos drafts approve directly),
  rationale ≤ 200 chars, batch idempotency.
- `tests/test_aios_accepted_memory_surfaces.py` end-to-end: create draft →
  approve → verify next `memoryos context build` query returns it.

### memoryOS.must_produce

- `memoryos ingest-doc-radar` accepts the current scout JSON shape
  (`top_tasks` top-level key) without warnings. Existing schema test extended.
- No source change beyond importer adapter + test.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
bash scripts/aios_coevolution/memory_pulse.sh   # imported>0 expected
python -m unittest tests/test_aios_memory_review_proposer.py tests/test_aios_accepted_memory_surfaces.py
cd memoryOS && python -m pytest tests/test_doc_radar_ingest.py -v
cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- memory_pulse reports `imported>0` for at least one run.
- Proposer creates a batch file, never calls drafts approve.
- E2E test proves accept → context build returns the memory.
- Full test suite green.

## Stop Conditions

- `proposer_auto_accept`: proposer calls `memoryos drafts approve` directly.
- `proposer_uses_remote_llm`: proposer calls external API (must be local-only).
- `import_skips_silently`: pulse reports imported=0 and warnings=0 simultaneously.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending until verification.

## Work Packets

### WP-0056-A — codex@myworld fixes import format + adds proposer

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: none
- brief: |
    Fix scout→ingest format in memory_pulse.sh. Add
    aios_memory_review_proposer.py + tests. Add E2E surface test.
    Local-LLM call falls back to deterministic heuristic if Ollama
    unreachable.
- result: pending

### WP-0056-B — codex@memoryOS adapts ingest schema

- target_agent: codex
- target_repo: memoryOS
- status: issued
- depends_on: WP-0056-A
- brief: |
    Make memoryos ingest-doc-radar accept current scout `top_tasks`
    shape without warnings. Extend regression test.
- result: pending
