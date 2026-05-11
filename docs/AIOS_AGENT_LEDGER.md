# AIOS Agent Ledger

This is the shared append-only log for the MyWorld AIOS ecosystem. Use it for
cross-repo decisions, OS-boundary changes, and final-AIOS design records.

For repo-local implementation details, also update that repo's own worklog.

## 2026-05-11 KST — codex — MyWorld AIOS shared docs bootstrap

- repo: myworld
- role: implementation
- goal: create root-level files that Hive Mind, MemoryOS, and CapabilityOS
  agents can read while converging on the final AIOS.
- changed: `AGENTS.md`, `docs/README.md`, `docs/AIOS_NORTHSTAR.md`,
  `docs/AIOS_AGENT_PROTOCOL.md`, `docs/AIOS_SMART_CONTRACT.md`,
  `docs/AIOS_AGENT_LEDGER.md`, `docs/agents/*.md`
- evidence: docs-only bootstrap from operator instruction.
- decision: shared agent records need more than `when/repo/agent`; they should
  include role, goal, changed artifacts, evidence, decision, risk, next owner,
  and status.
- risk: myworld root is not currently a clean standalone git repo; avoid
  broad git operations from this root.
- next: each OS agent should add future cross-repo records here and keep
  repo-local worklogs in sync.
- status: done

## 2026-05-11 20:55 KST — codex — Shared docs usage adopted

- repo: myworld
- role: operator
- goal: confirm how agents should use `/home/user/workspaces/jaewon/myworld/docs`
  while working across Hive Mind, MemoryOS, and CapabilityOS.
- changed: `docs/AIOS_AGENT_LEDGER.md` entry only.
- evidence: read `docs/README.md`, `AIOS_NORTHSTAR.md`,
  `AIOS_AGENT_PROTOCOL.md`, `AIOS_SMART_CONTRACT.md`,
  `AIOS_AGENT_LEDGER.md`, and `docs/agents/*.md`.
- decision: root docs are the shared cross-OS contract surface. For future
  cross-OS work, read them before acting; keep implementation details in each
  repo; write repo-local worklogs for local changes; write this ledger for
  cross-repo decisions, boundary changes, and AIOS-level contracts.
- risk: root `myworld` may not be a clean standalone git repo, so avoid broad
  root-level git operations.
- next: when a task crosses OS boundaries, draft or reference an AIOS smart
  contract and stop at an operator checkpoint if scope, permissions, or required
  artifacts are ambiguous.
- status: done

## 2026-05-11 21:08 KST — codex — Codex and Claude AIOS direction protocol

- repo: myworld
- role: planner
- goal: establish how Codex and Claude should jointly direct Hive Mind,
  MemoryOS, and CapabilityOS.
- changed: `docs/WORKSTREAMS.md`, `docs/AIOS_AGENT_LEDGER.md`
- evidence: read root AIOS docs plus `docs/agents/HIVEMIND_AGENT.md`,
  `docs/agents/MEMORYOS_AGENT.md`, and
  `docs/agents/CAPABILITYOS_AGENT.md`.
- decision: Codex leads implementation, tests, execution receipts, and
  verification; Claude leads architecture critique, policy/lifecycle review,
  privacy wording, and OS-boundary coherence. Cross-OS work remains
  contract-bound and must preserve repo ownership.
- risk: broad parent workspace git status includes many unrelated changes; use
  repo-local status checks before implementation.
- next: for the next concrete AIOS task, create or reference an AIOS smart
  contract, then route MemoryOS context, CapabilityOS recommendations, and Hive
  Mind execution in that order.
- status: done

## 2026-05-11 21:17 KST — codex — MyWorld root split to superproject

- repo: myworld
- role: implementation
- goal: detach `myworld/` from the parent workspace git root and make it the
  AIOS coordination root.
- changed: `.gitignore`, `.gitmodules`, `docs/AIOS_AGENT_LEDGER.md`,
  parent `../.gitignore`
- evidence: `git rev-parse --show-toplevel` now resolves to
  `/home/user/workspaces/jaewon/myworld` after initialization.
- decision: keep `hivemind/`, `memoryOS/`, and `CapabilityOS/` as independent
  git repositories referenced from `myworld` as submodule-style gitlinks;
  do not absorb their working trees into the root repo.
- risk: subrepos may have local uncommitted changes; root commit should record
  only the subrepo HEAD gitlinks and not alter subrepo worktrees.
- next: commit the new `myworld` superproject root, then continue OS-specific
  work inside each child repository.
- status: done
