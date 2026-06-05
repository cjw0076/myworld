---
contract_id: ASC-0225
slug: substrate-boundary-classifier
status: proposed
goal: Make AIOS choose between kernel substrate, Hive execution, CapabilityOS/plugin routing, MemoryOS knowledge retrieval, and GenesisOS challenge before autonomous work expands scope.
created: 2026-06-05T20:08:00+09:00
origin: founder directive — do not rely only on one model; decide whether AIOS should touch OS/process substrate, use agent-friendly plugins, or pull broader knowledge.
---

# ASC-0225 Substrate Boundary Classifier

## Why Now

The founder asked whether AIOS should operate at process/OS depth, expose
agent-friendly plugin surfaces, or use all available knowledge sources. Existing
AIOS docs contain pieces of the answer, but there is no single classifier that
prevents future autonomous work from turning every useful capability into a
kernel feature or every research idea into immediate execution.

This contract proposes the missing boundary rule. It does not execute child
repo work yet.

## Decision

Adopt `docs/AIOS_SUBSTRATE_BOUNDARY.md` as the control-plane classifier:

```text
kernel primitive
  -> Hive execution substrate
  -> CapabilityOS/plugin route
  -> MemoryOS/external knowledge route
  -> GenesisOS challenge
```

The classifier is deliberately conservative. Kernel escalation is allowed only
for authority, lifecycle, isolation, persistence, receipt integrity, rollback,
or privacy guarantees that cannot be provided by plugin/tool routing alone.

### Assumptions

- AIOS gains more from governed boundaries than from absorbing every useful
  tool into the kernel.
- Agent-friendly plugin and contract surfaces can preserve creativity without
  giving every idea execution authority.
- External knowledge is valuable when cited and scoped, but noisy when treated
  as always-on memory.
- Process/OS-level work is justified only when it creates a reusable guarantee
  that ordinary agents, plugins, or tools cannot provide.

Counter branch:

AIOS could instead become a full workflow/runtime engine that owns provider
adapters, background workers, local LLM cognition, MCP tools, memory providers,
web research, and execution scheduling in one integrated kernel. That path may
produce faster short-term autonomy, but it would also concentrate permission,
credential, privacy, and failure-mode risk. This contract rejects that default
until a concrete outside-domain proof shows the plugin/contract boundary is too
weak for a specific guarantee.

### Plain Language

AIOS should not grab deeper computer control just because deeper control is
possible. It should first ask: "Is this a safety/lifecycle/receipt problem, or
is this a tool/knowledge/model choice?" If it is a tool or knowledge choice,
keep it as a plugin route, research receipt, memory draft, or challenge note.
Only make a kernel feature when the system needs a hard guarantee like stop,
rollback, privacy, process survival, or auditable execution.

### Cross-Domain Frame

Use an airport control-tower frame:

- The tower owns clearance, route, hold, release, and incident records.
- Airlines and aircraft own flight execution.
- Weather, maps, radar, and maintenance systems feed evidence into decisions.
- The tower does not become every airplane, weather station, and repair shop.

AIOS should behave the same way. It coordinates authority and evidence; it does
not need to absorb every specialized system.

### Time Horizons

- 1 hour: proposed classifier exists and stops the next autonomous turn from
  silently expanding kernel authority.
- 1 week: accepted contracts include the substrate/surface/knowledge fields,
  making plugin-vs-kernel decisions reviewable.
- 1 year: AIOS has a small stable kernel with many swappable provider, plugin,
  memory, and research routes above it.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_SUBSTRATE_BOUNDARY.md`
- `docs/contracts/ASC-0225-substrate-boundary-classifier.md`
- `docs/AIOS_BUILD_METHOD.md`
- `docs/AIOS_PRODUCTION_PRAXIS.md`
- `docs/AIOS_SMART_CONTRACT.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials
- raw exports
- private history stores
- child repo implementation files
- CapabilityOS catalog edits without a follow-up accepted implementation contract
- Hive process/kernel edits without a follow-up accepted implementation contract

## AIOS Role Evidence

### MemoryOS

- required: no accepted memory.
- possible output: draft memory candidate only if this classifier later becomes
  a reviewed operator rule.

### CapabilityOS

- required: recommendation-only. The classifier says when a tool/plugin/MCP/API
  route should be recommended instead of executed.

### GenesisOS

- required: challenge frame included in the classifier. Unstable assumptions,
  language, or final-state definitions route to GenesisOS before execution.

### Hive Mind

- required: no execution in this proposal. Follow-up implementation must use
  Hive receipts if it touches process lifecycle, provider loops, or watchers.

### MyWorld

- required: publish the boundary classifier and ledger the decision.

## Required Work

- Add a substrate boundary document that answers:
  - when to touch process/OS-level substrate,
  - when to keep work plugin/capability-friendly,
  - when to retrieve broad external knowledge,
  - when to route to GenesisOS challenge,
  - which stop conditions prevent scope creep.
- Cite external architecture evidence at a summary level without copying raw
  source bodies.
- Add the gate fields to the smart-contract template and production praxis
  envelope:
  - `substrate_level`
  - `surface_type`
  - `knowledge_scope`
  - `authority`
  - `owner_repo`
  - `required_receipts`
- Add a dispatch decision table that preserves these boundaries:
  - CapabilityOS does not execute.
  - MemoryOS remains draft-first.
  - GenesisOS challenges but does not select final truth.
  - Hive execution requires receipts.
- Record a worklog and ledger entry.
- Leave this contract proposed unless the operator explicitly accepts and
  dispatches a classifier implementation.

## Verification Gate

```bash
git diff --check
python scripts/aios_monitor.py assess --json
test -f docs/AIOS_SUBSTRATE_BOUNDARY.md
test -f docs/contracts/ASC-0225-substrate-boundary-classifier.md
```

Pass criteria:

- Boundary doc exists and names the five ownership layers.
- Contract remains `status: proposed`.
- No child repo implementation files are changed.
- Dirty pre-existing `uri` and runtime `artifacts/` state are preserved.

## Stop Conditions

- `kernel_scope_creep`
- `plugin_executes_without_contract`
- `capabilityos_executes_tool`
- `memory_auto_accepts_research`
- `provider_truth_without_verifier`
- `raw_private_evidence_leak`
- `child_repo_implementation_without_dispatch`

## Follow-Up Implementation Candidate

After operator acceptance, a separate implementation contract can add a
machine-readable classifier command:

```bash
python scripts/aios_boundary_classifier.py \
  --question "Should AIOS daemonize local LLM background cognition?" \
  --json
```

That follow-up should produce a JSON decision with `layer`, `owner`,
`required_artifacts`, `stop_conditions`, and `next_contract_kind`.
