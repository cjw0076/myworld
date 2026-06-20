---
contract_id: ASC-0234
slug: world-deployable-aios-readiness-spine
status: accepted
accepted: 2026-06-20T00:00:00+09:00
accepted_by: claude@myworld
acceptance_note: serving_release_gate 9/9 and world_readiness_gate 8/8 both report ready as of 2026-06-20 audit. Spine is enacted; provenance chain now closed.
goal: Define the readiness spine for moving AIOS from local self-maintaining control plane to world-deployable infrastructure without collapsing MyWorld, Hive, MemoryOS, CapabilityOS, and GenesisOS ownership.
created: 2026-06-12T23:35:00+09:00
origin: founder directive — do not solve only from one model; trace Claude progress; use external knowledge, Claude/Codex/Gemini/local LLM signals, and decide whether AIOS must touch OS/process substrate, plugin surfaces, or broad knowledge.
---

# ASC-0234 World-Deployable AIOS Readiness Spine

## Why Now

Claude pushed AIOS forward locally with five unpushed commits:

- `8a5180e` provider router for Gemini, local Ollama, and Claude API.
- `75a3d38` provider bug fixes after multi-substrate review.
- `d81ebf8` multi-substrate fan-out and auto local model selection.
- `ebbd696` ULTRATHINK synthesis labeling.
- `958d49a` LLM synthesis, installer shell, and portable path fixes.

Live verification on 2026-06-12 showed:

- `python3 scripts/aios_provider.py status` reports Gemini and local Ollama available; Claude API is unavailable because no API key is present.
- `python3 scripts/aios_completion.py --json` reports `AIOS COMPLETE — fully sovereign and self-maintaining`.
- `python3 -m py_compile scripts/aios_provider.py scripts/aios_multi_substrate.py scripts/aios_completion.py scripts/aios_checkpoint.py` passes.
- `python3 scripts/aios_multi_substrate.py --json run ...` returned both Gemini and local arms and synthesized seven infrastructure gaps.

This proves local self-maintenance and multi-provider substrate progress. It
does not prove world deployment readiness.

## External Evidence

Current agent infrastructure points to the same readiness spine:

- OpenAI Responses API is the recommended primitive for new projects and
  supports stateful interactions and hosted tools. Source:
  https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI Conversations API persists conversation state with durable identifiers
  across sessions, devices, and jobs. Source:
  https://developers.openai.com/api/docs/guides/conversation-state
- OpenAI Agents SDK has built-in sessions and tracing for LLM generations, tool
  calls, handoffs, guardrails, and custom events. Sources:
  https://openai.github.io/openai-agents-python/sessions/ and
  https://openai.github.io/openai-agents-python/tracing/
- Claude Code exposes hooks, MCP, plugins, skills, and managed-agent style
  harness boundaries. Sources:
  https://docs.anthropic.com/en/docs/claude-code/hooks and
  https://docs.anthropic.com/en/docs/claude-code/mcp
- Gemini CLI exposes local project agent workflows and MCP server
  configuration. Sources:
  https://github.com/google-gemini/gemini-cli and
  https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md
- OpenTelemetry GenAI semantic conventions define shared signals for GenAI
  operations, metrics, and agent/framework spans. Source:
  https://opentelemetry.io/docs/specs/semconv/gen-ai/

Decision: AIOS should not copy any single provider harness. It should absorb
the common primitives: durable state, traceable tool calls, lifecycle hooks,
MCP/tool surfaces, bounded execution, and provider-independent observability.

## Readiness Gaps

1. Iterative engine spine
   - gap: `docs/AIOS_ECOSYSTEM_BLUEPRINT.md` says AIOS still lacks a
     model-in-the-loop turn function and behaves like a batch executor.
   - owner: `myworld` contract plus Hive execution substrate.
   - readiness test: one work object can run sample -> tool dispatch ->
     receipt -> resample with max-turn and loop detection.

2. Durable cross-session work object
   - gap: checkpoint and session pieces exist, but world deployment needs a
     stable `.aios/work/<id>.json` lineage object with session ids, parent ids,
     active plan, status, and replay checkpoint refs.
   - owner: `memoryOS` for durable memory/session lineage, `myworld` for
     contract identity.
   - readiness test: a paused work item resumes on another process or device
     without reading raw private provider history.

3. Cloud-native execution isolation
   - gap: local sandboxing and guard hooks are not the same as hosted
     multi-tenant isolation, network policy, package boundary, and compute
     quota enforcement.
   - owner: `hivemind`.
   - readiness test: a provider/tool run declares filesystem, process, network,
     package, and timeout scope before execution and emits a receipt after
     degraded or successful exit.

4. Credential and private-data boundary
   - gap: `scripts/aios_vault.py` exists, but provider CLIs and session logs
     still require explicit boundaries so agents do not ask the user for
     sensitive data repeatedly or leak raw history into shared artifacts.
   - owner: `myworld` authority core plus `CapabilityOS` recommendation layer.
   - readiness test: a route can request a named credential capability without
     exposing the value, and denial becomes a structured fallback receipt.

5. Unified observability and Akashic ledger
   - gap: logs, ledgers, events, MemoryOS traces, provider outputs, and
     multi-substrate disagreements are not yet one queryable trace graph.
   - owner: `memoryOS` for Akashic record and provenance; `hivemind` for run
     spans and provider receipts.
   - readiness test: one user goal can show every prompt, dispatch, tool call,
     model response summary, token/cost estimate, verifier result, pause,
     resume, and closeout without publishing raw secrets.

