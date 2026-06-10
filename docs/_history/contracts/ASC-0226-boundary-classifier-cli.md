---
contract_id: ASC-0226
slug: boundary-classifier-cli
status: closed
goal: Implement the ASC-0225 substrate/surface/knowledge boundary as a small machine-readable MyWorld CLI.
created: 2026-06-05T20:00:00+09:00
accepted: 2026-06-05T20:00:00+09:00
closed: 2026-06-05T20:06:00+09:00
origin: ASC-0225 follow-up under active autonomous-development goal.
accepted_by: codex_delegated_operator
human_approved: false
---

# ASC-0226 Boundary Classifier CLI

## Why Now

`ASC-0225` created the substrate boundary rule, but a document-only rule does
not reliably influence future autonomous turns. This contract makes the rule
callable as a small JSON CLI in MyWorld.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_boundary_classifier.py`
- `tests/test_aios_boundary_classifier.py`
- `docs/AIOS_SUBSTRATE_BOUNDARY.md`
- `docs/contracts/ASC-0226-boundary-classifier-cli.md`
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

## AIOS Role Evidence

### MemoryOS

- no accepted memory.
- no draft memory required.

### CapabilityOS

- represented as a classifier output owner for plugin/tool/MCP/API routes.
- no CapabilityOS execution or catalog mutation.

### GenesisOS

- represented as a classifier output owner for ambiguous frame/assumption
  challenges.
- no GenesisOS execution.

### Hive Mind

- represented as a classifier output owner for process/runtime execution
  substrate.
- no Hive execution in this contract.

### MyWorld

- owns the CLI, tests, docs, and closeout.

## Required Work

- Add `python scripts/aios_boundary_classifier.py --question ... --json`.
- Emit `aios.boundary_classifier.v1`.
- Classify at least:
  - kernel primitive,
  - Hive execution substrate,
  - CapabilityOS plugin/MCP route,
  - MemoryOS external knowledge route,
  - GenesisOS challenge,
  - contract clarification for underspecified prompts.
- Ensure multi-model or "all available knowledge" prompts expand
  `knowledge_scope` without expanding execution authority.
- Test via the CLI surface, not only internal functions.

## Verification Gate

```bash
python -m unittest tests.test_aios_boundary_classifier -v
python -m py_compile scripts/aios_boundary_classifier.py
python scripts/aios_boundary_classifier.py --question "Should AIOS daemonize local LLM background cognition?" --json
git diff --check
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Boundary classifier tests pass.
- CLI returns `schema_version=aios.boundary_classifier.v1`.
- Multi-model review remains `authority=recommendation_only`.
- Unknown prompt returns clarification, not execution.
- No child repo implementation files are changed.

## Result

- `scripts/aios_boundary_classifier.py` added.
- `tests/test_aios_boundary_classifier.py` added.
- `docs/AIOS_SUBSTRATE_BOUNDARY.md` now documents the classifier CLI.
- Kepler subagent reviewed edge cases and confirmed the key risk:
  multi-model/all-knowledge requests expand evidence scope, not execution
  authority.

## Stop Conditions

- `kernel_scope_creep`
- `plugin_executes_without_contract`
- `capabilityos_executes_tool`
- `memory_auto_accepts_research`
- `provider_truth_without_verifier`
- `raw_private_evidence_leak`
- `child_repo_implementation_without_dispatch`
