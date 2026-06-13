# AIOS Agent-Service Baseline — 2026-06-13

Purpose: capture the current external agent-service baseline that AIOS must
absorb before claiming world-deployable infrastructure readiness.

This is source-backed research, not implementation. It does not create hosted
infrastructure, credentials, deployment manifests, or user data flows.

## Source Baseline

### OpenAI

Current direction:

- Responses API remains the direct primitive when one model call plus tools and
  application-owned logic is enough.
- Agents SDK is the code-first layer when the application owns orchestration,
  tool execution, approvals, and state.
- Agents SDK sandbox agents make workspace execution, resumable filesystem
  state, artifacts, exposed ports, commands, packages, and human-review resume
  first-class concerns.
- OpenAI's 2026 Agents SDK update adds native sandbox execution and separates
  the agent harness from compute for security, durability, and scale.
- Codex cloud creates per-task containers, checks out the repo, runs setup and
  maintenance scripts, and applies explicit internet-access settings.

Sources:

- https://developers.openai.com/api/docs/guides/agents
- https://developers.openai.com/api/docs/guides/agents/sandboxes
- https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- https://developers.openai.com/codex/cloud/environments

### Anthropic

Current direction:

- Claude Managed Agents launched as a managed autonomous-agent harness with
  secure sandboxing, built-in tools, configurable containers, sessions, and
  streaming.
- Claude Managed Agents now include memory beta, vault credential refresh,
  webhooks, multi-agent sessions/orchestration, scheduled deployments,
  environment-variable credential injection into sandboxes, and self-hosted
  sandboxes on Claude Platform on AWS.
- The user-experience problem AIOS must solve is not simply "ask for less
  information." It is scoped user-controlled memory plus capability-bound
  credential references, so providers can act without repeatedly asking for
  sensitive values or seeing more private data than the task allows.

Source:

- https://docs.anthropic.com/en/release-notes/api

### Google Gemini

Current direction:

- Gemini Interactions API is positioned for agentic workflows, server-side
  state management, typed observable execution steps, background processing,
  and complex multi-modal multi-turn conversations.
- The Interactions API can continue from `previous_interaction_id`, avoiding
  manual resending of full conversation history when server-side state is used.
- Gemini Deep Research Agent plans, executes, and synthesizes multi-step
  research with citations, MCP tool connections, visualizations, and document
  input.
- Gemini release notes also show session-resumption support with server-side
  state storage for up to 24 hours.

Sources:

- https://ai.google.dev/gemini-api/docs/interactions/interactions-overview
- https://ai.google.dev/gemini-api/docs/interactions/deep-research
- https://ai.google.dev/gemini-api/docs/changelog

## AIOS Implications

The market baseline has moved beyond "LLM plus tools." The minimum credible
agent-service substrate now includes:

1. Durable server-side session state.
2. Resumable workspaces with filesystem artifacts.
3. Explicit sandbox boundaries for files, process, packages, network, and
   exposed ports.
4. Human approval and review continuation.
5. Webhooks or typed observable execution steps.
6. Credential vaults or access grants that inject references/scopes, not raw
   secrets in prompts.
7. Multi-agent orchestration and background work.
8. Memory as a governed product surface, not invisible chat history.
9. Research/web ingestion paths that produce cited, reviewable records.

AIOS should not clone a single provider's hosted harness. It should absorb the
common operating-system primitives:

| Primitive | AIOS Owner | Serving Gate Slice |
| --- | --- | --- |
| Session state and resume | MyWorld + MemoryOS | runtime_profile, memoryos_user_lifecycle |
| Workspace and artifacts | Hivemind + MyWorld | serving_ui_prototype, hivemind_worker_resume |
| Execution isolation | Hivemind | hivemind_worker_resume |
| Approvals and user control | MyWorld + CapabilityOS | capabilityos_access_routing |
| Credential access grants | CapabilityOS + MyWorld vault | capabilityos_access_routing |
| Observability and webhooks | MyWorld + MemoryOS | observability_support_redaction |
| Web/research absorption | MemoryOS + GenesisOS | memoryos_user_lifecycle, genesis_prelaunch_challenge |
| Anti-convergence pressure | GenesisOS | genesis_prelaunch_challenge |

## Product Design Brief Playback

Product: AIOS real end-user serving product.

What it should do: let a real user submit goals to an AIOS agent-service,
track progress, approve sensitive actions, review memory drafts, receive
artifacts, and control/export/delete their own data without seeing operator
control-plane internals.

Visual source: none yet. Product Design user-context preflight reports no saved
context. Therefore the next Product Design workflow is ideation, not prototype.

Interactivity target: full workflow, once a visual direction is selected.

Current gate state:

- `.aios/serving/design_gate.json`: `visual_target_type=needs_ideation`
- `next_product_design_step=ideate`
- `build_allowed=false`

## Readiness Requirement Delta

ASC-0261 already prevents prototype-only world-readiness claims. This baseline
adds source-backed pressure that future release slices should prove:

- session IDs and resume handles are explicit;
- workspace snapshots or artifacts are inspectable;
- background jobs emit typed steps or webhook-like events;
- user approvals resume the same work item without duplicate sensitive action;
- credentials are represented as scoped access grants;
- memory records have provenance, review lifecycle, and export/delete paths;
- research/web ingestion produces cited MemoryOS drafts;
- GenesisOS challenge runs before release to fight frozen-knowledge convergence.

## Next Contract Candidate

`ASC-0262` should bind this source baseline into the serving release gate as an
external-baseline evidence marker and prepare Product Design Slice 1 ideation
without building UI.
