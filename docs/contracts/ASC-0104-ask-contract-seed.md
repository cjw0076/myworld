---
contract_id: ASC-0104
slug: ask-contract-seed
status: closed
goal: Extend the AIOS ask interface so a one-line ask can also emit a proposed smart-contract seed for operator review, without bypassing acceptance, praxis, or dispatch gates.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder continuation
closed: 2026-05-13 KST
praxis_required: true
praxis_ref: docs/praxis/ASC-0104-ask-contract-seed.json
origin: follow-up after ASC-0103 ask interface
---

# ASC-0104 Ask Contract Seed

## Why Now

ASC-0103 created `bin/aios ask`, but ask output still stops at instruction and
praxis. The next useful interface step is a proposed contract seed. This seed
must remain proposed and non-executing until the operator narrows scope and
accepts it.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0104-ask-contract-seed.md`
- `docs/praxis/ASC-0104-ask-contract-seed.json`
- `scripts/aios_ask.py`
- `tests/test_aios_ask.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- UI application files

## Responsibilities

### myworld

must_produce:

- `python scripts/aios_ask.py "goal" --draft-contract --json`
- `.aios/asks/<ask_id>/contract_seed.md`
- contract seed frontmatter uses `contract_id: ASC-XXXX`
- contract seed frontmatter uses `status: proposed`
- contract seed includes `praxis_required: true`
- contract seed links back to ask instruction and praxis envelope

## Verification Gate

```bash
cd .
python -m unittest tests/test_aios_ask.py
python scripts/aios_work_praxis.py validate docs/praxis/ASC-0104-ask-contract-seed.json --json
python scripts/aios_ask.py "AIOS ask contract seed smoke" --write .aios/asks/asc-0104-smoke --draft-contract --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `ask_seed_auto_accepts_contract`
- `ask_seed_dispatches_work`
- `ask_seed_missing_praxis_required`
- `ask_seed_missing_operator_acceptance`
- `ask_seed_writes_child_repo_source`

## Receipts

- Implemented `scripts/aios_ask.py --draft-contract`.
- Ask receipts now include `artifact_paths.contract_seed` when a seed is
  requested.
- Contract seeds are written to `.aios/asks/<ask_id>/contract_seed.md`.
- Seeds use:
  - `contract_id: ASC-XXXX`
  - `status: proposed`
  - `praxis_required: true`
  - `praxis_ref: <ask praxis>`
- Updated `docs/AIOS_WORK_DISPATCH.md` to document ask contract seed usage.
- Verification passed:
  - `python -m unittest tests/test_aios_ask.py`
  - `python scripts/aios_work_praxis.py validate docs/praxis/ASC-0104-ask-contract-seed.json --json`
  - `python scripts/aios_ask.py "AIOS ask contract seed smoke" --write .aios/asks/asc-0104-smoke --draft-contract --json`
  - `python scripts/aios_monitor.py assess --json`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0104.myworld.result.json` passed.
