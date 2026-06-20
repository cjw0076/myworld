# AIOS Standards

Concise, agent-scannable operating standards for the AIOS planner.
Absorbed from buildermethods/agent-os "Discover Standards" pattern.
Injected before planning. Keep every rule one line.

## Authority & Safety

- Recommendation-only: never bind, install, or auto-accept without explicit approval.
- Draft-first: any memory or artifact write produces a draft; acceptance requires review.
- Fail-closed: if plan exceeds granted scope, reject before running — do not attempt.
- Privacy boundary: never read/write `_from_desktop/`, `dain/`, `minyoung/`, `.aios/secrets/`.
- Append-only audit: never edit ledger or contract records destructively.
- Named exit: every loop or pipeline must have a documented stop condition.
- Operator override: always preserve a path for a human to intervene.

## Planning Discipline (spec-kit pattern)

- Goal → spec → steps → execute. Never skip spec.
- Each step: one tool, one purpose, one verifiable output.
- Checkpoint required for any write that is hard to reverse.
- No placeholder content in fs.write: include the full document body, never "TBD" or "done".
- Prefer read-verify-write over write-and-hope.

## Canonical Shape

- Kernel layer: `aios <goal>` → planner → ContractObject → runtime → receipts.
- Organs: MemoryOS (memory), CapabilityOS (routing), HiveMind (execution), GenesisOS (divergence).
- Products run above the kernel; providers run below as replaceable vendors.
- MyWorld controls and routes; child repos implement their organs.

## Provider Hygiene

- claude: nuanced reasoning, docs, review, memory tasks.
- codex: implementation, tests, build-fix, debug.
- ollama (local): background cognition, classification, quick drafts.
- No LiteLLM (banned: supply chain incident 2026-03-24).

## Provenance

- Every result must cite its evidence_refs (which files read, which steps ran).
- Never claim completion without a receipt.
- Run receipts live in `.aios/runtime/receipts/`.
