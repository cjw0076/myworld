---
contract_id: ASC-0106
slug: aios-governance-audit
status: accepted
goal: Measure how much of AIOS's claimed governance actually functions — for each closed contract, score: (a) verification receipt depth, (b) DNA invariant citations, (c) Hive deliberation evidence, (d) dogfood proof, (e) cross-OS evidence. Surface 105-contract baseline so improvements can be measured.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder explicit GO sequence A→B→C→D)
acceptance_authority: claude@myworld (operator) per founder direct delegation.
origin: 2026-05-13 audit found only 33% of closed contracts have verification receipts, 3% cite DNA, 4% cite Hive verdict. Without measurement, AIOS keeps claiming governance while operating as worker template-fill.
---

# ASC-0106 AIOS Governance Audit

## Why Now

Verified 2026-05-13:
- 105 contracts, 82 closed (78%)
- 27/82 with verification receipt (33%)
- 3/105 cite DNA invariants
- 4/105 cite Hive verdict
- 18/82 with dogfood evidence
- 0 automatic regression verifications

**Diagnosis**: contract chain is active legislatively but underused
judicially. Constitution (DNA) is unused. Without measurement nothing
improves. Per founder discomfort observation — agents don't feel
inadequacy of perfunctory close.

## Founder Reframe Context

AIOS = Government. Government legitimacy depends on auditable
governance. ASC-0106 builds the audit primitive that exposes whether
AIOS-as-Government actually exists or is theater.

## Required Reading

- `docs/AIOS_DNA.md` (after ASC-0105 ships) or
  `hivemind/.runs/aios_dna_debate/final_state.md` (until ASC-0105 lands)
- `docs/AIOS_OPERATOR_PLAYBOOK.md`
- `scripts/aios_dna_lint.py` (after ASC-0105)
- `scripts/aios_monitor.py` (existing assessment surface)

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_governance_audit.py`
- `tests/test_aios_governance_audit.py`
- `docs/AIOS_GOVERNANCE_AUDIT.md`
- `docs/contracts/ASC-0106-aios-governance-audit.md`
- `docs/contracts/README.md` (link to audit)
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `docs/contracts/ASC-*.md` (audit READS contracts; never edits them)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`scripts/aios_governance_audit.py`:

- input: contract glob (default `docs/contracts/ASC-*.md`)
- per contract scoring (0-1 each):
  - `closure_evidence`: status:closed + receipt section non-empty
  - `verification_evidence`: receipt cites concrete tests / artifacts / commands run
  - `dna_citation`: cites at least 1 DNA invariant by number
  - `hive_verdict_citation`: cites Hive deliberation if scope is vision-level
  - `dogfood_evidence`: receipt mentions "dogfood" or actual output produced
  - `cross_repo_evidence`: if scope crosses repos, evidence each repo participated
- aggregate: `governance_score = mean(scores)`, `health_color: red|yellow|green`
- output: JSON + human markdown report
- regression: re-runs daily via self_check.sh

Discomfort layer (per founder observation):
- if `governance_score < 0.5` for >50% of recent 20 contracts → fire
  `governance_theater` finding (high severity), surfaces in monitor
- forces conscious decision: improve quality OR explicitly accept the
  theater state

`docs/AIOS_GOVERNANCE_AUDIT.md`:
- documents the scoring rubric
- shows current baseline (105 contracts as of 2026-05-13)
- points to where quality should improve

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_governance_audit.py
python -m unittest tests/test_aios_governance_audit.py
python scripts/aios_governance_audit.py --json | python -c "
import json,sys; d=json.load(sys.stdin)
print('avg_score:', d.get('aggregate',{}).get('governance_score','?'))
print('health:', d.get('aggregate',{}).get('health_color','?'))
print('per_contract_count:', len(d.get('per_contract',[])))
assert len(d.get('per_contract',[])) >= 100, 'should audit all 100+ contracts'
"
python scripts/aios_governance_audit.py --write docs/AIOS_GOVERNANCE_AUDIT.md
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Audit covers all 105+ contracts
- Per-contract scores reported with reasoning
- Aggregate baseline saved (current ~33% verification, 3% DNA, 4% Hive)
- Self-check.sh extended with `governance_theater` check
- Re-running audit produces identical output (deterministic)

## Stop Conditions

- `audit_modifies_contracts`: read-only
- `audit_silent_passing`: must report 0-score contracts not hide them
- `audit_self_exempts`: this contract itself should be audited too
- `audit_score_inflation`: scoring rubric fixed, no "give partial credit"
  drift across runs
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0106-A — codex@myworld implements audit

- target_agent: codex
- target_repo: myworld
- depends_on: ASC-0105 closed (audit needs DNA spec to score citations)
- brief: implement audit + tests + doc. Dogfood: run on all 105 contracts,
  publish baseline. Add governance_theater check to self_check.sh.
