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

| Lead | Primary responsibility | Must produce |
| --- | --- | --- |
| Codex | implementation, tests, CLI behavior, fixtures, execution receipts, verification | narrow patches, test reports, run receipts, capability observations |
| Claude | architecture review, policy semantics, lifecycle critique, privacy wording, coherence review | review notes, design objections, boundary checks, operator questions |
| Operator | release/revise/cancel decisions and scope escalation | checkpoint decisions |

Codex should not silently settle memory policy or review lifecycle decisions
that belong to MemoryOS/Claude review. Claude should not bypass Hive Mind
execution authority for concrete implementation.

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
