---
contract_id: ASC-0251
slug: end-user-serving-interface-spine
status: closed
goal: Define the first true end-user serving interface for AIOS as a product surface separate from the local operator Control Center.
created: 2026-06-13T15:07:00+09:00
accepted: 2026-06-13T15:31:00+09:00
closed: 2026-06-13T15:37:00+09:00
human_approved: true
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

ASC-0249 and ASC-0250 are now closed, so the local build/runtime profile
boundary exists before this serving-interface work starts.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0251-end-user-serving-interface-spine.md`
- `docs/product/AIOS_END_USER_SERVING_INTERFACE_SPEC.md`
- `docs/product/AIOS_SERVING_INTERFACE_ROUTE_MAP.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `apps/control/**`
- `apps/serving/**`
- `scripts/**`
- `tests/**`
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

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

## Product Design Brief Gate

Product Design context preflight on 2026-06-13 found no saved Product Design
context at `/home/user/.codex/state/plugins/product-design/user-context.md`.

Confirmed brief for this contract:

- product: AIOS end-user serving interface;
- source: current `apps/control` proves what not to expose to users and may be
  used only as operator-control contrast, not as the visual target;
- desired feel: quiet, trustworthy, work-focused service interface for users
  delegating tasks to an agent company;
- interactivity for this contract: design/spec only, no runnable UI build yet;
- implementation dependency: future UI build needs either a chosen visual
  direction, reference, mock, or prototype contract.

## Required Design Work For Claude

Before implementation, produce a design/spec packet with:

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
   - define what later prototype or screenshot must prove for the first user
     workflow, without building that prototype in this contract.
7. MyWorld control-plane mapping:
   - how user actions become contracts, dispatches, approvals, or MemoryOS
     records;
   - what the end user must never see from operator-only control state;
   - how support/admin can inspect enough evidence without crossing privacy
     boundaries.
8. Acceptance gates for a future UI build:
   - explicit route list;
   - mock data schema;
   - first workflow state machine;
   - accessibility and responsive checks;
   - browser verification expectations.

## Plain-Language Framing

Right now AIOS has a cockpit. A user should not have to sit in the cockpit.
They need a cabin door, a seat, a service button, a clear itinerary, and a way
to inspect what happened to their belongings.

## Counter Branch

Counter-default option: expose the current Control Center and hide advanced
sections. Rejected because it leaks internal control-plane concepts and makes
users responsible for operator decisions.

## Dependency

ASC-0250 closed the local build/runtime profile boundary on
2026-06-13T15:24:00+09:00. This contract may now proceed as a design/spec
packet. It still must not implement UI code.

## First Implementation Candidate

After this design/spec packet is accepted, create a separate narrow prototype:

- `apps/serving/` or equivalent, separate from `apps/control/`;
- one user task form;
- one job progress timeline;
- one memory/provenance panel;
- one artifact approval panel;
- no direct access to operator-only contracts, raw runtime logs, or provider
  internals.

## Work Packets

### WP-0251-A — Claude end-user serving interface spec

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Produce the required design/spec packet only. Do not implement
  UI code. Keep the surface separate from the operator Control Center and make
  the first user workflow concrete enough for a future prototype contract.
- result: pending

## Stop Conditions

- `serving_ui_reuses_operator_control_center`
- `user_memory_not_visible`
- `session_boundary_ambiguous`
- `approval_path_missing`
- `runtime_profile_dependency_unclosed`
- `ui_implementation_before_visual_target`
- `privacy_boundary_ambiguous`
