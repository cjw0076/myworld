---
contract_id: ASC-0129
slug: provider-fallback-execution-binding-hivemind-hive-claude-provider-loop-lacks-allowlisted-perm-39f438b4
status: withdrawn
goal: Bind ASC-0066 provider backpressure role capsules to an executable, verified fallback path that can hand work to Claude, Codex, Gemini, or a local LLM without bypassing Hive verification.
created: 2026-05-14T01:36:47+09:00
accepted:
closed:
withdrawn_reason: raw-permission-expansion-no-authority-model (ASC-0178 reconciliation; ASC-0066 template clone)
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0129 Provider Fallback Execution Binding

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. ASC-0115 requires this draft to answer the specific source packet(s)
listed below instead of silently merging them into a broad theme. This draft is
proposed only. The operator must accept it before any dispatch or
implementation.

## Source Goal Packets

- `rg_20260513T001226_aced75f2adb3` from `hivemind`: Hive Claude provider-loop lacks allowlisted permission mode for execution

## Source Evidence

- `rg_20260513T001226_aced75f2adb3` evidence: `hivemind/.runs/run_20260513_001129_1023bd/agents/claude/native/passthrough_01_result.yaml`

## Scope

repos:

- `hivemind`
- `CapabilityOS`
- `myworld`

allowed_files:

- contract-specific files must be narrowed before acceptance
- `docs/contracts/ASC-0129-provider-fallback-execution-binding-hivemind-hive-claude-provider-loop-lacks-allowlisted-perm-39f438b4.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- `.aios/goal_inbox/**`
- raw export paths
- broad child-repo source edits before accepted work packets

## Responsibilities

### hivemind.must_produce

- A narrowed accepted contract scope with exact files.
- Work packets for every repo that owns implementation.
- Verification receipts linked back to the source goal packets.

### MemoryOS.must_produce

- Context pack or memory draft candidates only if accepted scope requires it.
- No accepted memory without review.

### CapabilityOS.must_produce

- Route or fallback recommendation only if accepted scope requires it.
- No tool/provider binding without an accepted contract.

### Hive Mind.must_produce

- Execution plan, provider route, role capsule, receipt, and verification
  evidence for any implementation packet it owns.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_provider_loop.py tests/test_local_worker_routing.py -v
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py tests/test_observation.py -v
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- Accepted revision narrows allowed files before dispatch.
- Result packets link back to all source goal ids above.
- Verification evidence exists before closeout.

## Stop Conditions

- `fallback_executes_without_contract`
- `provider_secret_leak`
- `role_capsule_missing_rubric`
- `local_llm_used_as_final_acceptor_without_verifier`
- `verification_gate_failed`
- `operator_acceptance_missing`
- `scope_not_narrowed_before_dispatch`
