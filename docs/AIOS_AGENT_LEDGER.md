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

## 2026-05-11 KST — codex — MyWorld dispatch model

- repo: myworld
- role: implementation
- goal: define how myworld should assign work without becoming a generic worker
  repo.
- changed: `docs/AIOS_WORK_DISPATCH.md`, `docs/README.md`, `AGENTS.md`,
  `docs/AIOS_AGENT_LEDGER.md`
- evidence: docs-only update from operator clarification.
- decision: myworld is the control plane that writes contracts and dispatch
  packets; implementation agents run inside `hivemind/`, `memoryOS/`, or
  `CapabilityOS/` according to ownership.
- risk: unclear ownership can still cause cross-repo edits; use operator
  checkpoints when owner repo is ambiguous.
- next: create `docs/contracts/ASC-0001-*.md` before the next cross-repo sprint.
- status: done

## 2026-05-11 KST — codex — Control tower wording

- repo: myworld
- role: implementation
- goal: clarify the operator's intended metaphor for myworld.
- changed: `docs/AIOS_WORK_DISPATCH.md`, `docs/AIOS_NORTHSTAR.md`,
  `docs/AIOS_AGENT_LEDGER.md`
- evidence: docs-only clarification.
- decision: describe `myworld/` as the AIOS control tower: it coordinates,
  dispatches, holds, and releases work, while implementation happens in the
  owning lower repo.
- risk: none known.
- next: use this metaphor in future contracts and agent onboarding.
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

## 2026-05-11 21:35 KST — claude — ASC-0001 lifecycle proposed -> accepted -> closed (dogfood)

- repo: myworld
- role: review + dogfood operator
- goal: take ASC-0001 (memoryOS<->hivemind loop) through full control-plane
  lifecycle in one session: snapshot 3 repos, review codex's draft, accept,
  dispatch via `scripts/aios_dispatch.py`, run verification gate, close.
- changed: `docs/contracts/ASC-0001-memoryos-hivemind-loop.md` (frontmatter
  status proposed -> accepted -> closed; slug field added; Receipts section
  filled), `docs/contracts/README.md` (index status sync proposed -> accepted
  -> closed), `.aios/inbox/{hivemind,memoryOS}/asc-0001.*.json` (dispatched
  packets), `.aios/outbox/{hivemind,memoryOS}/asc-0001.*.result.json`
  (verification results), `.aios/state/dispatches.jsonl` (created/sent/
  collected events).
- evidence: hivemind verification 1 passed in 1.56s
  (`tests/test_quickstart.py::QuickstartDemoTest::test_memory_loop_demo_closes_isolated_feedback_loop`);
  memoryOS verification 2 passed in 0.29s (k57 reviewed-drafts and json
  privacy tests). Both result packets collected without stop conditions.
  Acceptance commit `a85221b`.
- decision: ASC-0001 closed. The hive<->memory loop is real and executable
  end-to-end through the control-plane dispatch surface. ASC-0002 should be
  CapabilityOS first executable surface (still 0% code, blocking any
  capability route work in hivemind).
- risk: verification packets self-executed by `claude@myworld` because no
  child-repo agent (codex@hivemind, codex@memoryOS) was active; this is
  acceptable for read-only test gates but must not become the default for
  contracts whose work involves writing child-repo code. The dispatch
  packets carry no `task_brief` or `verification_commands` extracted from
  the contract — child agents currently must re-derive their slice from
  the contract body.
- next: (1) operator decides whether to draft ASC-0002 (CapabilityOS first
  executable surface) now or capture dogfood findings first;
  (2) recommend small improvements to `scripts/aios_dispatch.py` packet
  shape (see chat findings list); (3) record the inline `## Work Packets`
  section convention vs JSON dispatch packet relationship in
  `docs/AIOS_WORK_DISPATCH.md`.
- status: done
