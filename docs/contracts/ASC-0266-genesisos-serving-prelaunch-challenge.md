---
contract_id: ASC-0266
slug: genesisos-serving-prelaunch-challenge
status: closed
goal: Implement the GenesisOS pre-launch adversarial challenge harness for real end-user AIOS serving so launch cannot close with unresolved privacy, authority, abuse, or frozen-knowledge risks.
created: 2026-06-13T20:00:00+09:00
accepted: 2026-06-13T20:00:00+09:00
closed: 2026-06-13T20:13:00+09:00
human_approved: true
origin: ASC-0260/ASC-0261 release gate marks GenesisOS pre-launch challenge as missing and owner-bound to GenesisOS.
depends_on:
  - ASC-0239
  - ASC-0260
  - ASC-0261
  - ASC-0262
---

# ASC-0266 GenesisOS Serving Prelaunch Challenge

## Decision

GenesisOS owns assumption mutation, semantic challenge, prompt-prison critique,
and frozen-knowledge pressure before launch. It does not approve release by
itself; it produces adversarial findings that MyWorld must resolve or explicitly
hold.

This contract turns ASC-0260 Slice 9 into an executable owner-bound packet for
`GenesisOS`. The launch proof under `.aios/serving/proofs/` remains runtime
evidence and should be produced only when a release candidate exists.

## Plain Language

In plain language: build the launch critic that tries to prove the serving
product is unsafe before users rely on it. Missing evidence is a blocker, not a
pass.

## Counter-Default Branch

The common default is "if all tests are green, launch." That is not enough for
AIOS. The counter-default branch is to assume green tests may still hide a bad
frame: privacy leaks, authority bypass, support overexposure, abuse paths, and
provider-convergence blind spots must be challenged separately.

## Cross-Domain Frame

Fire drills are the useful analogy: the building is not safe because the doors
look correct; it is safer after people rehearse failure under pressure and find
which exits do not work. Prelaunch challenge should do that for AIOS serving.

## Scope

repos:

- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/serving_prelaunch.py`
- `GenesisOS/tests/test_serving_prelaunch.py`
- `GenesisOS/docs/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores
- raw user data
- `.aios/serving/proofs/genesis_prelaunch.json`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `apps/**`
- `uri/**`
- unrelated child repo source files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `genesis_assumption_challenge`
- owner_repo: `GenesisOS`
- substrate_level: `none`
- surface_type: `dispatch`
- knowledge_scope: `multi_model_review`
- authority: `speculative_only`
- required_receipts:
  - `aios.serving_prelaunch_challenge.v1`
  - `assumption_negation_matrix`
  - `privacy_authority_abuse_findings`
  - `frozen_knowledge_pressure_report`

## Required Work

Implement a pre-launch challenge primitive that accepts a release-candidate
manifest and produces structured findings for:

- cross-user data leakage;
- user authority and approval bypass;
- support/admin raw-content exposure;
- connector consent and credential boundary failures;
- abuse and malicious user workflows;
- provider convergence and frozen-knowledge risk;
- whether ASC-0260's three negated assumptions were actually refuted.

The harness must be deterministic and testable without a real launch candidate.
It should be able to emit a `blocked` finding when required evidence is missing.

## Per-OS Responsibility

### GenesisOS

must_produce:

- `GenesisOS/genesisos/serving_prelaunch.py`
- `GenesisOS/tests/test_serving_prelaunch.py`
- focused test evidence for missing-evidence blocking, assumption negation, privacy risk blocking, and frozen-knowledge pressure

### Hive Mind

must_produce:

- no implementation in this contract; future release candidate receipts are inputs

### MemoryOS

must_produce:

- no implementation in this contract; future reviewed memory can feed the challenge

### CapabilityOS

must_produce:

- no implementation in this contract; future access-routing evidence can feed the challenge

## Acceptance Evidence

- `GenesisOS/genesisos/serving_prelaunch.py` exists and produces an
  `aios.serving_prelaunch_challenge.v1` payload.
- Tests prove unresolved cross-user data, authority, or support-risk findings
  make the challenge status `blocked`.
- Tests prove missing launch evidence is not treated as a pass.
- Tests prove frozen-knowledge/provider-convergence risk is surfaced as a
  first-class finding.
- Runtime proof `.aios/serving/proofs/genesis_prelaunch.json` is not generated
  by this contract; it belongs to the later release-candidate closeout.

## Verification Gate

```bash
cd GenesisOS
python -m pytest tests/test_serving_prelaunch.py -q
python -m py_compile genesisos/serving_prelaunch.py tests/test_serving_prelaunch.py
git diff --check
```

## Stop Conditions

- `launch_closes_without_adversarial_review`
- `assumption_not_negated`
- `privacy_risk_unresolved`
- `missing_evidence_treated_as_pass`
- `genesisos_selects_release_truth`
- `child_repo_implementation_without_owner_contract`

## Return Packet

Write `.aios/outbox/GenesisOS/asc-0266.GenesisOS.result.json` with:

- changed files;
- test commands and outcomes;
- remaining gaps;
- stop conditions triggered, if any.

## Result

Claude executed the owner-bound packet through `scripts/aios_child_watcher.sh`
as `claude@GenesisOS`.

Evidence:

- dispatch result: `.aios/outbox/GenesisOS/asc-0266.GenesisOS.result.json`
- child commit: `GenesisOS` `4670471 Add serving prelaunch adversarial challenge harness (ASC-0266)`
- changed child files:
  - `GenesisOS/genesisos/serving_prelaunch.py`
  - `GenesisOS/tests/test_serving_prelaunch.py`
  - `GenesisOS/docs/AGENT_WORKLOG.md`
- verification:
  - `python -m pytest tests/test_serving_prelaunch.py -q` passed 16/16 in `GenesisOS`
  - `python -m py_compile genesisos/serving_prelaunch.py tests/test_serving_prelaunch.py` passed
  - `git diff --check` passed in `GenesisOS`

Release gate delta:

- `genesis_prelaunch_challenge`: `missing` -> `partial`

The runtime launch-candidate proof remains intentionally missing:

- `.aios/serving/proofs/genesis_prelaunch.json`

That proof must be produced only after Product Design, serving UI, observability
support, and release-candidate evidence exist.
