# AIOS Agent Strength Routing Gap

- date: 2026-05-13 KST
- source: founder feedback during Uri development
- scope: AIOS runtime, Uri executor workflow, CapabilityOS/MemoryOS/GenesisOS usage

## Founder Observation

AIOS agents are not yet using their differentiated strengths:

- Codex is multimodal and can visually inspect product surfaces, evaluate
  screenshots, run browser checks, and create/use image assets, but current
  execution has mostly been text/code/test oriented.
- Claude appears stronger at large-codebase relationship mapping and
  architecture coherence, but current use has mostly been packet generation,
  not explicit dependency graph review and design risk critique.
- MCP/plugins, web APIs, public resources, and provider-specific capabilities
  are underused. Agents tend to rely on learned priors and local edits instead
  of actively searching, routing, copying public patterns lawfully, adapting
  usage, and verifying with production-like tools.
- Production creation is a loop of discovery, reference gathering, lawful reuse,
  usage shifting, visual iteration, and discomfort-driven capability growth.
  Current AIOS flow is too linear.

## Diagnosis

Current AIOS usage is mostly artifact-backed, not runtime-native:

- Hive is used for packets/receipts, but not enough for adversarial alternatives
  or specialist debate.
- MemoryOS receives drafts, but prior memory is not consistently queried before
  the next sprint and accepted memories are not yet shaping execution policy.
- CapabilityOS records tool recommendations, but it is not yet acting as a
  mandatory router that asks: which external tools, APIs, plugins, MCPs, browser
  checks, image generation, or public references should this sprint use?
- GenesisOS exists as a concept/stub, but it is not yet generating multiple
  candidate product universes before implementation.

## Required Runtime Behavior

Before each product sprint, AIOS should force a short routing pass:

1. MemoryOS recall: read relevant prior decisions, founder feedback, and failure
   notes.
2. CapabilityOS route: list tools to use and tools intentionally skipped.
   Include browser/visual verification for UI, official docs/web research for
   unstable external facts, plugins/MCPs when available, and image generation
   when assets would improve the experience.
3. GenesisOS expand: create 2-3 candidate product/design directions when the
   sprint touches UX, narrative, platform strategy, or interaction design.
4. Hive evaluate: assign roles by strength. Claude should map architecture and
   project dependency risks; Codex should implement, test, visually inspect, and
   use multimodal/tooling surfaces; other reviewers should critique clarity and
   user fit.
5. Executor closeout: write what was actually used, what was underused, and what
   new capability should be added.

## Immediate Uri Policy

For Uri UI/product sprints:

- Codex must run browser visual verification and inspect screenshot/layout
  evidence before calling the sprint done.
- Codex should consider image generation or sourced visual assets when the
  feature needs delight, spatial metaphor, avatar identity, campus atmosphere,
  or empty-state richness.
- Claude packets should include a codebase relationship map and explicit
  integration risks, not only feature tasks.
- CapabilityOS artifact must include an explicit `used` / `skipped` section for
  MCPs, plugins, browser, web, image generation, and local CLI tools.
- MemoryOS artifact must include recalled prior memory and what changed in the
  execution policy.
- GenesisOS should be invoked before major Uri surface changes to compare
  multiple product universes, not after the implementation.

## Product Implication

This gap is useful dogfood: AIOS itself should make agents feel the missing
tooling. When a worker notices "I should see this", "I need a source", "I need
an asset", or "this needs alternative universes", that discomfort should become
a CapabilityOS or GenesisOS upgrade request rather than being silently bypassed.
