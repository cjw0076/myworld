---
contract_id: ASC-0079
slug: hivemind-public-alpha-hardening
status: accepted
goal: Convert the external GitHub evaluation of hivemind into a bounded public-alpha hardening plan: preserve the validated architecture strengths, correct public-facing gaps, and route implementation work through the Hive-owned repo.
created: 2026-05-13 KST
accepted:
closed:
acceptance_authority: claude@myworld (operator) per founder "네가 판단" delegation 2026-05-13 KST. External evaluation route to public alpha approved.
origin: External evaluation of https://github.com/cjw0076/hivemind on 2026-05-13 KST plus Codex verification against GitHub API, README, pyproject, and local repo state.
---

# ASC-0079 Hivemind Public Alpha Hardening

## Why Now

An outside-reader evaluation scored `hivemind` around `3.7/5`: strong local
blackboard/DAG/provider-harness architecture, but public-alpha maturity gaps
around giant files, external onboarding proof, docs-code drift, and public
presentation. Codex verified the main claims against GitHub and local code:

- GitHub repo is public, MIT, created 2026-05-02, last pushed 2026-05-11,
  with 0 stars and 0 forks.
- README positions Hive as a local provider-CLI harness, not a replacement for
  provider CLIs or a full autonomous OS.
- `pyproject.toml` exists, so "dependencies unclear" is not accurate.
- Local largest files remain large: `hivemind/hivemind/harness.py`,
  `hivemind/hivemind/plan_dag.py`, and `hivemind/hivemind/hive.py`.
- Local tests are broader than the outside review saw: 32 Python test modules.

ASC-0079 turns this review into AIOS work without letting `myworld` directly
edit Hive source. MyWorld records the hardening contract and dispatches a Hive
packet; `hivemind/` owns implementation.

## Scope

repos:

- `myworld`
- `hivemind`

allowed_files:

- `docs/contracts/ASC-0079-hivemind-public-alpha-hardening.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `hivemind/README.md`
- `hivemind/pyproject.toml`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/harness.py`
- `hivemind/hivemind/plan_dag.py`
- `hivemind/tests/test_cli_entrypoint.py`
- `hivemind/tests/test_quickstart.py`
- `hivemind/tests/test_plan_dag.py`
- `hivemind/tests/test_production_hardening.py`
- `hivemind/docs/HIVE_PUBLIC_ALPHA.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `.env`
- `.env.*`
- raw private exports
- `.runs/**`
- `.hivemind/logs/**`
- provider credential files

## Per-OS Responsibility

### myworld.must_produce

- Proposed contract and dispatch packet.
- External-evaluation receipt summary in the AIOS ledger after acceptance or
  after a child result is collected.
- No direct Hive source edit unless a later operator explicitly reassigns
  ownership.

### hivemind.must_produce

- Public-alpha hardening plan or patch that addresses:
  - fresh-clone onboarding proof: quickstart demo, inspect, and tests;
  - public README correction for dependency/maturity boundaries;
  - docs-code drift risk;
  - top-level module split strategy for `harness.py`, `hive.py`, and
    `plan_dag.py` without destabilizing behavior.
- A verification receipt with exact commands and test counts.
- If refactor is too large for one sprint, a staged plan with first safe
  extraction target and stop condition.

### memoryos.must_receive

- Later MemoryOS draft candidate summarizing the external review, Codex
  verification, and Hive result. No memory is accepted by this contract.

### capabilityos.must_receive

- Later CapabilityOS observation candidate: outside-reader review is useful
  evidence for public-alpha routing and documentation-hardening capability.
  CapabilityOS does not execute tools in this contract.

### GenesisOS

- No implementation role in this contract.

## Verification Gate

Hive-owned verification should run from `hivemind/`:

```bash
python -m pytest tests/test_cli_entrypoint.py tests/test_quickstart.py tests/test_plan_dag.py tests/test_production_hardening.py -v
python -m pytest -q
python -m hivemind.hive demo quickstart
python -m hivemind.hive inspect --json
```

MyWorld closeout gate:

```bash
python scripts/aios_dispatch.py collect --repo hivemind
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Hive quickstart works from documented commands without provider API keys.
- README clearly states maturity boundary, dependency surface, first-five-minute
  path, and what belongs to sibling MemoryOS/CapabilityOS repos.
- Any module split is incremental and test-backed; no behavior-only refactor is
  accepted without tests.
- No raw run data, credentials, or `.runs/**` artifacts are committed.

## Stop Conditions

- `hive_source_edit_from_myworld`
- `provider_key_required_for_quickstart`
- `docs_claim_without_verification`
- `large_refactor_without_tests`
- `raw_run_artifact_committed`
- `sibling_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0079-A — codex@hivemind public-alpha hardening pass

- target_agent: codex
- target_repo: hivemind
- status: proposed
- brief: |
    Read the external evaluation summary in this contract, then inspect the
    current Hive repo. Implement only the smallest safe public-alpha hardening
    slice: README/dependency/onboarding corrections and, if low-risk, a
    docs-code drift or module-size guard. Do not attempt a sweeping split of
    `harness.py` in one turn. Return exact tests and a staged refactor plan.
- return_to: `.aios/outbox/hivemind/asc-0079.hivemind.result.json`
- result: pending
