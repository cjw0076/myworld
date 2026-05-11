# AIOS Workstreams

This file is the shared ownership map for directing Hive Mind, MemoryOS, and
CapabilityOS from the `myworld` workspace.

## Operating Rule

Codex and Claude coordinate AIOS as a contract-bound ecosystem, not as a single
mixed codebase. Each task must name the target OS, expected artifacts,
verification gate, and handoff owner before implementation starts.

Cross-OS work requires either:

- an explicit operator instruction that assigns the boundary crossing, or
- an AIOS smart contract that records scope, required artifacts, validation
  gates, stop conditions, and the next operator checkpoint.

## Lead Split

`claude@myworld` and `codex@myworld` together act as the AIOS **operator**. They realize the founder's ideas, wake child-repo agents (`codex@hivemind`, `codex@memoryOS`, `codex@CapabilityOS`), receive their work summaries, handle problems, and propose the next task. The founder's role is the idea source and the ultimate override; routine acceptance, dispatch, release/hold/escalate decisions belong to the operator pair.

| Lead | Primary responsibility | Must produce |
| --- | --- | --- |
| Codex (`codex@myworld`) | implementation, tests, CLI behavior, fixtures, execution receipts, verification, dispatch payload authoring | narrow patches, test reports, run receipts, capability observations |
| Claude (`claude@myworld`) | architecture review, policy semantics, lifecycle critique, privacy wording, coherence review, contract authoring, ledger writing | review notes, design objections, boundary checks, contracts, ledger entries |
| Operator (claude+codex jointly) | acceptance flips, dispatch via `aios_dispatch.py`, release/hold/retry/escalate, problem handling, next-task selection | accepted contracts, dispatched packets, collected results, escalation requests when scope, privacy, or vision is in doubt |
| Founder (재원) | ideas, north star, vision corrections, ultimate override, privacy authority | direction statements, vision/scope corrections, escalation resolutions |

Codex should not silently settle memory policy or review lifecycle decisions that belong to MemoryOS/Claude review. Claude should not bypass Hive Mind execution authority for concrete implementation. Both operators must escalate to the founder when:

- a contract changes scope policy, privacy boundaries, or OS ownership rules
- a stop condition triggers without an obvious in-policy resolution
- the next-task selection requires a vision call (which OS to grow, what to defer)
- a child-repo agent returns a result that contradicts the founder's stated direction

## OS Ownership

| OS | Repository | Owns | Does not own |
| --- | --- | --- | --- |
| Hive Mind | `hivemind/` | execution, scheduling, provider CLI wrapping, proofs, verification, receipts | accepted memory, capability catalog authority |
| MemoryOS | `memoryOS/` | memory, context paging, provenance, review lifecycle, retrieval traces | execution harness, tool binding decisions |
| CapabilityOS | `CapabilityOS/` | capability maps, routing recommendations, tool/MCP/API/skill catalogs, fallback plans | direct execution, memory acceptance |

## Required Preflight

Before touching a repo:

1. Read the root AIOS docs and that repo's role file.
2. Read the repo-local `AGENTS.md`, `CLAUDE.md`/`CODEX.md` when present, and
   local `docs/AGENT_WORKLOG.md` or `docs/WORKSTREAMS.md`.
3. Check repo-local `git status --short` from the target repo, not broad parent
   workspace status.
4. Record a starting entry in the target repo worklog for implementation work,
   or in `docs/AIOS_AGENT_LEDGER.md` for cross-OS planning and decisions.

## Default Task Flow

1. MemoryOS offers a context pack and retrieval trace.
2. CapabilityOS offers a capability plan and fallback plan.
3. Hive Mind converts those offers into an executable plan with verification
   gates.
4. Codex implements the agreed concrete slice and runs the verification gate.
5. Claude reviews architecture, lifecycle, privacy, and OS-boundary semantics.
6. MemoryOS records memory drafts and review outcomes.
7. CapabilityOS records capability observations linked to receipts.
8. Hive Mind reports final evidence and open checkpoints to the operator.

## Stop Conditions

Stop and ask for an operator checkpoint when any of these occurs:

- scope crosses OS boundaries without a contract or explicit instruction
- repo ownership is ambiguous
- required MemoryOS context or CapabilityOS route is missing for non-trivial
  cross-OS work
- a verification gate fails and the fix would broaden scope
- private exports, secrets, raw transcripts, or local-only data would need to be
  copied into shared docs
- another agent has active edits in the target files and the merge path is not
  obvious

## Current Direction

The active direction is to converge the three repositories into the final AIOS:

- Hive Mind becomes the executor/scheduler/verifier.
- MemoryOS becomes the context/provenance/review substrate.
- CapabilityOS becomes the router/catalog/fallback planner.

Work should move toward a closed loop:

```text
goal -> context -> route -> execute -> verify -> remember -> observe -> report
```
