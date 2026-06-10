---
contract_id: ASC-0081
slug: provider-fallback-execution-binding
status: closed
goal: Bind ASC-0066 provider backpressure role capsules to an executable, verified fallback path that can hand work to Claude, Codex, Gemini, or a local LLM without bypassing Hive verification.
created: 2026-05-13T10:11:37+09:00
accepted: 2026-05-13T11:21:51+09:00
closed: 2026-05-13T11:29:00+09:00
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# ASC-0081 Provider Fallback Execution Binding

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. The operator has accepted this contract through the founder-delegated
Codex operator loop. This is now the bounded execution surface for making Hive
dispatch provider workers replaceable across provider CLIs and local LLM
substrates.

## Source Goal Packets

- `rg_20260513T001129_b90c2e48bf82` from `CapabilityOS`: Hive Codex provider-loop read-only sandbox cannot access repo
- `rg_20260513T001226_aced75f2adb3` from `hivemind`: Hive Claude provider-loop lacks allowlisted permission mode for execution
- `rg_20260513T002158_4ef84e7c18bc` from `hivemind`: AIOS writable product-repo provider execution is not yet non-interactive
- `rg_20260513T023628_a7a9988e895f` from `uri`: AIOS Sprint 011 provider execution blocked: Codex worker returned access denied and Claude worker hit usage limit while executing Uri /memory human resource MemoryOS sprint.
- `rg_20260513T091830_710069d191ee` from `uri`: AIOS Sprint 012 provider execution blocked: Claude Code subscription access disabled by organization and Codex CLI returned access denied while executing self-ingest preview-consent sprint.

## Source Evidence

- `rg_20260513T001129_b90c2e48bf82` evidence: `hivemind/.runs/run_20260513_000916_60791d/agents/codex/native/passthrough_01_output.md`
- `rg_20260513T001226_aced75f2adb3` evidence: `hivemind/.runs/run_20260513_001129_1023bd/agents/claude/native/passthrough_01_result.yaml`
- `rg_20260513T002158_4ef84e7c18bc` evidence: `hivemind/.runs/run_20260513_000916_60791d/agents/codex/native/passthrough_01_output.md`
- `rg_20260513T002158_4ef84e7c18bc` evidence: `hivemind/.runs/run_20260513_001129_1023bd/agents/claude/native/passthrough_01_result.yaml`
- `rg_20260513T002158_4ef84e7c18bc` evidence: `hivemind/.runs/run_20260513_001129_1023bd/agents/claude/native/passthrough_03_output.md`
- `rg_20260513T023628_a7a9988e895f` evidence: `.aios/sprint_runs/uri/20260513T023526.json`
- `rg_20260513T023628_a7a9988e895f` evidence: `.aios/sprint_runs/uri/20260513T023544.json`
- `rg_20260513T091830_710069d191ee` evidence: `.aios/sprint_runs/uri/20260513T091756.json`
- `rg_20260513T091830_710069d191ee` evidence: `.aios/sprint_runs/uri/20260513T091809.json`

## Scope

repos:

