# AIOS Agent Protocol

Agents should leave records that another agent can evaluate without reading the
entire conversation. Use durable files, bounded summaries, and explicit
handoffs.

Protocol records implement `docs/AIOS_DNA.md`, especially Invariant 3 (no
record destroyed), Invariant 4 (named exits), and Invariant 5 (provenance
chain). When an agent creates a cross-repo or authority-bearing contract, cite
the relevant DNA invariant in the contract body.

## Required Log Fields

`when`, `repo`, and `agent` are necessary but not sufficient. Each meaningful
entry should include:

- `when`: ISO date/time or date.
- `repo`: `hivemind`, `memoryOS`, `CapabilityOS`, `myworld`, or external path.
- `agent`: `codex`, `claude`, `local-llm`, `operator`, or another explicit name.
- `role`: implementation, review, operator, research, local-worker, or planner.
- `goal`: what this entry was trying to advance.
- `changed`: files, docs, commands, contracts, or ledgers changed.
- `evidence`: tests, CLI output summary, receipts, traces, or review source.
- `decision`: accepted design decision or unresolved question.
- `risk`: privacy, scope, correctness, timeout, ownership, or overclaim risk.
- `next`: recommended next action and owner.
- `status`: proposed, in_progress, done, blocked, superseded, or rejected.

## Entry Template

```md
## YYYY-MM-DD HH:MM TZ — <agent> — <short title>

- repo: <hivemind|memoryOS|CapabilityOS|myworld>
- role: <implementation|review|operator|research|planner>
- goal: <one sentence>
- changed: <files or artifacts>
- evidence: <tests, receipts, traces, links, or "docs-only">
- decision: <decision or "none">
- risk: <risk or "none known">
- next: <next owner/action>
- status: <done|blocked|proposed|superseded>
```

## Writing Rules

- Prefer append-only records.
- Do not paste raw private exports, prompts, stdout/stderr bodies, secrets, or
  local-only sensitive paths.
- Link to evidence by file path, receipt id, trace id, or command summary.
- If an agent changes another repo, name both the source repo and target repo.
- If a task crosses OS boundaries, create or reference an AIOS smart contract.
- If the contract is ambiguous, stop at an operator checkpoint.
