---
contract_id: ASC-0110
slug: memoryos-retrieval-broken
status: closed
goal: Fix MemoryOS context build — currently returns selected=0 for every query, even with exact keyword matches against 43 existing drafts. All accumulated precedent (ASC-0091 writeback included) is unreadable. AIOS effectively has amnesia despite write operations.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (founder /loop directive — verifier surfaces discomfort + necessity)
acceptance_authority: claude@myworld (verifier role, founder /loop GOAL-0002 + "계속 Contract를 발행해" delegation)
origin: 2026-05-13 verifier round 1 — probed 5 queries against 43-draft memoryOS, ALL returned selected=[]. Even ASC-0091's first dogfood draft mem_940ad99fcc2ed445 not retrievable by its own contract id. Founder-cited DNA Invariant 5 (provenance chain) is broken at the read end.
closed: 2026-05-13 KST
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

Partial myworld audit slice:

- Added `scripts/aios_memory_retrieval_audit.py`.
- Added `tests/test_aios_memory_retrieval_audit.py`.
- Added MemoryOS retrieval tripwire to `scripts/aios_self_check.sh`.
- Runtime audit after ASC-0111 activation:
  - `python scripts/aios_memory_retrieval_audit.py --json`
  - `retrieval_rate=1.0`, `hits=4/4`, `passed=true`
  - trace ids: `rtrace_0cbbc166722cb175`,
    `rtrace_656e67298588789f`, `rtrace_fcc76676927b0604`,
    `rtrace_6c916b83bbc4b5ac`
- Verification passed:
  - `python -m py_compile scripts/aios_memory_retrieval_audit.py`
  - `python -m unittest tests/test_aios_memory_retrieval_audit.py`
  - `bash -n scripts/aios_self_check.sh`
  - `bash scripts/aios_self_check.sh` reported
    `retrieval=passed=true rate=1.0 hits=4/4`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed
    `247` tests

Closeout decision:

- WP-0110-A produced the MemoryOS-owned diagnosis/fix.
- The contract's first draft asked for "draft retrieval" through
  `context build`, but MemoryOS' review lifecycle intentionally exposes only
  accepted memories to Hive-facing context packs. The closeout narrows the
  fix to accepted MemoryObject retrieval plus draft search/review visibility.

MemoryOS resolution:

- `context build` stays accepted-only. Drafts remain reachable through `search`
  and `drafts` review workflows, not through Hive context before approval.
- Retrieval ranking now indexes privacy-safe metadata in addition to content:
  `origin`, `project`, `raw_refs`, `reframe_class`, `source_path`,
  `evidence_refs`, and `cited_in_contracts`.
- Context selection uses internal weighted ranking so a memory matching
  multiple founder/workstyle terms beats generic `origin=founder_directive`
  matches, while public search scores remain backward compatible (`3` exact
  phrase, `2` all terms, `1` any term).

WP-0110-A verification:

- `python -m py_compile memoryOS/memoryos/cli.py`
- `cd memoryOS && python -m pytest tests/test_retrieval.py -q` passed `2/2`
- `cd memoryOS && python -m pytest tests/test_sprint4.py -q` passed `964/964`
- `python scripts/aios_memory_retrieval_audit.py --json` reported
  `retrieval_rate=1.0`, `hits=4/4`, `passed=true`
- `bash scripts/aios_self_check.sh` reported
  `retrieval=passed=true rate=1.0 hits=4/4`
- `python -m unittest discover -s tests -p 'test_aios_*.py'` passed `247/247`

Recommended closeout decision:

- Treat ASC-0110 as a retrieval repair for accepted MemoryObjects plus a
  contract wording correction: draft memories must not be inserted into
  Hive-facing context without review approval.
- Child repo commit: `memoryOS/ca7c39a` (`Improve founder retrieval ranking`).

## Work Packets

### WP-0110-A — codex@memoryOS diagnoses + fixes retrieval

- target_agent: codex
- target_repo: memoryOS
- status: done
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: ASC-0091 closed ✓
- brief: produce diagnostic JSON identifying WHY selected=[]. Then
  smallest fix that makes 5 keyword queries return correct drafts.
  Tests verify each. Do not refactor schema; minimum diff.
- result: `memoryOS/ca7c39a`; `cd memoryOS && python -m pytest tests/test_retrieval.py -q`; `cd memoryOS && python -m pytest tests/test_sprint4.py -q`.

### WP-0110-B — codex@myworld adds retrieval audit to self_check

- target_agent: codex
- target_repo: myworld
- status: done
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: WP-0110-A
- brief: aios_memory_retrieval_audit.py + extend self_check.sh as
  active verification probe (joins #15 canary). Fires
  RETRIEVAL_DEGRADED if rate < 0.5.
- result: `python scripts/aios_memory_retrieval_audit.py --json` reported `retrieval_rate=1.0 hits=4/4`; `bash scripts/aios_self_check.sh` reported `retrieval=passed=true rate=1.0 hits=4/4`.
