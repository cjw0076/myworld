---
contract_id: ASC-0049
slug: hive-semantic-verifier-review
status: closed
goal: Add a Hive semantic verifier review surface for high-risk runs without automatic provider execution.
created: 2026-05-12 22:48 KST
accepted: 2026-05-12 22:48 KST by codex acting operator
closed: 2026-05-12 22:59 KST
supersedes: none
---

# ASC-0049 Hive Semantic Verifier Review

## Why Now

ASC-0048 refined the goal loop to the concrete Hive TODO
`myworld/hivemind/docs/TODO.md#semantic-verifier`: add semantic verifier LLM
review for high-risk runs. The first safe slice should not auto-run provider
CLIs. It should detect high-risk semantic conditions, write a verifier prompt,
and produce a durable review artifact that later provider or local LLM execution
can consume under explicit policy.

## AIOS Inputs

- MemoryOS context: `rtrace_ee519c13d4b1b75a`
- Accepted memory used: `mem_90b5cfe6570e6ee2`
- CapabilityOS top route: `cap_hivemind_execution_harness`
- Supporting routes: `cap_memoryos_import_run`,
  `cap_capabilityos_recommendation`, `cap_memoryos_context_build`,
  `cap_web_research_route`
- Hive dry-run: `run_20260512_224741_56e342`

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/semantic_verifier.py`
- `hivemind/hivemind/evaluation.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/run_validation.py`
- `hivemind/tests/test_semantic_verifier.py`
- `hivemind/tests/test_evaluation.py`
- `hivemind/docs/TODO.md`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `docs/contracts/ASC-0049-hive-semantic-verifier-review.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.runs/**`
- raw export paths
- provider transcript bodies
- private memory store data

## Responsibilities

### hive_mind.must_produce

- A first-class `hive semantic-review` command that reads one run and writes
  `artifacts/semantic_verification.json`.
- A semantic verifier prompt artifact suitable for later LLM/provider review,
  without raw provider stdout/stderr or private memory contents.
- High-risk detection over task wording, validation verdict, inspect verdict,
  disagreements, and provider/local risk receipts.
- Integration with `hive evaluate` so high-risk runs without semantic review
  surface a verifier recommendation, while existing semantic reviews are cited.
- Tests for high-risk detection, low-risk skip posture, CLI JSON output,
  artifact/state/event durability, and path/raw-body privacy.

### memoryos.must_produce

- No source change. MemoryOS provided context only.

### capabilityos.must_produce

- No source change. CapabilityOS provided route evidence only.

### myworld.must_produce

- Contract, dispatch/result collection, README index update, goal plan refresh,
  and ledger closeout after verification passes.

## Verification Gate

```bash
cd hivemind && python -m pytest tests/test_semantic_verifier.py -v
cd hivemind && python -m pytest tests/test_semantic_verifier.py tests/test_evaluation.py -v
cd hivemind && python -m hivemind.hive --root /tmp/asc-0049-semantic-smoke run "release public high-risk claim" --json
cd hivemind && python -m hivemind.hive --root /tmp/asc-0049-semantic-smoke semantic-review --run <RUN_ID> --json
cd hivemind && python -m pytest
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `artifacts/semantic_verification.json` exists and is referenced in run state.
- High-risk runs return `review_required` or stronger, not silent pass.
- Low-risk runs can return `not_required` but still produce an audit record.
- Default JSON hides absolute paths and raw provider/private bodies.
- `hive evaluate` cites semantic review state.

## Stop Conditions

- `provider_auto_execution`: implementation auto-runs Claude/Codex/Gemini or
  local LLM without explicit operator policy.
- `privacy_violation`: semantic artifact includes raw provider bodies, private
  memory contents, or non-debug absolute paths.
- `high_risk_silent_pass`: high-risk signals exist but no review requirement is
  surfaced.
- `schema_drift`: semantic artifact cannot be consumed as
  `hive_semantic_verification`.
- `child_scope_creep`: implementation edits MemoryOS or CapabilityOS source.
- `verification_gate_failed`
- `monitor_not_clear`

## Receipts

Closed 2026-05-12 22:59 KST by `codex@myworld` acting operator.

- Dispatch:
  - `.aios/inbox/hivemind/asc-0049.hivemind.json`
  - `.aios/inbox/myworld/asc-0049.myworld.json`
  - `.aios/outbox/hivemind/asc-0049.hivemind.result.json`
  - `.aios/outbox/myworld/asc-0049.myworld.result.json`
- Hive implementation:
  - commit `a0df4ca` (`Add semantic verifier review`)
  - `hivemind/hivemind/semantic_verifier.py`
  - `hivemind/tests/test_semantic_verifier.py`
- Verification:
  - `cd hivemind && python -m pytest tests/test_semantic_verifier.py -v`
    passed 6/6.
  - `cd hivemind && python -m pytest tests/test_semantic_verifier.py
    tests/test_evaluation.py -v` passed 12/12.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0049-semantic-smoke run "release public high-risk claim" --json`
    created `run_20260512_225418_1b3d02`.
  - `cd hivemind && python -m hivemind.hive --root
    /tmp/asc-0049-semantic-smoke semantic-review --run
    run_20260512_225418_1b3d02 --json` returned
    `kind=hive_semantic_verification`, `status=review_required`,
    `risk_level=high`, `provider_executed=false`.
  - `cd hivemind && python -m pytest` passed 322/322.
  - `cd hivemind && git diff --check` passed.
- Stop conditions triggered: none.

## Work Packets

### WP-0049-A — Codex@hivemind implements semantic verifier artifact

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 22:48 KST
- closed: 2026-05-12 22:57 KST
- depends_on: ASC-0048
- brief: |
    Add `hive semantic-review` as a provider-free semantic verifier surface for
    high-risk runs. It must write `artifacts/semantic_verification.json`, create
    a redacted verifier prompt artifact, update run state and events, and
    integrate with `hive evaluate`. Do not auto-run provider CLIs or local LLMs.
- result: `.aios/outbox/hivemind/asc-0049.hivemind.result.json`

### WP-0049-B — Codex@myworld collects and closes

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12 22:48 KST
- closed: 2026-05-12 22:59 KST
- depends_on: WP-0049-A
- brief: |
    Collect Hive result packet, run MyWorld verification, refresh the goal plan,
    update the contract index and ledger, and release the dispatch when monitor
    is clear.
- result: `.aios/outbox/myworld/asc-0049.myworld.result.json`
