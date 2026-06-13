---
contract_id: ASC-0251
slug: end-user-serving-interface-spine
status: proposed
goal: Define the first true end-user serving interface for AIOS as a product surface separate from the local operator Control Center.
created: 2026-06-13T15:07:00+09:00
origin: The current AIOS UI is a local operator workbench, not a well-made hosted interface for real users.
---

# ASC-0251 End-User Serving Interface Spine

## Why Now

AIOS has a useful local Control Center:

- `apps/control/index.html`
- `apps/control/chat.html`
- `scripts/aios_local_app.py`
- `scripts/aios_workbench.py`

That surface is for the operator and local development. The workbench code
explicitly describes itself as local-first and a developer surface. It is not
the interface a real user should receive when AIOS is offered as a service.

The product needs a separate end-user surface with account/session boundaries,
per-user memory transparency, job progress, artifact review, consent gates,
and a simple first task loop.

## Current External Baseline

Primary-source review on 2026-06-13:

- OpenAI Agents SDK documents `Agent` + `Runner` as the orchestration layer on
  top of Responses API, with sessions, tracing, tools, handoffs, and sandbox
  agents. The sandbox path includes persistent workspaces, manifests,
  snapshots, resume, and memory.
- Anthropic release notes say Claude Managed Agents public beta launched on
  2026-04-08 with secure sandboxing, built-in tools, server-sent event
  streaming, configurable containers, and sessions through the API.
- Google Gemini API documents Interactions API beta for server-side history,
  background processing, and agentic workflows, and a Deep Research Agent for
  multi-step cited research.

Sources:

- `https://openai.github.io/openai-agents-python/agents/`
- `https://openai.github.io/openai-agents-python/sessions/`
- `https://openai.github.io/openai-agents-python/tracing/`
- `https://openai.github.io/openai-agents-python/sandbox_agents/`
- `https://openai.github.io/openai-agents-python/sandbox/memory/`
- `https://docs.anthropic.com/en/release-notes/api`
- `https://ai.google.dev/gemini-api/docs/interactions/interactions-overview`
- `https://ai.google.dev/gemini-api/docs/interactions/deep-research`

## Product Boundary

The end-user serving interface is not the Control Center with fewer buttons.
It is a separate product entry:

- user sees one task stream, not the whole AIOS control plane;
- user can inspect what AIOS remembered about them;
- user can pause/resume jobs and see exact stage progress;
- user can approve sensitive actions without seeing provider internals;
- user can download or reject artifacts;
- operator can still audit every action through MyWorld ledgers.

## Required Design Work

Before implementation, produce a design/contract packet with:

1. User roles:
   - end user;
   - operator/admin;
   - support reviewer;
   - agent worker.
2. User-facing routes:
   - task inbox;
   - active job/session;
   - memory viewer and controls;
   - artifact review;
   - approval queue;
   - account/workspace settings.
3. Runtime mapping:
   - how `end_user_serving` differs from `build_control` and
     `live_agent_runtime`;
   - how a user task becomes an AIOS contract or work packet;
   - how a job resumes after interruption.
4. Memory boundary:
   - per-user memories;
   - visible provenance;
   - draft/review/accepted lifecycle;
   - export/delete request path.
5. Serving readiness gates:
   - session isolation;
   - file/workspace isolation;
   - action approvals;
   - observability;
   - rate/cost controls;
   - incident/support flow.
6. UI proof:
   - a prototype or screenshot must prove the first user workflow, not just an
     operator dashboard.

## Plain-Language Framing

Right now AIOS has a cockpit. A user should not have to sit in the cockpit.
They need a cabin door, a seat, a service button, a clear itinerary, and a way
to inspect what happened to their belongings.

## Counter Branch

Counter-default option: expose the current Control Center and hide advanced
sections. Rejected because it leaks internal control-plane concepts and makes
users responsible for operator decisions.

## Dependency

ASC-0251 should not be implemented until ASC-0250 closes the local
build/runtime profile boundary. Otherwise the serving UI may inherit the same
mixed-state problem.

## First Implementation Candidate

After ASC-0250 closes, create a narrow prototype:

- `apps/serving/` or equivalent, separate from `apps/control/`;
- one user task form;
- one job progress timeline;
- one memory/provenance panel;
- one artifact approval panel;
- no direct access to operator-only contracts, raw runtime logs, or provider
  internals.

## Stop Conditions

- `serving_ui_reuses_operator_control_center`
- `user_memory_not_visible`
- `session_boundary_ambiguous`
- `approval_path_missing`
- `runtime_profile_dependency_unclosed`
- `privacy_boundary_ambiguous`
