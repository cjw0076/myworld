---
contract_id: ASC-0036
slug: cross-repo-semantic-alignment
status: closed
goal: Teach every lower-repo agent the AIOS shared language and require semantic handshakes before cross-repo work.
created: 2026-05-12 15:39 KST
accepted: 2026-05-12 15:39 KST
closed: 2026-05-12 16:01 KST
---

# ASC-0036 Cross-Repo Semantic Alignment

## Why Now

The self-resonant repo loop needs more than inbox and outbox files. Agents in
different repos can use the same English words while meaning different things.
Before myworld can keep a live exchange with working repos, every lower-repo
agent must know the AIOS shared language and perform a short meaning handshake.

This is also a prerequisite for the eventual visualization-first control
application: the UI cannot be trusted if each repo reports "contract",
"memory", "capability", or "execution" with different semantics.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_ff2208eaa6d9895b`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_hivemind_execution_harness` ranked first, with
  `cap_memoryos_import_run`, `cap_capabilityos_recommendation`, and
  `cap_memoryos_context_build` as supporting routes.
- Hive Mind dry-run:
  `run_20260512_153529_9eaea3` prepared context, memory, and executor actions
  for this alignment task.

## Scope

repos:

- `myworld`
- `hivemind`
- `memoryOS`
- `CapabilityOS`

allowed_files:

- `docs/AIOS_SHARED_LANGUAGE.md`
- `docs/AIOS_OPERATING_LOOP.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `scripts/aios_child_watcher.sh`
- `scripts/aios_semantic_handshake.py`
- `tests/test_aios_semantic_handshake.py`
- `docs/contracts/ASC-0036-cross-repo-semantic-alignment.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `hivemind/AGENTS.md`
- `hivemind/.ai-runs/shared/comms_log.md`
- `memoryOS/AGENTS.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `CapabilityOS/AGENTS.md`

forbidden_files:

- `hivemind/hivemind/**`
- `memoryOS/memoryos/**`
- `CapabilityOS/capabilityos/**`
- `uri/**`
- `.aios/logs/**`
- `.env`

## Responsibilities

### myworld

must_produce:

- `docs/AIOS_SHARED_LANGUAGE.md` with contract meanings for core AIOS terms.
- `docs/AIOS_OPERATING_LOOP.md` documenting how acting operators call
  MemoryOS, CapabilityOS, Hive Mind, dispatch, watcher, monitor, and closeout
  surfaces while building AIOS.
- `scripts/aios_semantic_handshake.py` validator and focused tests.
- Child watcher prompt update requiring `semantic_handshake`.
- Dispatch packets to hivemind, MemoryOS, and CapabilityOS for repo-local
  agent instruction updates.
- Contract closeout, goal update, and ledger entry.

### Hive Mind

must_produce:

- Update `hivemind/AGENTS.md` so incoming Hive agents read the shared language.
- Record the semantic-handshake rule in `.ai-runs/shared/comms_log.md`.
- Preserve Hive execution authority: Hive executes and verifies, but does not
  accept memory or override capability routing.

### MemoryOS

must_produce:

- Update `memoryOS/AGENTS.md` so MemoryOS agents read the shared language.
- Record the semantic-handshake rule in `memoryOS/docs/AGENT_WORKLOG.md`.
- Preserve MemoryOS authority: memory drafts remain draft until review; accepted
  context must retain provenance.

### CapabilityOS

must_produce:

- Update `CapabilityOS/AGENTS.md` so CapabilityOS agents read the shared
  language.
- Preserve CapabilityOS authority: routes are recommendations, not execution.

## Verification Gate

```bash
python -m py_compile scripts/aios_semantic_handshake.py
python -m unittest tests/test_aios_semantic_handshake.py tests/test_aios_child_watcher.py
python scripts/aios_semantic_handshake.py --json
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py tests/test_aios_institution_readiness.py tests/test_aios_action_policy.py tests/test_aios_semantic_handshake.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- The glossary contains all required terms.
- Each lower repo `AGENTS.md` references `docs/AIOS_SHARED_LANGUAGE.md` or
  `../docs/AIOS_SHARED_LANGUAGE.md`.
- Each lower repo `AGENTS.md` contains the required terms checked by
  `aios_semantic_handshake.py`.
- Child watcher prompts require a semantic handshake.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `semantic_drift_unresolved`
- `missing_repo_agent_update`
- `handshake_validator_false_positive`
- `child_repo_scope_leak`
- `role_boundary_blur`
- `verification_gate_failed`

## Receipts

- pending

## Work Packets

### WP-0036-A — Codex@myworld builds shared language and validator

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: pending
- depends_on: ASC-0035
- brief: |
    Add the AIOS shared language, semantic handshake validator, watcher prompt
    handshake rule, and tests. Do not edit child repo implementation code.
- result: pending

### WP-0036-B — Codex@hivemind aligns Hive agent language

- target_agent: codex
- target_repo: hivemind
- status: issued
- issued: 2026-05-12
- accepted: pending
- closed: pending
- depends_on: WP-0036-A
- brief: |
    Update only `hivemind/AGENTS.md` and `.ai-runs/shared/comms_log.md`.
    Add an AIOS shared-language rule pointing to
    `../docs/AIOS_SHARED_LANGUAGE.md`, and require semantic handshakes before
    cross-repo AIOS work.
- result: pending

### WP-0036-C — Codex@memoryOS aligns MemoryOS agent language

- target_agent: codex
- target_repo: memoryOS
- status: issued
- issued: 2026-05-12
- accepted: pending
- closed: pending
- depends_on: WP-0036-A
- brief: |
    Update only `memoryOS/AGENTS.md` and `memoryOS/docs/AGENT_WORKLOG.md`.
    Add an AIOS shared-language rule pointing to
    `../docs/AIOS_SHARED_LANGUAGE.md`, and require semantic handshakes before
    cross-repo AIOS work.
- result: pending

### WP-0036-D — Codex@CapabilityOS aligns CapabilityOS agent language

- target_agent: codex
- target_repo: CapabilityOS
- status: issued
- issued: 2026-05-12
- accepted: pending
- closed: pending
- depends_on: WP-0036-A
- brief: |
    Update only `CapabilityOS/AGENTS.md`. Add an AIOS shared-language rule
    pointing to `../docs/AIOS_SHARED_LANGUAGE.md`, and require semantic
    handshakes before cross-repo AIOS work.
- result: pending
