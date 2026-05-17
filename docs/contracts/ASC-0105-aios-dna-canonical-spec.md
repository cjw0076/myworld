---
contract_id: ASC-0105
slug: aios-dna-canonical-spec
status: closed
goal: Convert ASC-0084 Hive verdict into the canonical AIOS DNA specification at docs/AIOS_DNA.md — the constitutional document every future contract must reference. Without this, the 105 contracts in flight have a debated DNA but no actual constitution to cite.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder explicit GO "A부터 쭉 계약 작성해" + reframe of AIOS as Government)
acceptance_authority: claude@myworld (operator) per founder direct delegation; founder framed AIOS as Government and DNA as constitution.
origin: ASC-0084 closed with `accept_with_dissent` verdict naming 8 invariants + 5-clause preamble + interaction map + amendment clause. The verdict lives in hivemind/.runs/aios_dna_debate/final_state.md but no canonical spec file exists yet. Verification audit 2026-05-13 shows only 3/105 contracts cite DNA invariants — constitution effectively dormant.
closed: 2026-05-13 KST
---

# ASC-0105 AIOS DNA Canonical Specification

DNA references: Invariant 1, Invariant 2, Invariant 3, Invariant 4,
Invariant 5, Invariant 6, Invariant 7, Invariant 8.

## Why Now

Verified 2026-05-13: 105 contracts written, 82 closed, but only **3
cite any DNA invariant**. ASC-0084 Hive deliberation produced an
8-invariant DNA + preamble + interaction map + amendment clause —
but the verdict file (`hivemind/.runs/aios_dna_debate/final_state.md`)
is buried in run artifacts. No canonical `docs/AIOS_DNA.md` exists
that contracts can `Reference` and `cite`.

ASC-0084 explicitly forbade creating the spec in the same contract as
the deliberation (`stop_condition: dna_spec_creation`). ASC-0105 is
the explicit downstream-spec contract that closes that gap.

## Founder Reframe Context

Founder 2026-05-13: AIOS = Government. Substrates (Claude/Codex/Gemini)
provide intelligence — that's not our work. Our work is **DNA design**
(constitution) + **expertise accumulation** (precedent / memory / capability).
This contract writes the constitution.

## Required Reading

- `hivemind/.runs/aios_dna_debate/final_state.md` (Hive verdict — source of truth)
- `hivemind/.runs/aios_dna_debate/round_5/synthesis.md`
- `docs/contracts/ASC-0084-hive-debate-aios-dna.md` (origin contract)
- `docs/AIOS_GOVERNANCE_MODEL.md` (existing governance doc — connect)
- `docs/AIOS_OPERATOR_PLAYBOOK.md` (operator constraints)

## Scope

repos: `myworld`

allowed_files:

- `docs/AIOS_DNA.md` (the canonical spec)
- `docs/AIOS_GOVERNANCE_MODEL.md` (cross-link)
- `docs/AIOS_AGENT_PROTOCOL.md` (cross-link)
- `docs/contracts/README.md` (require DNA citation in new contracts)
- `docs/contracts/ASC-0105-aios-dna-canonical-spec.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `scripts/aios_dna_lint.py` (NEW — validator)
- `tests/test_aios_dna_lint.py`

forbidden_files:

- `hivemind/.runs/**` (read-only — verdict is canonical, do not edit)
- `hivemind/**` source, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`docs/AIOS_DNA.md` — canonical constitution, version 1.0:

- Preamble (5 clauses verbatim from Hive verdict): scope, security_model,
  root_of_trust, prompt_safety, liveness
- 8 invariants (verbatim names + wording from Hive verdict):
  1. Decide before acting
  2. Draft-first
  3. No record destroyed
  4. Every loop has a named exit
  5. Provenance chain
  6. Operator override always possible
  7. AIOS never sends private-gated data
  8. Classify before committing
- Invariant interaction map (per Hive verdict)
- Amendment clause (per Hive verdict — Hive deliberation min 3 rounds + evidence)
- 4 dissents documented (preserved from Hive final_state)
- Cross-references to ASC-0084 verdict + each invariant's enforcing contracts

`scripts/aios_dna_lint.py`:
- input: contract file path
- check: contract body cites at least 1 DNA invariant by number when
  scope touches state outside myworld OR when contract proposes new
  authority/execution capability
- output: JSON `{contract_id, citations: [...], required: bool, missing: bool}`
- runs as part of every Hive verification gate going forward

`docs/contracts/README.md` extension:
- Section: "DNA citation requirement" — when contract scope crosses
  invariant boundary, must cite

### child repos

- No source change. Future cross-OS contracts must cite DNA in their
  per-OS responsibility sections.

## Verification Gate

```bash
python -m py_compile scripts/aios_dna_lint.py
python -m unittest tests/test_aios_dna_lint.py
python scripts/aios_dna_lint.py docs/contracts/ASC-0105-aios-dna-canonical-spec.md --json
# expect: citations include the contract self-reference
python scripts/aios_dna_lint.py docs/contracts/ASC-0091-memoryos-auto-writeback.md --json
# expect: missing=true (it doesn't cite DNA — surface this for retro-fix)
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- AIOS_DNA.md exists with all 8 invariants + preamble + interaction
  map + amendment clause + 4 dissents
- Lint script identifies missing DNA citations in existing contracts
- Lint runs in CI/Hive gate going forward
- Audit baseline: report of which existing 105 contracts cite DNA
  (current=3, document who's missing)

## Stop Conditions

- `dna_spec_drift_from_verdict`: docs/AIOS_DNA.md changes any wording
  from Hive verdict without amendment-clause process
- `dna_lint_blocks_existing`: lint must report missing for existing
  contracts but NOT block them retroactively
- `dna_silent_skip`: lint must always report citations or explicit
  "n/a — myworld-internal"
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- Canonical DNA spec:
  - `docs/AIOS_DNA.md`
- DNA lint:
  - `scripts/aios_dna_lint.py`
  - `tests/test_aios_dna_lint.py`
- Cross-links:
  - `docs/AIOS_GOVERNANCE_MODEL.md`
  - `docs/AIOS_AGENT_PROTOCOL.md`
  - `docs/contracts/README.md`
- Verification passed:
  - `test -f docs/AIOS_DNA.md`
  - `grep -c "^### Invariant [1-8]" docs/AIOS_DNA.md` returned `8`
  - `grep -q "Amendment Clause" docs/AIOS_DNA.md`
  - `grep -q "Dissent" docs/AIOS_DNA.md`
  - `python -m py_compile scripts/aios_dna_lint.py`
  - `python -m unittest tests/test_aios_dna_lint.py`
  - `python scripts/aios_dna_lint.py docs/contracts/ASC-0105-aios-dna-canonical-spec.md --json`
  - `python scripts/aios_dna_lint.py docs/contracts/ASC-0091-memoryos-auto-writeback.md --json`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 224 tests
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0105-dna.myworld.result.json` passed.
- Release writeback:
  - MemoryOS draft `mem_922593c0edb5bbac`
- Baseline dogfood:
  - ASC-0105 requires DNA and cites Invariants 1-8.
  - ASC-0091 requires DNA and reports `missing=true`, as expected for a
    pre-DNA contract; this is evidence, not a retroactive blocker.

## Work Packets

### WP-0105-A — codex@myworld writes spec + lint

- target_agent: codex
- target_repo: myworld
- depends_on: ASC-0084 closed ✓
- brief: write docs/AIOS_DNA.md from final_state.md verbatim. Implement
  lint script. Tests for lint. Update README.md with citation requirement.
  Dogfood: run lint over all 105 contracts; report baseline.