- `hivemind`
- `CapabilityOS`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
- `docs/contracts/README.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`
- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/AGENTS.md`
- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/local_workers.py`
- `hivemind/tests/test_provider_loop.py`
- `hivemind/tests/test_local_worker_routing.py`
- `hivemind/docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- `.aios/goal_inbox/**`
- `.aios/logs/**`
- `.aios/prompts/**`
- raw export paths
- provider credentials, PINs, tokens, keychains, shell history, or auth stores
- broad child-repo source edits outside the exact `allowed_files` list

## Responsibilities

### hivemind.must_produce

- Provider loop support for `codex`, `claude`, `gemini`, and `local` provider
  identities under the same receipt/status surface.
- Fallback candidate ordering that can name `gemini` and `local` without
  claiming local LLMs are final acceptors.
- Tests proving `gemini` provider-loop preparation and fallback visibility,
  plus local-worker non-final acceptance semantics.

### MemoryOS.must_produce

- Context pack or memory draft candidates only if accepted scope requires it.
- No accepted memory without review.

### CapabilityOS.must_produce

- A recommendation-only provider route that scores and returns fallback agents
  across `codex`, `claude`, `gemini`, and `local`.
- Route output that distinguishes `local` as a bounded local-worker substrate,
  not an unchecked final verifier.
- No provider execution, model launch, network call, or credential handling.

### Hive Mind.must_produce

- Execution plan, provider route, role capsule, receipt, and verification
  evidence for any implementation packet it owns.
- Child-watcher compatible invocation semantics for provider CLI-like workers:
  `codex`, `claude`, `gemini`, and `local`.

### myworld.must_produce

- Child watcher support for selecting and recording `gemini` and `local`
  fallback attempts when CapabilityOS recommends them.
- Result packets that keep `agent_attempts[]`, `fallback_used`, `final_agent`,
  `failure_category`, and privacy fields consistent across all provider
  substrates.
- Tests proving a provider-access failure can route to a non-Claude alternate
  without broadening child repo authority.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_provider_loop.py tests/test_local_worker_routing.py -v
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py tests/test_observation.py -v
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_child_watcher.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract is accepted and uses the exact allowed file list above.
- CapabilityOS `provider-route` can recommend among `codex`, `claude`,
  `gemini`, and `local`.
- Hive provider-loop can prepare/status provider identities for `codex`,
  `claude`, `gemini`, and `local`.
- Child watcher can run or record those provider identities under the same
  attempt schema.
- Local LLM fallback is allowed to draft, summarize, classify, or propose a
  route, but must not be treated as final acceptance unless a separate
  verifier passes.
- Result packets link back to all source goal ids above.
- Verification evidence exists before closeout.

## Stop Conditions

- `fallback_executes_without_contract`
- `provider_secret_leak`
- `role_capsule_missing_rubric`
- `local_llm_used_as_final_acceptor_without_verifier`
- `verification_gate_failed`
- `provider_identity_not_in_route_schema`
- `fallback_attempt_missing_from_result_packet`

## Work Packets

### WP-0081-A — CapabilityOS provider route expansion

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-13
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: none
- brief: |
    Extend the recommendation-only provider route surface so
    `capabilityos.provider_route.v1` can score and return fallback agents for
    `codex`, `claude`, `gemini`, and `local`.

    Required reading:
    - `/home/user/workspaces/jaewon/myworld/AGENTS.md`
    - `/home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_INTERFACE.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
    - `/home/user/workspaces/jaewon/myworld/CapabilityOS/AGENTS.md`

    Allowed files:
    - `CapabilityOS/capabilityos/catalog.py`
    - `CapabilityOS/capabilityos/cli.py`
    - `CapabilityOS/tests/test_cli.py`
    - `CapabilityOS/AGENTS.md`

    Preserve the recommendation-only invariant: CapabilityOS must not execute
    providers, start Ollama, call Gemini/Claude/Codex, read raw logs, or handle
    credentials.

    Verification:
    `cd /home/user/workspaces/jaewon/myworld/CapabilityOS && python -m pytest tests/test_cli.py tests/test_observation.py -v`
- result: `.aios/outbox/CapabilityOS/asc-0081.CapabilityOS.result.json`;
  repo commit `be22e98`.

### WP-0081-B — Hive provider loop substrate expansion

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-13
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: WP-0081-A
- brief: |
    Extend Hive provider-loop substrate declarations so `codex`, `claude`,
    `gemini`, and `local` can be represented through one receipt/status/fallback
    surface. `local` may produce bounded local-worker drafts but must not be
    treated as final acceptance without a verifier.

    Required reading:
    - `/home/user/workspaces/jaewon/myworld/AGENTS.md`
    - `/home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_INTERFACE.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
    - `/home/user/workspaces/jaewon/myworld/hivemind/AGENTS.md`

    Allowed files:
    - `hivemind/hivemind/provider_loop.py`
    - `hivemind/hivemind/hive.py`
    - `hivemind/hivemind/local_workers.py`
    - `hivemind/tests/test_provider_loop.py`
    - `hivemind/tests/test_local_worker_routing.py`
    - `hivemind/docs/AGENT_WORKLOG.md`

    Verification:
    `cd /home/user/workspaces/jaewon/myworld/hivemind && python -m pytest tests/test_provider_loop.py tests/test_local_worker_routing.py -v`
- result: `.aios/outbox/hivemind/asc-0081-hivemind.hivemind.result.json`;
  repo commit `e835f28`.

### WP-0081-C — MyWorld child watcher fallback execution binding

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-13
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: WP-0081-A
- brief: |
    Extend `scripts/aios_child_watcher.sh` so CapabilityOS-recommended fallback
    agents can include `gemini` and `local`, not only the static
    `codex`/`claude` pair. The watcher must record every attempt in
    `agent_attempts[]`, preserve privacy fields, and avoid storing raw provider
    stdout/stderr in result packets.

    Required reading:
    - `/home/user/workspaces/jaewon/myworld/AGENTS.md`
    - `/home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_INTERFACE.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0081-provider-fallback-execution-binding.md`

    Allowed files:
    - `scripts/aios_child_watcher.sh`
    - `tests/test_aios_child_watcher.py`
    - `docs/AIOS_WORK_DISPATCH.md`
    - `docs/AGENT_WORKLOG.md`

    Verification:
    `cd /home/user/workspaces/jaewon/myworld && python -m unittest tests/test_aios_child_watcher.py`
- result: `.aios/outbox/myworld/asc-0081-myworld.myworld.result.json`.

## Receipts

- CapabilityOS result:
  `.aios/outbox/CapabilityOS/asc-0081.CapabilityOS.result.json`
- Hive result:
  `.aios/outbox/hivemind/asc-0081-hivemind.hivemind.result.json`
- MyWorld result:
  `.aios/outbox/myworld/asc-0081-myworld.myworld.result.json`
- CapabilityOS repo durability commit: `be22e98`
- Hive repo durability commit: `e835f28`
- Final monitor: `python scripts/aios_monitor.py assess --json` returned
  `health=clear`.
