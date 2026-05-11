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
