---
contract_id: ASC-0227
slug: autodraft-boundary-gate
status: closed
goal: Make contract autodrafts include the ASC-0226 boundary classifier output so autonomous goal evolution cannot draft execution scope without a substrate/surface/knowledge gate.
created: 2026-06-05T20:10:00+09:00
accepted: 2026-06-05T20:10:00+09:00
closed: 2026-06-05T20:13:00+09:00
origin: active autonomous-development goal after ASC-0226.
accepted_by: codex_delegated_operator
human_approved: false
---

# ASC-0227 Autodraft Boundary Gate

## Why Now

`ASC-0226` made the boundary rule callable, but autonomous contract drafting
still generated proposed contracts without including that classifier output.
This contract wires the classifier into autodraft so future goal-evolution
drafts carry boundary evidence by default.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_contract_autodraft.py`
- `tests/test_aios_contract_autodraft.py`
- `docs/AIOS_SUBSTRATE_BOUNDARY.md`
- `docs/contracts/ASC-0227-autodraft-boundary-gate.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials
- raw exports
- private history stores
- child repo implementation files
- CapabilityOS catalog edits
- Hive provider/process edits

## Required Work

- Add the boundary classifier output to every autodrafted contract body.
- Keep autodrafts `status: proposed`; do not auto-accept or dispatch.
- Test that generated bodies include:
  - `## Substrate / Surface / Knowledge Gate`
  - `schema_version: aios.boundary_classifier.v1`
  - authority
  - required receipts
- Preserve pre-existing dirty `uri` and runtime `artifacts/` state.

## Verification Gate

```bash
python -m unittest tests.test_aios_contract_autodraft tests.test_aios_boundary_classifier -v
python -m py_compile scripts/aios_contract_autodraft.py scripts/aios_boundary_classifier.py
python scripts/aios_monitor.py assess --json
git diff --check
```

Pass criteria:

- Focused tests pass.
- `scripts/aios_contract_autodraft.py` remains at or below 250 pure LOC.
- Autodrafted contracts include the boundary gate.
- No child repo implementation files are changed.

## Result

- `scripts/aios_contract_autodraft.py` imports the boundary classifier and
  renders a `Substrate / Surface / Knowledge Gate` section.
- `tests/test_aios_contract_autodraft.py` locks the gate into generated bodies.
- `docs/AIOS_SUBSTRATE_BOUNDARY.md` documents that autodraft now calls the
  classifier.

## Stop Conditions

- `autodraft_missing_boundary_gate`
- `autodraft_auto_accepts_contract`
- `boundary_classifier_bypassed`
- `child_repo_implementation_without_dispatch`
- `verification_gate_failed`
