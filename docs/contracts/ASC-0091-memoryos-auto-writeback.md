---
contract_id: ASC-0091
slug: memoryos-auto-writeback
status: proposed
goal: Make every contract closeout automatically generate a MemoryOS draft so the 80+ contracts being closed are reflected in memory, not silently lost. Fixes the founder-verified gap: 0 drafts in last 24h despite 80+ contracts active.
created: 2026-05-13 KST
proposed_by: claude@myworld (operator)
acceptance_authority: pending founder GO.
origin: founder Q2 verification 2026-05-13 KST — "memoryOS에 지금까지 작업 내용 반영되고있는가?" Answer was NO: 34 drafts all from 2026-05-11, last 24h = 0. Even though ASC-0056 is in flight to fix memory_pulse import format, the deeper gap is that contract closeouts don't trigger memory writes at all.
---

# ASC-0091 MemoryOS Auto-Writeback on Contract Closeout

## Why Now

Verified 2026-05-13 KST: 80+ contracts closed since 2026-05-11.
MemoryOS draft count grew by ZERO in the same period. memory_pulse
(ASC-0051) runs scout → ingest, but scout output doesn't include
contract closeout summaries — those live in commit messages + ledger
entries instead.

ASC-0091 adds an explicit contract-closeout hook: when `aios_dispatch.py
release` succeeds with status=closed, generate a MemoryOS draft that
captures the contract's outcome, evidence_refs, key learnings, and
substrate observations. Drafts go through normal memoryOS review
lifecycle (draft-first invariant intact).

This is complementary to ASC-0056 (which fixes scout-side ingest format)
— ASC-0091 is a different write path entirely.

## Scope

repos: `myworld`, `memoryOS`

allowed_files:

- `scripts/aios_dispatch.py` (release hook addition)
- `scripts/aios_contract_to_memory.py`
- `tests/test_aios_contract_to_memory.py`
- `memoryOS/memoryos/cli.py` (only if a new ingest subcommand needed)
- `memoryOS/tests/test_contract_closeout_ingest.py` (only if added)
- `docs/AIOS_MEMORY_AUTO_WRITEBACK.md`
- `docs/contracts/ASC-0091-memoryos-auto-writeback.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_contract_to_memory.py`: given a contract id, produces a
  MemoryOS-ingestible JSON with:
  - schema_version `aios.contract_closeout_memory.v1`
  - contract_id, slug, goal, closed_at, closed_by
  - evidence_refs (commit SHAs, result packets, discovery docs)
  - key_learnings (extracted from receipts section if present)
  - cross_references (other ASCs cited)
  - substrate_observations (which agent attempted, fallback used, etc.)
- `aios_dispatch.py release` extended: after successful release, calls
  `aios_contract_to_memory.py emit --contract <id>` and pipes into
  `memoryos ingest-contract-closeout` (new subcommand).
- New behavior is OPT-OUT via `--no-memory-write` flag (default ON
  once ASC-0091 closes; OFF until then).
- Tests cover: emit produces valid JSON, ingest produces draft,
  draft is queryable.

### memoryOS.must_produce

- `memoryos ingest-contract-closeout` subcommand consuming the new
  schema. Produces a `MemoryObject(type=decision, status=draft)`.
- Test for the subcommand.

## Verification Gate

```bash
python -m unittest tests/test_aios_contract_to_memory.py
python scripts/aios_contract_to_memory.py emit --contract ASC-0050 --json
cd memoryOS && python -m memoryos ingest-contract-closeout --json < /tmp/closeout.json
python -m memoryos drafts list --json | python -c "import json,sys; d=json.load(sys.stdin); assert any('ASC-0050' in str(x) for x in d), 'closeout draft missing'"
cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
```

## Stop Conditions

- `closeout_silent_skip`: release succeeds but no memory write
  attempted (must log skip reason if any)
- `closeout_auto_accept_memory`: drafts go to draft, never accepted
- `closeout_bypass_invariant_5`: every emitted draft must carry
  evidence_refs (DNA Inv 5 from ASC-0084)
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.
