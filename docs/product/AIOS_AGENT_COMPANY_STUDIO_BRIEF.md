# AIOS Agent Company Studio Brief

- repo: myworld
- agent: codex@myworld
- status: Gate A product framing, no UI implementation
- related_contract: ASC-0276

## Product Claim

AIOS is the operating system for a company of agents.

The user does not hire a chatbot. The user gives a goal to a small company:
strategy, operations, memory, procurement, research pressure, and quality
control work together under visible contracts.

## User-Visible Departments

| Department | AIOS Organ | User Sees |
| --- | --- | --- |
| Board | MyWorld | goal contract, status, release/hold decisions, next checkpoint |
| Operations | Hivemind | jobs, stages, retries, artifacts, run receipts |
| Institutional Memory | MemoryOS | context used, memory drafts, review queue, retrieval traces |
| Procurement | CapabilityOS | tool/provider recommendation, consent, budget, fallback, denial reason |
| R&D Pressure | GenesisOS | counter-branch, discomfort, assumption challenge, launch risk |
| Quality/Hardening | Claude lane | invariants, stop conditions, privacy and authority critique |
| Product/Growth | Codex lane | visible workflows, interaction design, browser proof |

## Surface Principles

- Show the company state, not raw logs.
- Show draft memory separately from accepted memory.
- Show recommendations separately from execution.
- Show Genesis findings as pressure, not final truth.
- Show credentials as grants and revocations, never secrets.
- Show refusal with a user-resolvable reason.
- Show artifacts and receipts as durable work product.

## First Workflow Shape

```text
user goal
  -> MyWorld job contract
  -> MemoryOS context offer
  -> CapabilityOS route recommendation
  -> Hivemind worker execution
  -> GenesisOS challenge when risk is high
  -> artifacts + receipts
  -> MemoryOS draft review
  -> user-visible closeout
```

## What Must Wait

No `apps/**` work is allowed from this brief. UI waits for:

1. operator selects a concrete visual target through
   `scripts/aios_serving_design_gate.py select --confirmed-by-user`;
2. ASC-0253 or its successor authorizes serving UI implementation;
3. browser proof exists at the claimed viewport sizes;
4. release readiness remains honest until all production serving slices pass.
