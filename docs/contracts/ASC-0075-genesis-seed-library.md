---
contract_id: ASC-0075
slug: genesis-seed-library
status: accepted
goal: Build a curated, append-only seed library inside GenesisOS that captures wild ideas (from mutator, branches, analogies, operator dumps) BEFORE they pass any verification gate, so non-obvious thoughts are not silently filtered out by Hive's success criteria.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: claude@myworld (operator) per founder "네가 판단" delegation 2026-05-13 KST. Founder declined to micromanage; operator pair authorized for batch decisions on this proposed queue.
origin: founder directive on prompt-prison. Verification gates filter for "works now" — they suppress "interesting but risky" thoughts. Genesis must preserve those before they're evaluated, otherwise the AIOS converges back to the safe default.
---

# ASC-0075 Genesis Seed Library

## Why Now

AIOS verification gates (Hive run, capability audit, action policy)
optimize for "passes now". They filter out:

- Half-formed ideas
- Long-shot bets
- Counter-intuitive proposals
- Cross-frame insights that don't fit current schemas

Without a library that preserves these BEFORE they're filtered, the
loop converges to safe-default. GenesisOS needs an append-only seed
graveyard that operators can revisit when stuck — "what wild ideas did
we have that we let die?"

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/seeds/  (write-only, append)`
- `GenesisOS/genesisos/library.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_library.py`
- `GenesisOS/docs/SEED_LIBRARY.md`
- `scripts/aios_genesis_seed_capture.py`
- `tests/test_aios_genesis_seed_capture.py`
- `docs/contracts/ASC-0075-genesis-seed-library.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.library.Library` exposing:
  - `capture(text, source: operator|mutator|branches|analogy|critic,
            tags: [...], confidence: float | null) → Seed`
  - `list(tags=[], source=None, since=None) → list[Seed]`
  - `bury(seed_id, reason)` — soft delete (mark `buried=true`, never
    actually remove)
  - `revive(seed_id)` — unbury for reconsideration
- Seeds stored under `GenesisOS/seeds/YYYY-MM-DD/<seed_id>.json`,
  append-only, atomically.
- `genesisos cli library capture --text <file> --source operator --tags ...`
- `library list --tags x,y --json`
- `library random --n 5 --json` — surface 5 random seeds for
  serendipitous review.

### myworld.must_produce

- `scripts/aios_genesis_seed_capture.py` — wrapper for ad-hoc operator
  capture (e.g. claude noting an interesting thought during chat).
- Tests.

### Hive / Memory / Capability

- No source change. Future contract may import accepted seeds as
  capability cards or memory drafts — out of scope here.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_library.py -v
python -m genesisos.cli library capture --text /tmp/seed.md --source operator --tags test --json
python -m genesisos.cli library list --tags test --json
python -m genesisos.cli library random --n 5 --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_seed_capture.py
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Capture produces a seed file under `GenesisOS/seeds/<date>/`.
- List returns seeds matching tags.
- Random returns N distinct seeds.
- Bury / revive lifecycle correct (no actual deletion).

## Stop Conditions

- `seed_actual_delete`: bury must be soft only.
- `seed_modify_in_place`: append-only — no edits to existing seed file.
- `seed_silent_drop`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0075-A — codex@GenesisOS implements library

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed.

### WP-0075-B — codex@myworld capture wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0075-A
