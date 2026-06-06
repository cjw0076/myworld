# AIOS Codex CLI Absorption

Codex must be treated as an AIOS provider substrate, not as the final user
interface. AIOS should use Codex when it is the best implementation and
verification worker, observe its failures, and preserve enough structure that
Claude, Gemini, local LLMs, or deterministic workers can take over when Codex
is unavailable.

## Current Observation

As of 2026-06-05 KST, the interactive Codex session can read, patch, test,
dispatch, and collect AIOS work, and the external `codex --help` command now
prints the command summary without requiring a local PIN in this workspace.
This means AIOS wrappers should treat `codex --help` as an auth/capability
probe whose result can change by installed CLI version or local auth state, not
as a permanently failing command.

On 2026-06-07 KST, the operator ran `codex login` successfully in the same
workspace. AIOS should continue to probe per invocation because this changes
local auth state without making credentials safe to store or replay.

Earlier, on 2026-05-13 KST, the external `codex` binary required a local PIN
when called from a TTY. Without that interactive PIN path, non-interactive
provider calls failed before Codex could even print help:

```text
codex --help
틀렸습니다. (1/3)
틀렸습니다. (2/3)
접근 거부.
```

This historical symptom is not a normal empty output. AIOS should classify the
older failure shape as `pin_required_noninteractive` with localized
`auth_denied_korean` symptoms under provider backpressure, then route through a
fallback or an operator unlock checkpoint instead of waiting for the same
provider to produce work. When `codex --help` succeeds, wrappers can continue
to a bounded non-interactive `codex exec` probe before dispatching real work.

Do not store the PIN in AIOS docs, dispatch packets, contracts, or provider
logs. If AIOS later needs unattended Codex execution, that requires a reviewed
credential/secret-handling contract, not plaintext storage.

## What AIOS Should Absorb

Codex strengths:

- repo search and source reading
- targeted file patches
- tests and CLI verification gates
- dispatch watcher / collect closeout
- dirty-worktree-safe integration
- structured summaries from local evidence

Codex weaknesses:

- no native persistent monitor in a one-shot CLI turn
- non-interactive binary can fail before help text or task execution
- long-running autonomy needs external daemon state
- product sprint execution can under-complete if limited to one tick

## Required Wrapper Behavior

Any Hive or AIOS wrapper around Codex must:

1. Run an auth/PIN probe before dispatching work.
2. Classify localized failures, including Korean `접근 거부`.
3. Require a result packet, even for degraded/failure outcomes.
4. Preserve `cwd`, allowed files, forbidden files, and stop conditions.
5. Requeue unchecked sprint tasks instead of pretending one tick finished all
   work.
6. Feed observations to CapabilityOS.
7. Preserve reviewed summaries for MemoryOS rather than raw provider logs.

## Observed Entry-Agent Execution Modes

2026-05-14 KST quantum/P20 session showed Codex acting less like a single child
repo worker and more like an AIOS entry agent. AIOS should preserve this as a
first-class operating mode rather than hiding it inside chat.

### 1. Sense-And-Route Mode

Observed behavior:

- read repo-local evidence (`git status`, JSON outputs, logs, paper docs)
- read AIOS control docs (`AIOS_NORTHSTAR`, dispatch/build method, shared
  language)
- identify which OS should own each slice instead of treating Hive Mind as the
  whole AIOS

AIOS primitive:

```yaml
mode: sense_and_route
inputs:
  - operator_goal
  - current_worktree_state
  - shared_logs
  - AIOS role docs
outputs:
  - semantic_handshake
  - owner_os_map
  - stop_conditions
```

### 2. Evidence-Audit Mode

Observed behavior:

- read completed result JSONs without launching new experiments
- compute aggregate metrics from local evidence
- distinguish JSON-backed claims from partial log impressions
- preserve source paths so another agent can replay the audit

AIOS primitive:

```yaml
mode: evidence_audit
inputs:
  - result_json_paths
  - run_logs
  - precommitted_decision_rule
outputs:
  - metric_table
  - scope_limited_claim
  - unresolved_gate
```

### 3. Bounded-Hive-Run Mode

Observed behavior:

- created a Hive run in prepare-only mode
- attached result artifacts under `.runs/<run>/artifacts/`
- used the Hive run as the receipt surface, not as the only OS layer

AIOS primitive:

```yaml
mode: bounded_hive_run
authority: execution_receipt_surface
must_not:
  - silently widen scope
  - launch experiments after a stop condition
```

### 4. Multi-OS Reflection Mode

Observed behavior:

- invoked CapabilityOS for route recommendation
- invoked MemoryOS `import-run --dry-run` for provenance readiness
- invoked GenesisOS `critique`/`diverge` before claim promotion
- kept Hive Mind as execution/verification, not memory or routing authority

AIOS primitive:

```yaml
mode: multi_os_reflection
os_roles:
  myworld: contract_and_checkpoint
  hivemind: execution_and_verification
  memoryOS: context_and_provenance
  CapabilityOS: route_and_fallback
  GenesisOS: divergence_and_claim_risk
outputs:
  - multi_os_route_artifact
  - next_contract_seed
```

### 5. Operator-Hold Mode

Observed behavior:

- after `goal stop`, Codex killed/verified process state and did not continue
  experiments
- later, when asked for results, Codex read already-written artifacts only
- new g3_s0 experiment was proposed but not launched

AIOS primitive:

```yaml
mode: operator_hold
trigger:
  - user_stop
  - contract_stop_condition
allowed_actions:
  - inspect_artifacts
  - summarize_existing_evidence
  - write handoff notes
forbidden_actions:
  - launch_new_process
  - commit_or_push_without_operator_release
  - promote_claim_beyond_existing_evidence
```

