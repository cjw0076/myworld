---
contract_id: ASC-0228
slug: hive-claude-execute-policy-gate
status: closed
goal: Policy-gate or replace the unsafe Claude execute workaround before adding broader automation
created: 2026-06-06 07:02 KST
accepted: 2026-06-06 07:08 KST
closed: 2026-06-06 07:14 KST
origin: AIOS-GOAL-0001 goal evolution from Hive Product Evaluation Next Product P0.
accepted_by: codex_delegated_operator
human_approved: false
---

# ASC-0228 Hive Claude Execute Policy Gate

## Why Now

Goal evolution selected this unblocked recommendation:

- path: `myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md#next-product-p0-1`
- domain: `hivemind`
- policy_decision: `unknown`
- reason: refined from Hive product evaluation to first concrete P0

Codex is accepting this narrow contract under the active autonomous-development
goal because the source is a concrete Hive Product P0 and the Hive repo is
clean. The work must not broaden into parallel fan-out or unrelated provider
automation.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/harness.py`
- `hivemind/tests/test_provider_passthrough.py`
- `hivemind/docs/HIVE_PRODUCT_EVALUATION.md`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `.aios/outbox/hivemind/*.result.json`
- `docs/contracts/ASC-0228-myworld-hivemind-docs-hive-product-evaluation-md-next-product-p0-1.md`
- `scripts/aios_goal_candidates.py`
- `scripts/aios_goal_refinements.py`
- `tests/test_aios_goal_candidate_refinement.py`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/logs/**`
- `.aios/state/**`
- `.env`
- `.env.*`
- provider credentials
- raw export paths
- Hive provider auth files
- MemoryOS accepted-memory stores
- CapabilityOS catalog writes
- broader DAG fan-out implementation
- provider execution beyond mocked/unit-test execution

## Responsibilities

### myworld.must_produce

- Accepted contract with exact allowed files and stop conditions.
- Dispatch/result/ledger evidence if the child watcher is used.
- Closeout evidence showing no broader automation was added.

### hivemind.must_produce

- Replace or policy-gate the hard-coded Claude
  `--dangerously-skip-permissions` execute path.
- Regression test proving Claude execute command construction no longer uses
  `--dangerously-skip-permissions`.
- Existing provider passthrough hard-block test for the dangerous Claude flag
  must remain green.
- Product docs/TODO closeout only if the code and tests prove the P0 closed.

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `execution_substrate`
- owner_repo: `hivemind`
- substrate_level: `provider_process`
- surface_type: `direct_hive_execution`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- next_contract_kind: `hive_execution_contract`

required_receipts:

- `test_report`
- `provider_command_policy_receipt`
- `hivemind_worklog_entry`
- `myworld_ledger_closeout`

boundary_stop_conditions:

- `dangerous_claude_bypass_still_present`
- `provider_execution_without_mock_or_explicit_grant`
- `broader_automation_scope_creep`


## AIOS Role Evidence

### MemoryOS

- context_pack: `pending_or_not_required`
- retrieval_trace: `pending_or_not_required`
- accepted_memory_ids: `pending_or_not_required`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `pending_or_not_required`
- recommended_tools: `pending_or_not_required`
- fallback_plan: `pending_or_not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `pending_or_not_required`
- assumption_mutations: `pending_or_not_required`
- semantic_alignment_notes: `pending_or_not_required`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `replace unsafe Claude execute command construction or gate it before use`
- provider_route: `Claude CLI plan-mode only; no dangerous bypass flag`
- verification_receipt: `pending_after_execution`
- degraded_or_fallback_receipt: `pending_if_triggered`


## Verification Gate

```bash
cd hivemind
python -m unittest tests.test_provider_passthrough -v
python -m unittest tests.test_provider_passthrough tests.test_production_hardening -v
python -m py_compile hivemind/harness.py hivemind/provider_passthrough.py
git diff --check
cd ..
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- No generated Claude command includes `--dangerously-skip-permissions`.
- Dangerous Claude passthrough remains policy-blocked with receipt artifacts.
- No provider CLI is executed live by the tests; subprocess execution must be
  mocked where execute behavior is asserted.
- `hivemind` worktree changes are committed and pushed separately from
  unrelated MyWorld dirty state.
- MyWorld monitor remains clear or only reports advisory info findings.

## Stop Conditions

- `dangerous_claude_bypass_still_present`
- `provider_execution_without_mock_or_explicit_grant`
- `broader_automation_scope_creep`
- `allowed_files_too_broad`
- `verification_gate_failed`
- `monitor_not_clear`

## Work Packets

### WP-0228-A — Hive Claude execute policy gate

- target_agent: codex
- target_repo: hivemind
- status: accepted
- issued: 2026-06-06
- brief: |
    semantic_handshake:
      contract_id: ASC-0228
      target_repo: hivemind
      terms_confirmed:
        - AIOS smart contract
        - dispatch packet
        - memory draft
        - capability route
        - hive execution
        - stop condition
        - semantic handshake
      ambiguous_terms: []

    Replace or policy-gate Hive's hard-coded Claude execute workaround so
    `invoke_external_agent(..., agent="claude", execute=True)` cannot build a
    command containing `--dangerously-skip-permissions`. Preserve the existing
    provider passthrough policy block for that flag. Do not add broader
    automation, DAG fan-out, provider live execution, or credential handling.
- required_reading:
  - `hivemind/AGENTS.md`
  - `docs/AIOS_SHARED_LANGUAGE.md`
  - `hivemind/docs/HIVE_PRODUCT_EVALUATION.md`
  - `hivemind/docs/PROVIDER_HARNESS_GUIDE.md`
  - `hivemind/tests/test_provider_passthrough.py`
- must_produce:
  - code/test diff within allowed files
  - Hive worklog/comms log entry
  - test report
  - result packet or MyWorld closeout receipt

## Source Plan Evidence

- generated_at: `2026-06-06T07:02:50+09:00`
- monitor_health: `watch`
- readiness: `L6 repeatable`
- alignment_reasons: `verification_signal, concrete_product_eval_p0`
- blocked_reasons: ``

## Result

- status: closed
- hivemind_commit: `7e79aca`
- hivemind_push: `origin/main`
- changed:
  - `hivemind/hivemind/harness.py`
  - `hivemind/tests/test_provider_passthrough.py`
  - `hivemind/docs/HIVE_PRODUCT_EVALUATION.md`
  - `hivemind/docs/TODO.md`
  - `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `scripts/aios_goal_candidates.py`
- `scripts/aios_goal_refinements.py`
- `tests/test_aios_goal_candidate_refinement.py`
- decision: Hive no longer builds Claude execute commands with
  `--dangerously-skip-permissions`; `external_command()` now uses
  `-p <prompt> --permission-mode plan --output-format text`. Native provider
  passthrough still hard-blocks the dangerous Claude bypass flag and records
  policy-block receipts.
- follow-up refinement: goal evolution now skips closed Product P0 items, so
  the closed ASC-0228 source advances to
  `myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md#next-product-p0-2`
  instead of reselecting the `[closed via ASC-0228]` item.

## Verification Receipt

```bash
cd hivemind
python -m unittest discover -s tests -p 'test_provider_passthrough.py' -v
python -m unittest discover -s tests -p 'test_production_hardening.py' -v
python -m py_compile hivemind/harness.py hivemind/provider_passthrough.py
git diff --check
bash scripts/public-release-check.sh
cd ..
python -m unittest tests.test_aios_goal_candidate_refinement tests.test_aios_goal_source_hygiene tests.test_aios_goal_evolution tests.test_aios_contract_autodraft tests.test_aios_boundary_classifier -v
python -m py_compile scripts/aios_goal_evolution.py scripts/aios_goal_plan.py scripts/aios_goal_sources.py scripts/aios_goal_candidates.py scripts/aios_goal_refinements.py scripts/aios_goal_source_hygiene.py scripts/aios_goal_stop_conditions.py scripts/aios_contract_autodraft.py scripts/aios_boundary_classifier.py
python scripts/aios_goal_evolution.py plan --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --json
python scripts/aios_contract_autodraft.py draft --goal docs/goals/AIOS-GOAL-0001-make-something-great.md --json
python scripts/aios_monitor.py assess --json
```

Observed:

- provider passthrough tests: 13/13 passed.
- production hardening tests: 37/37 passed.
- py_compile: passed.
- Hive `git diff --check`: passed.
- public release gate: 19/19 passed, artifact root
  `hivemind/.hivemind/release/20260606_070951`.
- MyWorld focused goal tests: 24/24 passed.
- MyWorld py_compile: passed.
- goal evolution after closeout recommends
  `myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md#next-product-p0-2`.
- contract autodraft after closeout proposes ASC-0229 and does not write it.
- monitor after implementation: `watch` with only info-level
  `persona_axis_advisory`.

## Closeout

- stop_conditions_triggered: none.
- scope_check: no broader automation, DAG fan-out, credential handling,
  MemoryOS accepted-memory write, or CapabilityOS catalog write.
- ledger_note: `docs/AIOS_AGENT_LEDGER.md` already contains unrelated dirty
  work and is intentionally not staged in this closeout; this closed contract
  is the durable MyWorld receipt for ASC-0228.
- file_size_note: `hivemind/harness.py` remains an oversized legacy module;
  ASC-0228 deliberately changed only the unsafe command builder. Future
  work should continue extracting provider command construction into narrower
  modules.
- next: open or execute the next Hive Product P0:
  `Harden DAG step result handling: local/provider failures must not become
  completed steps.`
