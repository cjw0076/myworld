---
contract_id: ASC-0126
slug: memoryos-retrieval-real-fix
status: closed
goal: Fix MemoryOS retrieval so `Agent(Retriever)` actually returns relevant accepted memories. ASC-0110 was closed but `selected=0` / `signal_coverage=0.0` persists across many traces. Without real retrieval, AIOS cognition has amnesia at every turn — the Retriever persona (per founder 2026-05-14 reframe) is structurally absent.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by claude@myworld (operator) per founder explicit GO "계약 우선순위대로 전달해" with C→D→B priority decision.
closed: 2026-05-14 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder explicit GO.
origin: verifier observed 2026-05-14 KST during 4-OS query for "post-AIOS architecture": `selected=0` (zero memories chosen) despite 101 drafts existing. Second probe for "AIOS founder operator pattern" returned `context_items=31, signal_coverage=0.0` — items pulled but scoring is dead. ASC-0110 marked closed without solving root cause (operator_session_log notes "fake-close"). Founder reframe makes this critical: MemoryOS = `Agent(Retriever)`, the persona that grounds Agent(Main) in user/project ontology. If Retriever fails, all other personas operate blind.
---

# ASC-0126 MemoryOS Retrieval Real Fix

## Why Now

The 2026-05-14 founder reframe sharpened the role: MemoryOS is
`Agent(Retriever)` — the persona that retrieves founder profile, current
project state, prior decisions, work-pattern ontology for Agent(Main) to
consume. Today this persona is structurally degraded:

Probes 2026-05-14 KST:

```
context build --task "post-AIOS architecture"      → selected=0
context build --task "AIOS founder operator pattern" → context_items=31, signal_coverage=0.0
```

`signal_coverage=0.0` is the load-bearing failure: items are pulled but the
ranking signal is dead, so Agent(Main) cannot trust which of 31 items are
relevant. Effective state = no retrieval.

ASC-0110 attempted to fix this. Its close receipt did not show
`selected > 0` on a regression test. Closed-without-evidence pattern
(documented in operator_session_log 2026-05-13).

This contract refuses any "close without selected>0 evidence" path.

DNA references: Invariant 1 (decide before acting — the prior close was
premature), Invariant 3 (no record destroyed — debug must not delete
drafts), Invariant 4 (named exit), Invariant 5 (provenance — every
retrieved item must cite scoring rationale), Invariant 8 (classify
before committing — scoring is classification).

## Required Reading

- `memoryOS/memoryos/context.py` (build pipeline + ranking)
- `memoryOS/memoryos/retrieval/` (whatever scoring lives here)
- `docs/contracts/ASC-0110-*.md` (prior attempt — diagnose what closed without working)
- `~/.claude/projects/.../memory/feedback_observation_vs_verification.md`
- Operator session log entry on ASC-0110 fake-close

## Scope

repos:

- `memoryOS`
- `myworld`

allowed_files:

- `memoryOS/memoryos/context.py`
- `memoryOS/memoryos/retrieval/**`
- `memoryOS/memoryos/scoring/**` (create if absent)
- `memoryOS/memoryos/cli.py`
- `memoryOS/scripts/retrieval_regression_probe.py`
- `memoryOS/tests/test_retrieval.py`
- `memoryOS/docs/RETRIEVAL.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0126-memoryos-retrieval-real-fix.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `myworld/**` source changes outside ASC-0126 closeout/index/ledger records
- `hivemind/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`
- Any deletion of existing draft / accepted memory records

## Per-OS Responsibility

### memoryOS.must_produce

Diagnose then fix. Three named pieces of evidence required:

1. **Root cause artifact** — `memoryOS/docs/RETRIEVAL.md` section explaining
   why `signal_coverage=0.0` happens today. Real source-quoted analysis, not
   speculation.

2. **Scoring fix** — actually make the ranking signal non-zero on real
   accepted memories. Allowed approaches (in preference order):
   a. Repair existing scoring (if it's a bug)
   b. Replace with deterministic local scorer (BM25/TF-IDF over indexed text)
   c. Last resort: add embedding scorer (must be local, no network)
   Whatever ships must be auditable — every score must trace to a formula.

3. **Regression test** — `test_retrieval.py` with concrete cases:
   - given known drafts {A, B, C} where A is on-topic for query Q
   - `context build --task Q` returns A in top-3 with score > 0
   - `signal_coverage > 0.0` on at least 3 distinct topics
   - cases derived from real existing accepted memories, not synthetic

### Hive / Capability / Genesis / myworld: no source change

## Verification Gate

```bash
cd memoryOS
python -m pytest tests/test_retrieval.py -v
python scripts/retrieval_regression_probe.py --task "AIOS founder operator pattern" --require-signal-positive --require-items-positive
python scripts/retrieval_regression_probe.py --task "GenesisOS prompt prison" --require-signal-positive
python scripts/retrieval_regression_probe.py --task "CapabilityOS router" --require-signal-positive --require-items-positive
python -m pytest
cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
```

The probe script is part of `must_produce` — it runs `context build`, parses
JSON, asserts `signal_coverage > 0` and `context_items > 0`, exits nonzero
on failure. Single executable per line so verification gate parser accepts.

Pass criteria:

- `signal_coverage > 0.0` on ≥3 distinct real queries
- regression test green (deterministic)
- no existing memory record deleted
- scoring rationale documented per item (provenance chain)

## Stop Conditions

- `selected_zero_persists`: cannot close while any test query returns selected=0
- `signal_coverage_zero_persists`: cannot close while signal_coverage=0.0
- `memory_record_destroyed`: scoring fix must not delete accepted drafts
- `remote_llm_v1`: deterministic local first; remote LLM scoring is later contract
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- MemoryOS commit `2aeae86 Fix retrieval signal coverage`.
- `.aios/outbox/memoryOS/asc-0126.memoryOS.result.json`
- `python -m pytest tests/test_retrieval.py -v` passed 3/3.
- `python scripts/retrieval_regression_probe.py --task "AIOS founder operator
  pattern" --require-signal-positive --require-items-positive` returned
  `context_items=31`, `signal_coverage=1.0`, trace
  `rtrace_32d7f5b15a175fa4`.
- `python scripts/retrieval_regression_probe.py --task "GenesisOS prompt
  prison" --require-signal-positive` returned `context_items=3`,
  `signal_coverage=1.0`, trace `rtrace_4ff57f350582bc41`.
- `python scripts/retrieval_regression_probe.py --task "CapabilityOS router"
  --require-signal-positive --require-items-positive` returned
  `context_items=26`, `signal_coverage=1.0`, trace
  `rtrace_447daede9b758410`.
- Full MemoryOS `python -m pytest` passed 2017/2017.
- MyWorld `python -m unittest discover -s tests -p 'test_aios_*.py'` passed
  304/304.

## Work Packets

### WP-0126-A — codex@memoryOS diagnoses + fixes retrieval

- target_agent: codex
- target_repo: memoryOS
- depends_on: none (ASC-0110 closed but evidence-thin — supersedes effectively)
- brief: write RETRIEVAL.md root-cause section, ship scoring fix
  (repair > deterministic > local-embedding in that preference order),
  add regression tests with real-memory cases, prove signal_coverage>0
  on 3+ queries. Refuse close if any probe still returns selected=0.