### 5b. Forced-Continuation Hold Reentry Mode

2026-05-15 KST quantum/Paper5 session exposed a second operator-hold boundary:
an external goal loop can keep re-entering Codex with an open-ended objective
(`진리`) even after Codex has already recorded an operator gate and pushed the
handoff receipt.

Observed behavior:

- Codex completed the finite package/audit slice.
- Codex explicitly refused to mark the open-ended objective complete.
- Codex recorded and pushed an operator gate receipt in the product repo.
- The external loop re-entered Codex anyway with "continue working toward the
  active thread goal".
- Safe action became evidence inspection, receipt hardening, and AIOS
  observation capture rather than launching the next experiment.

AIOS primitive:

```yaml
mode: forced_continuation_hold_reentry
trigger:
  - open_ended_objective
  - prior_operator_hold_receipt_exists
  - next_action_requires_operator_choice
allowed_actions:
  - inspect_current_state
  - harden_completion_audit
  - record_provider_observation
  - confirm round_controller_or_monitor_state
forbidden_actions:
  - silently choose among mutually exclusive operator paths
  - launch new experiments
  - mark open-ended goal complete
  - stack child-repo work on dirty owner repos
exit:
  - operator selects a path
  - contract packet names an owner and allowed files
  - monitor/controller remains armed with hold_for_monitor
```

This mode prevents "continue" pressure from becoming unauthorized execution.
Repeated reentry after a durable hold should improve the hold receipt or
control-plane observation exactly once, then report the same operator gate
without widening scope.

### 6. Dirty-Workspace Custodian Mode

Observed behavior:

- preserved uncommitted quantum outputs instead of cleaning or reverting
- explicitly named modified/untracked files for the next restart
- avoided committing shared logs and result JSONs without user instruction

AIOS primitive:

```yaml
mode: dirty_workspace_custodian
outputs:
  - changed_file_manifest
  - ownership_notes
  - commit_hold_reason
```

### 7. Tmux-Backed Long-Run Mode

2026-05-15 KST quantum/P21 session exposed a Codex execution boundary:
launching `nohup ... &` directly from the one-shot shell returned a PID, but
the child was immediately gone and the log remained empty. The same command
persisted when wrapped inside a detached tmux session.

Observed symptoms:

```text
direct_nohup_background:
  pidfile_written: true
  ps_after_launch: empty
  log_after_launch: empty
  gpu_after_launch: idle

tmux_plus_nohup:
  tmux_session_visible: true
  log_streaming: true
  gpu_memory_allocated: true
  run_completed: true
```

AIOS primitive:

```yaml
mode: tmux_backed_long_run
trigger:
  - experiment_expected_to_outlive_provider_turn
  - direct_nohup_background_exits_empty
launch_pattern:
  - tmux new-session -d -s <session> "<cd repo && nohup command > log 2>&1 & echo pid > pidfile; wait>"
verification:
  - tmux ls includes session
  - pidfile exists
  - log has first heartbeat lines
  - GPU or process state matches expected workload
failure_class:
  direct_nohup_background_empty: provider_shell_child_cleanup_or_lost_job_control
```

Do not treat an empty log plus vanished direct-nohup PID as a scientific run
failure. Treat it as a provider launch failure and retry with a persistent
launcher or route to another execution provider.

## Entry Agent Pattern

Codex can serve as an AIOS entry agent when the user enters from an ordinary
chat instead of an ASC contract. In that mode, Codex should:

1. Translate the user goal into a semantic handshake.
2. Search existing AIOS and repo artifacts.
3. Build an owner map across Hive Mind, MemoryOS, CapabilityOS, GenesisOS, and
   myworld.
4. Execute only the slice it is authorized to execute.
5. Leave a replayable run artifact or shared-log note.
6. Stop at operator checkpoints instead of silently converting planning into
   execution.

This is not a replacement for myworld contracts. It is a bootstrap path that
turns an unstructured chat entry into a contractable AIOS state.

## Role Capsule Additions

```yaml
substrate:
  id: codex_cli
  invocation_mode: one_shot_exec
  auth_probe: codex --help
  failure_patterns:
    pin_required_noninteractive:
      - "틀렸습니다."
      - "접근 거부"
tool_use_capacity:
  native_function_calls: true
  parallel_tool_calls: true
  shell_available: true
  file_patch_available: true
  persistent_monitor_native: false
  schedule_wakeup_native: false
degradation_strategy:
  pin_required_noninteractive: ask_operator_unlock_or_fallback
  auth_denied: fallback_to_claude_or_local_worker
  read_only_sandbox: reroute_to_writable_provider_path_or_hold
  one_shot_undercompletion: requeue_unchecked_task
verification:
  result_packet_required: true
  empty_output_is_failure: true
  final_acceptance_requires_hive_gate: true
entry_agent_modes:
  - sense_and_route
  - evidence_audit
  - bounded_hive_run
  - multi_os_reflection
  - operator_hold
  - dirty_workspace_custodian
```

## Global Codex Instruction

The user-level Codex guidance lives at `/home/user/.codex/AGENTS.md`. Its job
is to make every future Codex session aware that AIOS is the intended control
plane and that Codex should leave reusable observations when it discovers a
new CLI behavior or failure mode.

## Next Contract

`ASC-0081-provider-fallback-execution-binding.md` is the executable follow-up:
it should turn this absorption map into a working Hive fallback path for
Claude, Codex, Gemini, and local LLM workers.
