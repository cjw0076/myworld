---
contract_id: ASC-0249
slug: build-runtime-isolation-boundary
status: closed
goal: Separate AIOS system-building work from live AIOS agent runtime work so control-plane development cannot accidentally mix with production-like agent execution on the same machine.
created: 2026-06-13T14:45:00+09:00
accepted: 2026-06-13T14:45:00+09:00
closed: 2026-06-13T15:24:00+09:00
human_approved: true
origin: Operator flagged that AIOS is being built while real AIOS-using agents also run from this machine; Codex observed shared .aios state, long-running pulses, round controller, and provider sessions under the same workspace.
---

# ASC-0249 Build/Runtime Isolation Boundary

## Why Now

AIOS is currently both the product under construction and the local substrate
used by agents. That is useful for dogfooding, but it creates a dangerous
ambiguity:

- a build contract can spawn or leave provider processes that look like live
  AIOS agents;
- live pulse/round/runtime state can make control-plane development look
  blocked or active;
- result packets, leases, MCP servers, and operator sessions can share the same
  `.aios` runtime directories unless the mode is explicit.

ASC-0248 added per-dispatch lease collision control. It does not solve the
larger build-vs-runtime namespace problem.

This contract delegates implementation to Claude. Codex must not patch the
implementation in this slice.

## Current Evidence

Observed on 2026-06-13 around 14:43 KST:

- `aios_round_controller.py run ... --interval 30.0` is alive under the
  `myworld` root.
- Long-running pulse loops write to `.aios/primitives/events.jsonl`.
- Multiple provider sessions and MCP servers point at the same
  `/home/user/workspaces/jaewon/myworld` workspace.
- The ASC-0248 Claude provider session stayed alive after writing a closed
  result packet and was manually terminated by Codex after verification.
- `.aios/inbox/*` is empty and `aios_dispatch.py status` shows ASC-0248
  collected, but build and runtime state still share one local namespace.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_round_controller.py`
- `scripts/aios_child_watcher.sh`
- `scripts/aios_monitor.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_round_controller.py`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_monitor.py`
- `docs/contracts/ASC-0249-build-runtime-isolation-boundary.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work For Claude

Add an explicit local boundary between AIOS system-building work and live AIOS
agent runtime work.

Minimum requirements:

1. Introduce a small, auditable runtime profile concept with at least:
   - `build_control` for contracts, code changes, verification, and delegation;
   - `live_agent_runtime` for actual AIOS agent workloops/pulses.
2. Make the active profile visible in dispatch, round-controller, or monitor
   status output so operators can see which mode is active.
3. Prevent build-control workers from silently starting live child execution
   unless the profile or packet explicitly allows it.
4. Detect stale provider sessions for a closed dispatch and surface them as an
   isolation finding, not as successful work.
5. Keep runtime profile state local under `.aios/` and out of commits.
6. Preserve existing dogfood loops; do not kill or disable long-running pulses
   by default. The goal is separation and visibility, not a blanket stop.
7. Add focused tests for:
   - default profile classification;
   - build-control child execution blocked without explicit allowance;
   - live-runtime profile can still recommend or run the appropriate watcher;
   - closed-dispatch stale provider session is reported as isolation risk;
   - existing ASC-0248 lease behavior still passes.

Do not implement hosted cloud isolation, private-key brokering, provider API
adapters, or product UI in this contract.

## Plain-Language Framing

AIOS needs two clearly labeled rooms on the same machine:

- one room for building AIOS;
- one room for AIOS agents doing real work.

Agents may move between rooms only through an explicit door, not by sharing the
same hallway and hoping nobody confuses the state.

## Cross-Domain Frame

### Biology: Symbiosis

Two organisms can cooperate closely without becoming the same organism. The
useful pattern is not total separation; it is a membrane that permits selected
exchange while preserving identity. AIOS should keep dogfooding, but build
work and live runtime work need an explicit membrane: profile, state root,
allowed transitions, and receipts.

### Geology: Strata

Sedimentary layers preserve history because older and newer layers are not
flattened into one present surface. AIOS should similarly preserve build
events, runtime events, and provider-process evidence as separate layers even
when they happen on one machine.

### Counter Branch

Counter-default option: do not add a profile boundary; instead, stop all live
pulse loops whenever system-building work starts. This is rejected for now
because it would reduce dogfood evidence and hide the exact interference AIOS
needs to learn from. The better first move is visible separation with explicit
transition gates.

## Assumptions

- Assumption 1: local profile state is enough before hosted runtime rollout.
- Assumption 2: dogfooding remains allowed, but must be labeled.
- Assumption 3: profile separation should be visible before it is physically
  perfect.

Negated checks:

- Do not stop all existing pulse loops as a substitute for isolation.
- Do not store private keys, provider account material, or raw auth values.
- Do not commit runtime profile files under `.aios/`.
- Do not mark live child execution as safe when it merely happened locally.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_dispatch tests.test_aios_child_watcher tests.test_aios_round_controller tests.test_aios_monitor -v
python3 -m py_compile scripts/aios_dispatch.py scripts/aios_round_controller.py scripts/aios_monitor.py
bash -n scripts/aios_child_watcher.sh
git diff --check
```

Pass criteria:

- Focused tests pass.
- Operators can distinguish build-control work from live-agent runtime work.
- Build-control mode cannot silently trigger live child execution.
- Stale closed-dispatch provider sessions are visible as isolation risk.
- ASC-0248 dispatch lease tests remain green.

## AIOS Role Evidence

### MemoryOS

- source_context: operator warning plus process/state inventory from the local
  machine.
- draft_policy: no accepted memory mutation in this slice.

### CapabilityOS

- route: local control-plane profile/status primitives first; hosted runtime is
  out of scope.
- authority: no provider account material or external API binding.

### GenesisOS

- challenge: Dogfooding can hide product defects if "the system under
  construction" and "the system doing work" share the same identity.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements profile visibility and guardrails; tests
  prove no silent build-to-runtime crossover.

## Work Packets

### WP-0249-A — Claude build/runtime isolation boundary

- target_repo: `myworld`
- target_agent: `claude`
- status: closed
- instruction: Implement the Required Work For Claude section. Keep the slice
  tight. Return a result packet with changed files, tests run, profile schema,
  isolation behavior, and remaining gaps.
- result: completed through ASC-0250 finish-forward after the first ASC-0249
  run produced useful partial changes but no clean closeout packet.

## Stop Conditions

- `build_runtime_profile_ambiguous`
- `silent_child_execution_from_build_control`
- `closed_dispatch_provider_session_unreported`
- `runtime_profile_committed`
- `test_gate_failed`
- `scope_violation`
- `privacy_violation`
