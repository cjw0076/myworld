---
contract_id: ASC-0070
slug: genesis-assumption-mutator
status: proposed
goal: Add a GenesisOS mutator that takes any contract or memory record, enumerates its core assumptions, generates negations + dimensional rotations of each, and writes the resulting candidate-set as Genesis seeds for operator review.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: pending founder GO.
origin: founder GenesisOS sub-contract sequence — "assumption mutation" is one of GenesisOS's 4 declared responsibilities (per AGENTS.md).
---

# ASC-0070 Genesis Assumption Mutator

## Why Now

Most agent failures aren't logic errors — they're unexamined assumptions.
A contract assumes "user is technical", "all data fits in memory", "this
is a one-shot task". The mutator surfaces those assumptions and generates
their negation + orthogonal rotations so the operator can see the
assumption-space, not just the chosen point.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/mutator.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_mutator.py`
- `GenesisOS/docs/ASSUMPTION_MUTATION.md`
- `scripts/aios_genesis_mutate.py`
- `tests/test_aios_genesis_mutate.py`
- `docs/contracts/ASC-0070-genesis-assumption-mutator.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.mutator.Mutator` exposing:
  - `extract_assumptions(record) → list[Assumption]`
  - `negate(Assumption) → Assumption` (boolean inversion)
  - `rotate(Assumption, axis) → Assumption` (orthogonal: scale,
    audience, time, risk, modality)
  - `generate_seeds(record, axes=["negate","scale","audience","time","risk","modality"]) → list[Seed]`
- A `Seed` is `{seed_id, source_record_id, assumption_changed, rotation_axis,
  proposed_alternate, rationale, status: candidate}`.
- Seeds are stored append-only under `GenesisOS/seeds/<date>/<seed_id>.json`.
- `genesisos cli mutate --record <path> --json` prints generated seeds.

### myworld.must_produce

- `scripts/aios_genesis_mutate.py` — wrapper that takes a contract id,
  pulls the contract file, calls mutator, writes seeds to
  `.aios/genesis_seed_inbox/<batch>/`. Operator reviews via existing
  `aios_primitives task` queue or manually.
- Test for the wrapper.

### Hive / Memory / Capability

- No source change. Memory may import accepted seeds as draft observations
  in a future contract — out of scope here.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_mutator.py -v
python -m genesisos.cli mutate --record /tmp/sample_contract.md --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_mutate.py
python scripts/aios_genesis_mutate.py --contract-id ASC-0050 --json
ls .aios/genesis_seed_inbox/ | head -3
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Mutator returns ≥6 seeds (one per axis) for a non-trivial input.
- Each seed cites which assumption was changed.
- Append-only — re-running same record produces same seed_ids.
- Recommendation only — no mutation of source records.

## Stop Conditions

- `mutator_modifies_source_record`
- `mutator_creates_contract`: seeds remain seeds; promotion to contract
  is a separate operator action.
- `seed_silent_drop`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0070-A — codex@GenesisOS implements mutator

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed.

### WP-0070-B — codex@myworld dispatch wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0070-A
