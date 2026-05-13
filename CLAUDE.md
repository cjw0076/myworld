# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Workspace Is

`myworld/` is the **AIOS control plane**. It does not host implementation code — it issues goals, contracts, and cross-repo handoffs that the three sibling OS repos execute against:

- `hivemind/` — execution layer: scheduler, provider CLI harness, verification gates, run receipts. (Own git repo, own `CLAUDE.md`.)
- `memoryOS/` — memory substrate: append-only graph, draft/review lifecycle, provenance, retrieval traces. (Own git repo, own `CLAUDE.md`.)
- `CapabilityOS/` — capability map: catalog of providers/MCPs/skills/APIs, routing recommendations, fallback plans. (Own git repo. Currently docs-only — no Python package yet.)

The workspace root itself is **not a clean standalone git repo** — avoid broad root-level git operations. Run git commands inside the specific sibling repo you are touching.

Each sibling has its own `CLAUDE.md` with repo-specific commands, source layout, and invariants. **Read the sibling's `CLAUDE.md` first** when working inside that sibling — do not re-derive its commands from this file.

## Required Reading Before Cross-Repo Work

When a task crosses repo boundaries (or you are unsure which repo owns it), read in this order before touching code:

1. `AGENTS.md` — workspace entry point and ownership boundaries
2. `docs/AIOS_NORTHSTAR.md` — final system shape and the three OS roles
3. `docs/AIOS_AGENT_PROTOCOL.md` — the durable-record format for cross-repo entries
4. `docs/AIOS_SMART_CONTRACT.md` — the contract shape for multi-OS tasks
5. `docs/AIOS_AGENT_LEDGER.md` — append-only cross-repo decision log
6. `docs/WORKSTREAMS.md` — Codex/Claude lead split, OS ownership, default task flow
7. `docs/contracts/README.md` — contract directory index, file shape, lifecycle
8. The role file for the repo you are touching:
   - `docs/agents/HIVEMIND_AGENT.md`
   - `docs/agents/MEMORYOS_AGENT.md`
   - `docs/agents/CAPABILITYOS_AGENT.md`

For repo-local work that does not cross OS boundaries, the sibling's own docs (`hivemind/docs/`, `memoryOS/docs/`) are sufficient.

## Ownership Boundaries (Do Not Mix)

These boundaries are contractual. Do not silently move responsibility across them:

- **Hive Mind** owns execution authority. It plans, runs, verifies, and produces receipts. It does **not** decide what becomes accepted memory and does **not** install/bind external tools without a contract.
- **MemoryOS** owns the memory and review lifecycle. It proposes memory drafts but never silently accepts them. It does **not** execute tools as a substitute for Hive Mind.
- **CapabilityOS** owns recommendations and binding plans. In early versions it does **not** directly execute or install external tools, and does **not** override Hive Mind's execution authority.

If a task is ambiguous about ownership, stop at an operator checkpoint rather than guessing.

## Control Plane Workflow

`claude@myworld` + `codex@myworld` jointly act as the AIOS **operator**. The founder (재원) provides ideas and the ultimate override; routine acceptance, dispatch, release/hold/escalate decisions belong to the operator pair. See `docs/WORKSTREAMS.md` for the full role split and escalation rules.

A non-trivial cross-OS task flows through this workspace as:

1. Founder states an idea at the workspace root, OR an operator surfaces a next task from the prior contract's results.
2. Operator drafts an AIOS smart contract under `docs/contracts/ASC-NNNN-<slug>.md` (shape per `docs/AIOS_SMART_CONTRACT.md`). Status starts `proposed`.
3. Operator accepts → status `accepted`. (No founder approval needed unless an escalation rule from `WORKSTREAMS.md` triggers.)
4. Operator dispatches via `python scripts/aios_dispatch.py create … && send …` — packets land in `.aios/inbox/<repo>/`.
5. Child-repo agent (codex@hivemind, codex@memoryOS, codex@CapabilityOS, or codex@myworld for myworld-scoped work) wakes, picks up the inline `## Work Packets` from the contract or the JSON inbox packet, and implements **inside the target sibling repo**.
6. Child agent writes a result packet to `.aios/outbox/<repo>/`. Operator runs `aios_dispatch.py collect`.
7. Operator runs the verification gate (or watcher V1 once ASC-0004 lands), confirms pass, fills receipts, flips status to `closed`, and appends a single ledger entry in `docs/AIOS_AGENT_LEDGER.md`.
8. Operator proposes the next contract.

