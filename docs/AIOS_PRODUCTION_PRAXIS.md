# AIOS Production Praxis

AIOS should not behave like one general agent with extra folders. Production
work must use the OS split deliberately.

## Principle

If a task can be solved by one agent using only local memory and a patch, it may
still be done that way for small maintenance. But creative production,
architecture, product work, external integrations, model/provider routing,
visual design, or ambiguous founder intent must pass through a praxis envelope.

The envelope makes each OS do the work it is good at:

| Layer | Job |
| --- | --- |
| MemoryOS | recover accepted context, provenance, prior failures, and review lifecycle |
| CapabilityOS | route tools, APIs, MCPs, provider CLIs, local models, plugins, and fallback paths |
| GenesisOS | reframe intent, surface hidden discomfort, align shared language, generate alternatives |
| Hive Mind | execute scoped work, schedule agents, verify, and return receipts |
| myworld | hold founder intent, contract scope, dispatch, monitor, and release/hold decisions |

## Specialist Bias

AIOS must assign work by strength:

- Codex: code patches, tests, multimodal inspection, screenshots, visual
  verification, image/asset generation when appropriate.
- Claude: large codebase topology, architectural critique, dependency and
  integration reading, policy/lifecycle review.
- CapabilityOS: provider/tool/API/plugin/MCP/local-model routing and fallback.
- GenesisOS: prompt-prison escape, assumption mutation, language alignment,
  multi-universe branch generation.
- MemoryOS: context packs, accepted memory, provenance, retrieval trace,
  memory draft writeback.
- Hive Mind: execution plan, provider-loop, verification receipts, run
  artifacts.
- Local LLM: cheap extraction, draft summaries, fixture text, never final
  acceptance without verifier.

## Required Praxis Envelope

```json
{
  "schema_version": "aios.production_praxis.v1",
  "task": "...",
  "memory_context": {
    "status": "used",
    "evidence_refs": ["aios://memory/..."]
  },
  "capability_routes": {
    "status": "used",
    "routes": ["aios://capability/..."],
    "external_resources": ["plugin:hugging_face.paper_search"]
  },
  "genesis_reframe": {
    "status": "used",
    "frictions": ["..."],
    "alternative_frames": ["..."]
  },
  "hive_execution_plan": {
    "status": "planned",
    "verification_gate": "..."
  },
  "specialist_assignment": [
    {"agent": "codex", "strength": "multimodal/code/test", "job": "..."},
    {"agent": "claude", "strength": "codebase topology/review", "job": "..."}
  ],
  "stop_conditions": []
}
```

## External Resource Rule

Use MCP/plugin/web/API resources when the task depends on:

- current model/provider/API behavior
- public repository state
- external design or implementation examples
- package, framework, or standard behavior likely to change
- research papers, benchmarks, datasets, Spaces, or tooling ecosystem changes

The result should cite the tool or source as evidence. CapabilityOS should
record the route as recommendation-only unless a contract grants execution
authority.

## Creative Friction Rule

GenesisOS must name the discomfort or missing affordance before creative work.
Examples:

- "The current flow makes the user manually prompt instead of feeling AIOS is
  alive."
- "The dashboard shows status but not intent, friction, and next move."
- "Provider fallback exists but feels like failure handling, not capability
  substitution."

Production creativity should come from resolving named friction, not from
decorating an existing plan.

## Gate Rule

For non-trivial production work, a missing praxis envelope is a stop condition.
The right fix is not to ask the founder for a better prompt. The right fix is
to invoke the missing OS layer and route the work again.
