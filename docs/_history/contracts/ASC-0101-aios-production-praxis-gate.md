---
contract_id: ASC-0101
slug: aios-production-praxis-gate
status: closed
goal: Make AIOS production work require explicit MemoryOS context, CapabilityOS routing, GenesisOS reframing, Hive verification, and modality/provider specialization before implementation begins.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder correction
closed: 2026-05-13 KST
origin: founder critique 2026-05-13 KST - "서로가 잘하는 것을 하나도 하지 않고 있어"
---

# ASC-0101 AIOS Production Praxis Gate

## Diagnosis

This is both an agent-practice issue and an AIOS-system issue, but the system
issue is primary.

If AIOS depends on a specific agent remembering to use MemoryOS, CapabilityOS,
GenesisOS, plugins, MCPs, web resources, multimodal perception, asset
generation, and Hive verification, then AIOS is only a convention. The OS must
make the correct collaboration pattern the path of least resistance.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0101-aios-production-praxis-gate.md`
- `docs/AIOS_PRODUCTION_PRAXIS.md`
- `scripts/aios_work_praxis.py`
- `tests/test_aios_work_praxis.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files
- generated image assets
- UI application files

## Required Praxis

Before production creative or engineering work, AIOS must produce a bounded
praxis envelope:

- `memory_context`: what MemoryOS says matters from accepted/provenanced
  history.
- `capability_routes`: what CapabilityOS recommends, including MCP/plugins,
  APIs, provider CLIs, local models, and fallback paths.
- `external_resource_check`: what current outside resources or primary docs
  were checked when the answer depends on current tool/API/model behavior.
- `genesis_reframe`: how GenesisOS mutates the prompt, detects the real need,
  names discomfort/friction, and proposes alternative framings.
- `hive_execution_plan`: what Hive executes, how it verifies, and what receipt
  proves completion.
- `specialist_assignment`: which agent/model/tool is used for its strength:
  Codex for code and visual/multimodal/asset work, Claude for large codebase
  topology and architectural critique, local LLM for cheap extraction/drafts,
  web/MCP/API tools for current external facts.

## Why CapabilityOS And GenesisOS Need High Freedom

CapabilityOS needs high freedom before execution because capability discovery
is inherently expansive. It should search tools, APIs, MCP servers, provider
CLIs, local models, reference implementations, and fallback routes. Its freedom
is exploratory and routing-oriented, not execution authority.

GenesisOS needs high freedom before execution because creative progress often
comes from escaping the user's first wording. It should translate intent across
agents, mutate assumptions, surface hidden discomfort, create multi-branch
alternatives, and stabilize shared language. Its freedom is semantic and
generative, not authority to change memory lifecycle or execute repo edits.

## Verification Gate

```bash
python -m unittest tests/test_aios_work_praxis.py
python scripts/aios_work_praxis.py draft --task "AIOS visual control app" --json
python scripts/aios_work_praxis.py validate tests/fixtures/praxis/valid_praxis.json --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `memory_context_missing`: production work starts without MemoryOS context or
  an explicit reason it is unavailable.
- `capability_route_missing`: work starts without CapabilityOS route options.
- `genesis_reframe_missing`: creative or ambiguous work starts without
  assumption/friction reframing.
- `external_resource_skipped`: current tool/API/model behavior is assumed from
  memory when it should be checked through plugin/MCP/web/API resources.
- `specialist_flattening`: one agent performs all roles without assigning
  work to the strongest available model/tool.
- `hive_gate_missing`: implementation proceeds without a concrete execution
  receipt or verification gate.

## Receipts

- Created `docs/AIOS_PRODUCTION_PRAXIS.md` to define the required production
  praxis envelope and specialist bias.
- Created `scripts/aios_work_praxis.py` with:
  - `draft --task ... --json`
  - `validate <praxis.json> --json`
- Created `tests/test_aios_work_praxis.py` and
  `tests/fixtures/praxis/valid_praxis.json`.
- External-resource dogfood: queried the Hugging Face plugin for multimodal
  agent/UI workflow papers and recorded the need for plugin/MCP/API evidence
  in the praxis envelope.
- Verification passed:
  - `python -m unittest tests/test_aios_work_praxis.py`
  - `python -m py_compile scripts/aios_work_praxis.py`
  - `python scripts/aios_work_praxis.py draft --task "AIOS visual control app" --json`
  - `python scripts/aios_work_praxis.py validate tests/fixtures/praxis/valid_praxis.json --json`
- Dispatch result:
  - `.aios/outbox/myworld/asc-0101.myworld.result.json` passed and collected.
