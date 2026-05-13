---
contract_id: ASC-0092
slug: hive-context-binding
status: proposed
goal: Make every Hive deliberation receive a MemoryOS context_build result as required reading so Hive doesn't keep deliberating in isolation. Fixes founder-verified gap: ASC-0084 DNA debate cited 0 mem_/trace_id references.
created: 2026-05-13 KST
proposed_by: claude@myworld (operator)
acceptance_authority: pending founder GO.
origin: founder Q3 verification 2026-05-13 KST — "memoryOS 참고해서 hive가 토론 진행했는가?" Answer was NO: ASC-0084 synthesis docs cite 0 mem_*/trace_id references. Hive deliberated in isolation despite memoryOS having 34 accepted drafts.
---

# ASC-0092 Hive Context Binding (memoryOS → Hive deliberation)

## Why Now

ASC-0084 DNA debate ran 5 rounds with 3 voices. Output: 8-invariant
DNA spec with preamble + interaction map + amendment clause.
Substantial work. But the synthesis docs cite ZERO `mem_*` or
`trace_id` references — Hive deliberated using only the contract body
+ training-data prior, ignoring 34 already-accepted memoryOS drafts.

This is a systemic gap: Hive contracts (ASC-0084, ASC-0089, future)
should always start by pulling MemoryOS context relevant to the topic.
Otherwise Hive re-derives from scratch and loses prior accepted
learnings.

ASC-0092 adds a required-reading bootstrap: every Hive contract's
verification gate runs `memoryos context build --task "<contract goal>"`
first, attaches the result to the run's `round_0/context.md`, and
each agent voice must cite at least one memory reference per round
(or explicitly note "no relevant accepted memory found").

## Scope

repos: `myworld`, `memoryOS`, `hivemind`

allowed_files:

- `scripts/aios_hive_context_bootstrap.py`
- `tests/test_aios_hive_context_bootstrap.py`
- `hivemind/hivemind/hive.py` (only if context-build hook needed)
- `hivemind/tests/test_hive_context_binding.py`
- `docs/AIOS_HIVE_CONTEXT.md`
- `docs/contracts/ASC-0092-hive-context-binding.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/memoryos/**` (only test additions allowed)
- `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_hive_context_bootstrap.py`: given a contract id, calls
  `memoryos context build --task "<goal>"` and writes result to
  `hivemind/.runs/<run_id>/round_0/context.md`. Includes a citation
  block: trace_id, selected memory ids, top retrieval scores.
- Pre-dispatch hook: when an ASC dispatches to hivemind, this script
  runs first. The dispatch packet's `required_reading` includes the
  context.md path.
- Tests: synthetic contract → bootstrap produces context.md with
  citations.

### memoryOS.must_produce

- No source change unless `context build --task` doesn't already
  support the use case (verify first; add only if needed).

### hivemind.must_produce

- Each Hive agent voice (proposer/critic/extender) must cite at least
  one memoryOS reference per round, or explicitly note
  `no_relevant_accepted_memory`. Enforced by Hive contract template
  + verification gate.

## Verification Gate

```bash
python -m unittest tests/test_aios_hive_context_bootstrap.py
python scripts/aios_hive_context_bootstrap.py --contract ASC-0084 --json
test -f hivemind/.runs/aios_dna_debate/round_0/context.md   # retro-fit test
grep -c "mem_\|trace_id" hivemind/.runs/<latest_hive_run>/round_*/synthesis.md   # ≥1 per round
python -m unittest discover -s tests -p 'test_aios_*.py'
```

## Stop Conditions

- `context_silent_empty`: bootstrap produces empty context.md without
  noting why
- `cite_skipped_silently`: hive synthesis doc has 0 memoryOS refs and
  no `no_relevant_accepted_memory` note
- `context_grows_unbounded`: context.md > 10k tokens (truncate or
  summarize)
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.
