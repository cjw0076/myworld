# AIOS Governance Model

AIOS is allowed to become powerful only if it becomes more accountable at the
same time. The long-term target is not unchecked autonomy. The target is an
operating system that can coordinate enterprise-scale and sovereign-AI
workflows while preserving authority, evidence, consent, privacy, rollback, and
human checkpoints.

Canonical constitution: `docs/AIOS_DNA.md`. Governance readiness below is a
phenotype of the DNA invariants, especially Invariant 1 (decide before acting),
Invariant 5 (provenance chain), Invariant 6 (operator override), Invariant 7
(private-gated data), and Invariant 8 (classify before committing).

## Post-L6 Readiness

The base readiness model proves the cross-OS loop can repeat. Governance
readiness starts after L6.

```text
L7 accountable authority
  AIOS can state who authorized a task, which repo owns execution, what scope
  is allowed, which stop conditions apply, and where the audit record lives.

L8 resource and capability governance
  AIOS can route tools, web, providers, APIs, memory, and child agents through
  explicit budgets, risk notes, fallback plans, and forbidden-use rules.

L9 organizational governance
  AIOS can coordinate multiple workstreams with role ownership, ledgers,
  dispatch state, review checkpoints, and cross-repo handoffs without relying
  on chat memory.

L10 sovereign-scale simulation readiness
  AIOS can model a sovereign-AI operating stack in simulation: policy,
  resource allocation, audits, public evidence, legal/safety checkpoints, and
  reversible execution. It does not claim real-world legal sovereignty.
```

## Authority Rules

- Human operator authority is the root authority.
- Codex and Claude may act as delegated operators only when the contract,
  ledger, or direct instruction grants that role.
- Child repos own implementation in their domains.
- CapabilityOS recommends capabilities and routes; it does not silently execute
  tools.
- MemoryOS records and reviews memory; it does not silently accept facts.
- Hive Mind owns execution orchestration and verification.
- Any ambiguous high-authority action stops at a checkpoint.

## Resource Rules

Every non-trivial resource route should identify:

- capability or tool family
- owner repo
- risk class
- privacy class
- cost or budget class
- fallback route
- evidence required
- stop conditions

## Human Checkpoints

Human checkpoint rules are mandatory for:

- private or personal data use
- credentialed external systems
- paid APIs or irreversible spending
- legal, medical, financial, or employment-impacting outputs
- public communication on behalf of a person or organization
- attempts to claim or exercise real-world authority
- child repo scope expansion beyond an accepted contract

## Anti-Overclaim Rules

- Do not call AIOS sovereign because it has scripts.
- Do not call AIOS enterprise-ready because it has dispatch packets.
- Do not call AIOS autonomous because a loop is running.
- Do not claim governance readiness without authority, audit, resource, and
  checkpoint evidence.
- Do not optimize institutional power without reversibility and review.