The control plane never edits sibling-repo source code directly. It edits contracts, agent docs, the ledger, dispatch state under `.aios/`, and operator-owned scripts under `scripts/`.

## Cross-Repo Logging

When a change crosses OS boundaries (e.g. Hive Mind work that requires a MemoryOS schema change, or a contract that names two repos), append an entry to `docs/AIOS_AGENT_LEDGER.md` using the template in `docs/AIOS_AGENT_PROTOCOL.md`. Required fields: `when, repo, agent, role, goal, changed, evidence, decision, risk, next, status`. Entries are append-only; do not edit prior records.

For repo-local changes, also update that repo's own worklog (e.g. `memoryOS/docs/AGENT_WORKLOG.md`).

## Conventions

- Conversation language: Korean is preferred; code identifiers and filenames stay in English.
- Do **not** paste raw private exports, prompts, stdout/stderr bodies, or secrets into shared docs. Link to evidence by file path, receipt id, or trace id.
- Do **not** import quantum Paper #4 scope into MyWorld. Quantum is a reference domain only; MyWorld is the agent-memory / ontology / reflective-system workspace.
- Operator checkpoints are a valid output, not a failure.

## AIOS 발전 지원 — Claude Self-Observation Protocol

Claude Code가 myworld에서 meaningful한 operator 작업을 수행할 때마다 아래를 따른다.

### 1. 자가 관찰 의무 (Self-Observation Duty)

세션 종료 전 또는 task 전환 시, 다음 중 하나라도 해당되면 `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`에 항목 추가:

- 새로운 tool 조합 패턴 발견 (병렬화, 위임 결정, context 보호 전략)
- 반복 실패 패턴 또는 그 회복법
- AIOS가 흡수할 수 있는 행동 구조가 명확해진 경우
- 창업자 에스컬레이션이 필요했던 경우

형식은 파일 내 기존 포맷 준수. 500단어 이하.

### 2. AIOS 흡수 관점에서의 행동 원칙

Claude는 myworld에서 일하면서 AIOS의 역설계 대상임을 인식한다:

**task 관리**: 다단계 작업은 TaskCreate로 명시화 → 상태를 in_progress/completed로 명시 전환. context compaction 이후에도 이 상태가 재주입되므로 연속성이 유지됨. AIOS contract lifecycle의 원형.

**병렬 실행**: 독립적인 tool call은 단일 메시지에서 동시에 발행. 순서 의존성이 없으면 무조건 병렬. AIOS hive dispatch의 원형.

**위임 임계값**: "main context를 오염시키는 긴 결과"는 Agent 도구로 격리. 짧은 탐색은 Bash grep 직접. AIOS agent 선택 로직의 원형.

**메모리 기록**: ephemeral task 상태는 memory에 쓰지 않음. 미래 세션에 유효한 패턴, 결정, 역할 정보만 MEMORY.md. AIOS MemoryOS write trigger의 원형.

### 3. 새 패턴 발견 시 라우팅

Claude가 새 tool 조합, 실패 회복법, 에스컬레이션 패턴을 발견하면:

1. self-observation log에 기록 (즉각)
2. 해당 패턴이 AIOS 계약으로 발전할 수 있으면 `docs/AIOS_PROVIDER_ABSORPTION.md`에 "Candidate" 섹션 추가
3. 창업자 결정이 필요하면 escalation log에 별도 항목

이 protocol의 목적: Claude CLI를 쓰면 쓸수록 AIOS가 학습하는 구조를 만드는 것.
