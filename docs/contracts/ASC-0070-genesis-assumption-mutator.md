---
contract_id: ASC-0070
slug: genesis-assumption-mutator
status: closed
goal: Add a GenesisOS mutator that takes any contract or memory record, enumerates its core assumptions, generates negations + dimensional rotations of each, and writes the resulting candidate-set as Genesis seeds for operator review.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: claude@myworld (operator) per founder "네가 판단" delegation 2026-05-13 KST. Founder declined to micromanage; operator pair authorized for batch decisions on this proposed queue.
origin: founder GenesisOS sub-contract sequence — "assumption mutation" is one of GenesisOS's 4 declared responsibilities (per AGENTS.md).
closed: 2026-05-15 KST by codex@myworld
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
- `GenesisOS/seeds/**`
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

- GenesisOS WP-0070-A implemented:
  - `GenesisOS/genesisos/mutator.py`
  - `GenesisOS/genesisos/cli.py`
  - `GenesisOS/tests/test_mutator.py`
  - `GenesisOS/docs/ASSUMPTION_MUTATION.md`
  - `GenesisOS/seeds/2026-05-15/*.json` sample append-only candidate seeds
- MyWorld WP-0070-B implemented:
  - `scripts/aios_genesis_mutate.py`
  - `tests/test_aios_genesis_mutate.py`
- Verification:
  - `cd GenesisOS && python -m pytest tests/test_mutator.py -v` passed 9/9.
  - `python -m genesisos.cli mutate --record /tmp/sample_contract.md --json` emitted six candidate seeds; rerun returned six `skipped_existing` write actions with stable seed ids.
  - `cd GenesisOS && python -m unittest tests/test_critic.py tests/test_cli.py tests/test_mutator.py` passed 17/17.
  - `python -m unittest tests/test_aios_genesis_mutate.py` passed 2/2.
  - `python scripts/aios_genesis_mutate.py --contract-id ASC-0050 --json` emitted six candidate seeds under `.aios/genesis_seed_inbox/asc-0050-68764cf9b6cf`.
  - `python scripts/aios_genesis_mutate.py --contract-id ASC-0070 --json` emitted six candidate seeds under `.aios/genesis_seed_inbox/`.
  - `ls .aios/genesis_seed_inbox/ | head -3` showed `asc-0070-a002cd50ba64`.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 346/346.
  - `python scripts/aios_monitor.py assess --json` completed with `health=attention`; findings were dirty-worktree triage for unrelated `hivemind` changes, scoped GenesisOS ASC-0070 work, and an advisory persona-axis review.

## Work Packets

### WP-0070-A — codex@GenesisOS implements mutator

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed.

### WP-0070-B — codex@myworld dispatch wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0070-A
