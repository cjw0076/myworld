---
contract_id: ASC-0030
slug: capabilityos-web-research-route
status: closed
goal: Add a recommendation-only CapabilityOS web research route so AIOS can deliberately use broad internet search with source and privacy guardrails.
created: 2026-05-12 03:20 KST
accepted: 2026-05-12 03:20 KST
closed: 2026-05-12 03:27 KST
---

# ASC-0030 CapabilityOS Web Research Route

## Why Now

The operator clarified that CapabilityOS should have broad internet/web reach.
The right first step is not to let CapabilityOS itself browse indefinitely.
CapabilityOS owns capability routing, so it should declare when a task needs
web research, what search surface is appropriate, what source policy applies,
and what evidence must come back. Execution still belongs to Codex/Hive or an
explicit provider/tool runner under contract.

## Scope

repos:

- `CapabilityOS`

allowed_files:

- `CapabilityOS/AGENTS.md`
- `CapabilityOS/README.md`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/tests/fixtures/capabilities.json`
- `docs/contracts/ASC-0030-capabilityos-web-research-route.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `.aios/logs/**`
- `.aios/outbox/**`
- `.aios/inbox/**`
- `.env`
- raw export paths
- browser caches or downloaded web archives

## Responsibilities

### capabilityos.must_produce

- A default catalog card for broad web research/search.
- A CLI surface that returns a deterministic web research route plan.
- The route plan must be recommendation-only and must not open network
  connections.
- The plan must include source policy, allowed tool families, forbidden
  behaviors, privacy notes, and evidence requirements.
- `audit` may list the web card under `network_required`, but
  `execution_enabled` must remain empty.

### hive_mind.must_produce

- No source change in this contract. Future Hive packets may consume the route
  plan to execute web research through the harness.

### memoryos.must_produce

- No source change in this contract. Future MemoryOS packets may decide which
  web-derived evidence becomes durable memory candidates.

### myworld.must_produce

- Contract, dispatch, release, goal update, and ledger closeout.

## Design Answers

Q1. Does CapabilityOS get direct broad internet execution?

Not in this contract. It gets broad web *routing authority*: it can decide that
internet research is needed and return a policy-bound route. Direct browsing
remains with the executing agent/tool layer so every query, source, and quote
can be audited.

Q2. How broad is broad?

Broad means not limited to local repo docs. The route can recommend general web
search, source opening, page finding, and official-primary-source preference.
It still forbids secrets, raw private exports, credentialed browsing, and
background crawling.

Q3. Why not use MemoryOS first?

MemoryOS should store reviewed web-derived knowledge later. First,
CapabilityOS needs to expose the capability route so future MemoryOS import can
distinguish web evidence from local repo evidence.

## Verification Gate

Run:

```bash
cd CapabilityOS
python -m pytest tests/test_cli.py -v
python -m capabilityos.cli web-route --task "research current web evidence for AIOS capability routing" --json
python -m capabilityos.cli recommend --task "search the internet for current API docs and cite sources" --json
python -m capabilityos.cli audit --json
```

Pass criteria:

- Tests pass.
- `web-route` returns `contract=capabilityos.web_research_route.v1`.
- `web-route` returns `recommendation_only=true` and no execution result body.
- `recommend` ranks the web research card for web/search/current-doc tasks.
- `audit` reports the web research card in `network_required` and keeps
  `execution_enabled=[]`.

## Stop Conditions

- `network_execution_inside_capabilityos`: CapabilityOS opens URLs, calls web
  APIs, launches browsers, or downloads pages.
- `unbounded_browse_plan`: route lacks source limits, evidence requirements, or
  stop rules.
- `privacy_violation`: route suggests sending raw private exports, secrets, or
  local sensitive data to web.
- `implicit_memory_acceptance`: web-derived facts are stored as accepted memory
  without MemoryOS review.
- `hive_authority_bypass`: CapabilityOS directly executes Hive-owned work.

## Receipts

- CapabilityOS commit: `20ccbbc`.
- Dispatch: `.aios/inbox/CapabilityOS/asc-0030.CapabilityOS.json`.
- Result packet: `.aios/outbox/CapabilityOS/asc-0030.CapabilityOS.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0030
  --reason asc_0030_capabilityos_web_research_route_verified`.
- Verification:
  - `python -m pytest tests/test_cli.py -v` passed 11/11.
  - `python -m pytest` passed 16/16.
  - `python -m capabilityos.cli web-route --task "research current web
    evidence for AIOS capability routing" --json` returned
    `contract=capabilityos.web_research_route.v1`,
    `recommendation_only=true`, and
    `capabilityos_executes_network=false`.
  - `python -m capabilityos.cli recommend --task "search the internet for
    current API docs and cite sources" --json` ranked
    `cap_web_research_route` first.
  - `python -m capabilityos.cli audit --json` returned
    `execution_enabled=[]` and
    `network_required=["cap_web_research_route"]`.

## Work Packets

### WP-0030-A — Codex@CapabilityOS implements web research route

- target_agent: codex
- target_repo: CapabilityOS
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: none
- brief: |
    Add a recommendation-only broad web research capability and CLI route plan
    to CapabilityOS. Preserve the invariant that CapabilityOS does not execute
    tools or open network connections. Update tests and docs, then return a
    result packet through the ASC-0030 verification gate.
- result: `.aios/outbox/CapabilityOS/asc-0030.CapabilityOS.result.json`
