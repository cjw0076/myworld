---
contract_id: ASC-0066
slug: provider-backpressure-role-distillation
status: closed
goal: Make AIOS survive provider rate limits, quota exhaustion, policy blocks, timeouts, and context failures by classifying provider backpressure and handing the same role capsule to fallback providers under Hive verification.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder directive to sprint AIOS forward and build realistic provider backdoors
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: founder 재원 direct sprint directive
origin: observed Claude provider-loop failure left as active+failed+review instead of cooldown/fallback; founder asked whether another model can take over the same role like distillation.
---

# ASC-0066 Provider Backpressure Role Distillation

## Why Now

AIOS cannot depend on any single provider. Even if the design assumes abundant
tokens, real providers hit rate limits, quota, auth failures, policy blocks,
timeouts, and context exhaustion.

The current Hive provider-loop records a failed Claude worker as
`active + last_status=failed + next_action=review`. That is observable but not
self-healing. AIOS needs a break-glass lane: classify the provider failure,
cool down the degraded provider, package the role/context/rubric, and hand the
same role to a fallback provider or local worker.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/provider_loop.py`
- `hivemind/tests/test_provider_loop.py`
- `docs/contracts/ASC-0066-provider-backpressure-role-distillation.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `.env`
- `.env.*`
- `.aios/logs/**`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`

## Per-OS Responsibility

### hivemind.must_produce

- Provider-loop failure taxonomy:
  - `rate_limit`
  - `quota_exhausted`
  - `auth_denied`
  - `policy_blocked`
  - `timeout`
  - `context_exhausted`
  - `provider_unavailable`
  - `unknown_provider_failure`
- On failed provider tick, worker records:
  - `status: degraded`
  - `failure_category`
  - `cooldown_until`
  - `fallback_candidates`
  - `role_capsule`
  - `next_action: fallback`
- `role_capsule` includes prompt, provider, loop mode, run id, worker id,
  stop conditions, and acceptance rubric. It must not include raw private
  exports or secrets.
- Tests prove policy block and rate-limit text classify distinctly.

### myworld.must_produce

- Contract index and closeout only after Hive tests pass.

### CapabilityOS

- No source role in this first slice. Existing provider-route recommendations
  may be used by later contracts.

### MemoryOS

- No source role in this first slice. Later contracts may store successful
  role handoffs as reviewed memory.

### GenesisOS

- No source role. GenesisOS may later critique provider dependence.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_provider_loop.py -v
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Existing provider-loop tests pass.
- Failed provider tick no longer leaves the worker as plain `active`.
- Policy-blocked execution produces `failure_category=policy_blocked`.
- Rate-limit stderr/reason text produces `failure_category=rate_limit`.
- Worker exposes fallback candidates without executing them.

## Stop Conditions

- `fallback_executes_without_contract`
- `provider_secret_leak`
- `raw_prompt_private_data_persisted`
- `capabilityos_bypassed_for_routing_execution`
- `memoryos_auto_accept`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0066-A — codex@hivemind adds provider backpressure state

- target_agent: codex
- target_repo: hivemind
- status: accepted
- brief: |
    Add provider failure classification and degraded/fallback state to
    `provider_loop.py`. Do not execute fallback providers yet. Record a role
    capsule and fallback candidates so a later contract can hand the role to
    Codex, Gemini, local LLM, or deterministic worker.
- return_to: `.aios/outbox/hivemind/asc-0066.hivemind.result.json`
- result: pending

### WP-0066-B — codex@myworld records closeout

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Update contract index and ledger after Hive tests pass. Do not edit
    MemoryOS, CapabilityOS, GenesisOS, or Uri.
- return_to: `.aios/outbox/myworld/asc-0066.myworld.result.json`
- result: pending