6. CapabilityOS / SkillOS neuromuscular layer
   - gap: scripts and tools exist, but tool selection is not yet a live
     capability registry with risk, availability, cost, prior success, fallback,
     and owner boundary.
   - owner: `CapabilityOS`.
   - readiness test: every tool/provider/plugin recommendation returns
     `recommendation_only` until a contract grants execution authority, and
     failures update capability routing evidence.

7. Genesis entropy and SECI knowledge conversion
   - gap: multi-provider synthesis reduces single-model lock-in, but AIOS still
     needs an explicit cycle for socialization, externalization, combination,
     internalization, and discomfort injection so knowledge does not freeze.
   - owner: `GenesisOS`.
   - readiness test: important conclusions carry at least one challenge branch,
     one external/source-backed branch when needed, and a memory draft or
     rejection path instead of immediate accepted truth.

## Ownership Boundary

- `myworld`: contracts, dispatch, authority, identity, lifecycle gates, and
  operator checkpoints.
- `hivemind`: provider execution, scheduler, cloud/runtime isolation,
  verification, run spans, and proofs.
- `memoryOS`: Akashic ledger, context packs, retrieval traces, durable work
  lineage, provenance, and review lifecycle.
- `CapabilityOS`: provider/tool/plugin/skill recommendations, dynamic route
  scores, fallback plans, and capability gaps.
- `GenesisOS`: divergent branches, assumption mutation, entropy, SECI cycle,
  and pre-close challenge surfaces.

## Required Work

- Create a world-deployment readiness gate that is separate from
  `scripts/aios_completion.py`. The current completion gate can stay scoped to
  local self-maintenance.
- Add a readiness report command or artifact that returns the seven gap
  statuses above with evidence refs and owner repo.
- Dispatch owner-specific follow-up packets instead of implementing child repo
  internals directly from MyWorld.
- Preserve Claude's current local commits and dirty work until an explicit
  review/commit/push decision is made.

## Verification Gate

```bash
python3 scripts/aios_provider.py status
python3 scripts/aios_completion.py --json
python3 -m py_compile scripts/aios_provider.py scripts/aios_multi_substrate.py scripts/aios_completion.py scripts/aios_checkpoint.py
python3 scripts/aios_multi_substrate.py --json run --timeout 120 --task "<readiness gap prompt>"
git diff --check
```

Pass criteria:

- The new readiness gate does not redefine local `AIOS COMPLETE`; it adds a
  separate world-deployment axis.
- No secrets, `.env`, raw provider logs, or private history stores are copied
  into docs or dispatch packets.
- Child repo implementation remains owner-dispatched.
- Provider disagreement and degraded output become structured receipts, not
  silent success.

## Stop Conditions

- `world_readiness_claim_without_gate`
- `raw_provider_history_leak`
- `credential_value_in_prompt_or_doc`
- `child_repo_implementation_without_dispatch`
- `completion_gate_scope_confusion`
- `single_provider_truth_without_hive_verifier`
- `capabilityos_executes_instead_of_recommends`
- `memoryos_accepts_without_review`

## Plain Language (GenesisOS escape — terminology-trapped)

AIOS is a local program that routes your AI tasks to the right tool (Claude,
Gemini, a local model). Right now it only works on one machine. "World
deployable" means: install it on a new machine in five minutes, store secrets
safely, and prove it actually sent tasks to each tool and got back answers.
The readiness spine is a checklist for that jump from one-machine to any-machine.

## Cross-Domain Frame (GenesisOS escape — single-frame)

Analogy from aviation: a flight management system (FMS) sits above the
individual engines and navigation radios. The FMS does not replace those
instruments; it routes inputs, records the flight envelope, and enforces
procedures. A FMS that works on one aircraft type but cannot be ported to
another is not a product — it is a prototype. AIOS-to-world-deployment is
the portability certification flight: same checklist, new airframe (machine),
every instrument (provider) must self-report green before departure.

The key tension the aviation frame exposes: **pre-flight checks must be
run on the target airframe, not the development bench.** A local
`AIOS COMPLETE` is a bench test. The world-deployment readiness gate is the
airframe pre-flight.

## Assumptions

1. A new-machine install under 10 minutes is achievable with `aios_install.sh`
   + vault init.
2. Provider availability can be verified at install time, not just at task time.
3. Credential secrets can be stored without ever appearing in git history,
   logs, or docs.
4. A multi-substrate run with ≥2 providers constitutes functional proof of
   routing — single-provider success is a passing bench test, not a deployment
   proof.
5. "World-deployable" does not require multi-tenant hosting; single-operator
   install on a remote machine qualifies.

Counter-branch: Assumption 5 may be wrong — if uri production requires a
hosted endpoint accessible by multiple users simultaneously, single-operator
remote-machine install is insufficient. That branch is tracked in ASC-0180
(Hive hosting debate) and remains open for founder verdict.

## Next Contracts

- `ASC-0235`: world-deployment readiness report CLI in MyWorld.
- `ASC-0236`: Hive cloud/runtime isolation receipt schema.
- `ASC-0237`: MemoryOS Akashic work-lineage and replay checkpoint index.
- `ASC-0238`: CapabilityOS SkillOS dynamic routing scorecard.
- `ASC-0239`: GenesisOS SECI entropy gate for pre-close synthesis.
