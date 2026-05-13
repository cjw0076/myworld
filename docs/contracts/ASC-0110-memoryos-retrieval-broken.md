---
contract_id: ASC-0110
slug: memoryos-retrieval-broken
status: accepted
goal: Fix MemoryOS context build — currently returns selected=0 for every query, even with exact keyword matches against 43 existing drafts. All accumulated precedent (ASC-0091 writeback included) is unreadable. AIOS effectively has amnesia despite write operations.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (founder /loop directive — verifier surfaces discomfort + necessity)
acceptance_authority: claude@myworld (verifier role, founder /loop GOAL-0002 + "계속 Contract를 발행해" delegation)
origin: 2026-05-13 verifier round 1 — probed 5 queries against 43-draft memoryOS, ALL returned selected=[]. Even ASC-0091's first dogfood draft mem_940ad99fcc2ed445 not retrievable by its own contract id. Founder-cited DNA Invariant 5 (provenance chain) is broken at the read end.
---

# ASC-0110 MemoryOS Retrieval Broken

## Why Now (verifier discomfort)

Verified 2026-05-13 by direct probe:

```
context build "DNA invariants"          → selected=[]
context build "Hive deliberation"       → selected=[]
context build "founder GO"              → selected=[]
context build "Genesis stub"            → selected=[]
context build "provider fallback"       → selected=[]
context build "ASC-0091 contract..."    → selected=[]  (own dogfood draft!)
```

43 drafts in MemoryOS. 0 retrievable.

**Implication for AIOS-as-Government**:
- DNA Invariant 5 (provenance chain) requires `derives_from / evidence_refs`
  to actually be CONSUMED later, not just written.
- ASC-0091 (memoryos auto-writeback) closed and produces drafts — but
  drafts that nobody can find are no different from no drafts.
- claude operator's 4-OS query pattern (memory:trace selected=0) has
  been silently meaningless this entire session.
- All precedent accumulated since 2026-05-11 = 0% effective value.

**Discomfort**: a write-only memory is theater. AIOS has been claiming
"learning" while actually building a black hole.

## Required Reading

- `memoryOS/memoryos/cli.py` `context build` implementation
- `memoryOS/memoryos/store.py` (search/retrieval logic)
- `memoryOS/docs/AGENT_WORKLOG.md`
- `docs/AIOS_DNA.md` (after ASC-0105) — Invariant 5
- `docs/contracts/ASC-0091-memoryos-auto-writeback.md`

## Scope

repos: `memoryOS`, `myworld`

allowed_files:

- `memoryOS/memoryos/store.py`
- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/retrieval.py` (NEW if extraction warranted)
- `memoryOS/tests/test_retrieval.py`
- `memoryOS/tests/test_context_build.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `scripts/aios_memory_retrieval_audit.py`
- `tests/test_aios_memory_retrieval_audit.py`
- `docs/contracts/ASC-0110-memoryos-retrieval-broken.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/memory/processed/**` (read-only — actual stored content)
- `memoryOS/ontology/**` (read-only)
- `hivemind/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### memoryOS.must_produce

Diagnose first (V1 of contract is to FIND the bug, V2 to FIX):

- WHY is selected always empty:
  - Token mismatch? (drafts indexed by token X, query tokenized as Y)
  - Status filter? (only `accepted` returned, all 43 are `draft`)
  - Project filter? (drafts tagged by project, query passes none)
  - Schema mismatch between draft and query expectations
  - Or a bug in retrieval ranking
- Output diagnostic JSON: `{drafts_total, drafts_searchable, query_pipeline_steps[], drop_at_stage}`
- THEN fix: minimum mod that makes correct keyword query return correct draft
- Tests:
  - 1 draft with body "X" → context build for "X" returns it
  - 1 draft tagged project=AIOS → context build with project=AIOS returns it
  - Tokenization respects unicode (Korean queries should match Korean drafts if any)

### myworld.must_produce

`scripts/aios_memory_retrieval_audit.py`:

- runs N synthetic queries against current memoryOS
- reports retrieval rate (queries returning ≥1 result / total queries)
- baseline: today = 0/N. Goal after fix: ≥80%.
- runs as part of self_check.sh going forward

### child repos: no other change

## Verification Gate

```bash
cd memoryOS
python -m unittest tests/test_retrieval.py tests/test_context_build.py -v
python -m memoryos --root . context build --task "ASC-0091" --json | python -c "
import json,sys; d=json.load(sys.stdin)
ids = d.get('selected_memory_ids',[])
assert len(ids) > 0, f'still broken — selected={ids}'
print(f'OK retrieved {len(ids)} drafts'); print(ids)
"
cd ..
python -m py_compile scripts/aios_memory_retrieval_audit.py
python -m unittest tests/test_aios_memory_retrieval_audit.py
python scripts/aios_memory_retrieval_audit.py --json | python -c "
import json,sys; d=json.load(sys.stdin)
rate = d.get('retrieval_rate', 0)
assert rate >= 0.5, f'retrieval rate {rate} < 0.5 floor'
print(f'OK retrieval_rate={rate}')
"
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria (DNA-cited):

- DNA Invariant 5 (provenance chain) — drafts retrievable by their
  own evidence_refs / derives_from terms
- Audit shows ≥50% retrieval rate (improvement from 0%)
- ASC-0091 dogfood draft `mem_940ad99fcc2ed445` retrievable by query
  containing "ASC-0091" or "contract closeout"
- Diagnostic JSON identifies the drop_at_stage clearly (audit value)

## Stop Conditions

- `retrieval_modifies_drafts`: fix must be search-side, not draft mutation
- `retrieval_silent_pass_zero`: tests must reject 0-result results, not
  treat as success
- `retrieval_breaks_existing_drafts`: existing 43 drafts must remain
  intact and now searchable, not be re-indexed destructively
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending. (And ASC-0110's own writeback when closed will test if writeback
+ retrieval finally compose end-to-end.)

## Work Packets

### WP-0110-A — codex@memoryOS diagnoses + fixes retrieval

- target_agent: codex
- target_repo: memoryOS
- depends_on: ASC-0091 closed ✓
- brief: produce diagnostic JSON identifying WHY selected=[]. Then
  smallest fix that makes 5 keyword queries return correct drafts.
  Tests verify each. Do not refactor schema; minimum diff.

### WP-0110-B — codex@myworld adds retrieval audit to self_check

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0110-A
- brief: aios_memory_retrieval_audit.py + extend self_check.sh as
  active verification probe (joins #15 canary). Fires
  RETRIEVAL_DEGRADED if rate < 0.5.
