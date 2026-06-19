---
contract_id: ASC-0278
slug: openai-agent-surface-absorption
status: proposed
created: 2026-06-19T15:30:00+09:00
goal: Absorb current OpenAI agent-service primitives into AIOS OS-owned contracts without binding AIOS to deprecated Agent Builder, provider-managed state, or raw trace memory.
owner_repo: myworld
primary_agent: claude@myworld
supporting_repos:
  - hivemind
  - memoryOS
  - CapabilityOS
  - GenesisOS
parent: ASC-0271
depends_on:
  - ASC-0235
  - ASC-0237
  - ASC-0238
  - ASC-0240
  - ASC-0260
  - ASC-0277
external_baseline:
  - docs/research/AIOS_OPENAI_AGENT_SURFACE_DELTA_2026-06-19.md
---

# ASC-0278 OpenAI Agent Surface Absorption

## Decision

OpenAI's current public agent stack now exposes code-first agents, stateful
Responses/Conversations, sandbox sessions, ChatKit, MCP/connectors,
observability traces, eval loops, and background mode. Agent Builder is useful
as a transition surface but is deprecated and scheduled to shut down on
November 30, 2026. The legacy Evals platform has a separate deprecation path:
existing evals become read-only on October 31, 2026 and the Evals dashboard/API
are scheduled to shut down on November 30, 2026.

AIOS must absorb the durable primitives without making any provider-managed
runtime the AIOS boundary. Claude owns the first hardening pass because this is
architecture, lifecycle, privacy, and contract-sequencing work. Codex keeps the
control-plane record and should not directly implement child repo internals.

## Plain Language

Treat provider agent platforms as contractors with offices, notebooks, tools,
and activity logs. AIOS is the company operating system that decides who may do
which work, where records live, which tools are allowed, and how the company
learns from each run.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0278-openai-agent-surface-absorption.md`
- `docs/research/AIOS_OPENAI_AGENT_SURFACE_DELTA_2026-06-19.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- raw trace bodies
- raw MCP payloads
- raw user data
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `uri/**`
- `apps/**`
- unrelated generated snapshots

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- owner_repo: `myworld`
- substrate_level: `runtime`
- surface_type: `contract`
- knowledge_scope: `web_primary_sources`
- authority: `speculative_only`
- primary_agent: `claude@myworld`
- required_receipts:
  - `aios.openai_agent_surface_delta.v1`
  - `aios.provider_state_ownership_matrix.v1`
  - `aios.managed_agent_deprecation_risk.v1`
  - `aios.os_absorption_split.v1`

## AIOS Role Evidence

### MemoryOS

- context_pack: `pending_or_not_required`
- retrieval_trace: `rtrace_6e4d0eb8aa220243`
- accepted_memory_ids: `pending_or_not_required`
- draft_memory_policy: Provider traces, sandbox snapshots, and conversation IDs
  are source references or draft candidates only.

### CapabilityOS

- route: `cap_aios_repo_goal_loop`, `cap_myworld_operator_control_plane`,
  `cap_aios_child_watcher`
- recommended_tools: official OpenAI docs, AIOS route/challenge/helper,
  read-only Codex explorer
- fallback_plan: if provider docs shift again, rerun dated official-source
  delta before accepting child implementation contracts.
- authority: `recommendation_only`

### GenesisOS

- branch_set: `pending_or_not_required`
- assumption_mutations:
  - provider state simplifies hosting -> provider state can hide split-brain
  - ChatKit accelerates UI -> provider-specific UI can create lock-in
  - traces/evals improve learning -> raw traces can leak private data
- semantic_alignment_notes: AIOS owns memory, authority, and receipts.
- authority: `speculative_only`

### Hive Mind

- execution_plan: no child execution under this proposal
- provider_route: none
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `pending_or_not_required`

Persona roles:

- Hive=Wrapper: present as future execution owner.
- MemoryOS=Retriever: present through retrieval trace and draft rules.
- CapabilityOS=Router: present through route recommendation.
- GenesisOS=Philosophy: present through critique and assumption negation.
- MyWorld=Sovereign: present as contract owner.

## Required Claude Hardening Work

Claude should read the external baseline and produce a hardening review that:

1. maps each OpenAI surface to the owning AIOS OS;
2. names which state IDs are source refs, resumable execution refs, or reviewed
   memory candidates;
3. rejects any reliance on deprecated Agent Builder as canonical AIOS state;
4. distinguishes current trace/eval workflow primitives from deprecated legacy
   Evals platform state;
5. defines provider-state split-brain stop conditions;
6. proposes owner-specific follow-on contracts only where current AIOS evidence
   is weaker than the official external surface.

## Owner Split To Produce

Claude should return an `aios.os_absorption_split.v1` packet with this shape:

| Surface | AIOS Owner | Required Follow-On If Gap Exists |
| --- | --- | --- |
| Responses/Conversations state | Hivemind + MemoryOS | provider state reconciliation and replay/continuation receipts |
| Agents SDK sessions / `RunState` | Hivemind | resumable execution receipt schema and duplicate-action prevention |
| Sandbox Agents | Hivemind | manifest/snapshot/port/package/filesystem boundary receipts |
| ChatKit | MyWorld + Hivemind | user-authenticated serving session bridge, not Agent Builder lock-in |
| MCP/connectors | CapabilityOS | connector approval, OAuth scope, official-server and tunnel policy |
| Traces/evals | MemoryOS + GenesisOS | redacted trace/eval draft import plus entropy-pressure closeout gate |
| Background mode | Hivemind + MemoryOS | retention/ZDR label, async polling receipt, privacy classification |

## Verification Gate

This contract can close only when:

- Claude result packet exists under `.aios/outbox/myworld/` or an equivalent
  ledger entry names the same evidence.
- The result names at least four owner-specific follow-on contracts or explains
  why existing ASC contracts already cover the slice.
- The result includes a provider-state ownership matrix.
- The result includes a deprecation-risk note for Agent Builder and the legacy
  Evals platform.
- The result includes privacy stop conditions for raw traces, MCP payloads,
  sandbox files, and credential/OAuth material.
- No child repo implementation files are changed by MyWorld under this
  contract.

## Stop Conditions

- `agent_builder_treated_as_canonical_aios_state`
- `provider_state_auto_promoted_to_memory`
- `raw_trace_body_committed`
- `mcp_payload_or_oauth_scope_leaked`
- `sandbox_snapshot_without_isolation_receipt`
- `background_job_without_retention_label`
- `child_repo_implementation_from_myworld`
- `apps_ui_build_started_under_architecture_contract`

## Time Horizons

| Horizon | Good Outcome | Bad Outcome |
| --- | --- | --- |
| 1 hour | Contract and source-backed baseline exist; Claude can harden without chat context. | AIOS only has a prose opinion about OpenAI surfaces. |
| 1 week | Owner-specific contracts are accepted/dispatched where gaps remain. | AIOS keeps claiming readiness from marker scripts while provider-state gaps remain unowned. |
| 1 year | AIOS can swap OpenAI, Claude, Gemini, local LLMs, MCP servers, and future managed-agent surfaces without losing memory or authority. | AIOS becomes a wrapper around one provider's deprecated or changing workflow product. |

## Next

Accept this contract only for Claude architecture hardening. Implementation
belongs in later owner-specific child contracts.
