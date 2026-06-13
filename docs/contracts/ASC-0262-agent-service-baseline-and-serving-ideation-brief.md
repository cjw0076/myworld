---
contract_id: ASC-0262
slug: agent-service-baseline-and-serving-ideation-brief
status: closed
goal: Refresh the external agent-service infrastructure baseline and bind it to the AIOS serving release path before Product Design ideation begins.
created: 2026-06-13T20:25:00+09:00
accepted: 2026-06-13T20:25:00+09:00
closed: 2026-06-13T20:25:00+09:00
human_approved: true
origin: The persistent objective asks whether Messages API -> Agent SDK -> Managed Agents evolved further, and requires AIOS to absorb hosting, session, sandbox, credential, memory, observability, and anti-frozen-knowledge requirements before serving real users.
---

# ASC-0262 Agent-Service Baseline And Serving Ideation Brief

## Decision

AIOS now has a current source-backed agent-service baseline:

- `docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md`

The baseline confirms that provider ecosystems have moved toward durable
server-side state, sandboxed workspaces, native agent harnesses, background
execution, managed/self-hosted sandboxes, vault-style credential handling,
observable steps/webhooks, and agent memory.

This is not UI work. Product Design remains at brief playback:

- product: real end-user AIOS serving product;
- visual source: none;
- next Product Design step: ideation;
- build permission: false until a concrete visual direction is selected.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md`
- `docs/contracts/ASC-0262-agent-service-baseline-and-serving-ideation-brief.md`
- `scripts/aios_serving_release_gate.py`
- `tests/test_aios_serving_release_gate.py`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/serving/**`
- `apps/control/**`
- child repo implementation files
- `CapabilityOS/**`
- `hivemind/**`
- `memoryOS/**`
- `GenesisOS/**`
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Sources

OpenAI:

- https://developers.openai.com/api/docs/guides/agents
- https://developers.openai.com/api/docs/guides/agents/sandboxes
- https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- https://developers.openai.com/codex/cloud/environments

Anthropic:

- https://docs.anthropic.com/en/release-notes/api

Google:

- https://ai.google.dev/gemini-api/docs/interactions/interactions-overview
- https://ai.google.dev/gemini-api/docs/interactions/deep-research
- https://ai.google.dev/gemini-api/docs/changelog

## AIOS Role Evidence

### MemoryOS

- Required future action: turn this baseline into reviewed MemoryOS drafts
  before it becomes accepted operational memory.

### CapabilityOS

- Required future action: convert provider capabilities into recommendation
  entries for hosted sandbox, session, credential, observability, and research
  routes.

### GenesisOS

- Required future action: challenge provider convergence before release so AIOS
  does not clone one vendor's harness or freeze around today's ecosystem.

### Hive Mind

- Required future action: implement queue/resume and sandbox receipt slices in
  the owning repo, not from MyWorld.

## Verification

```bash
test -f docs/research/AIOS_AGENT_SERVICE_BASELINE_2026-06-13.md
python3 scripts/aios_serving_release_gate.py assess --root . --json
python3 scripts/aios_world_readiness.py --json
git diff --check
```

Expected current state:

- baseline doc exists;
- serving release gate remains not ready;
- world readiness remains false;
- no UI implementation is created.

## Stop Conditions

- `official_source_missing`
- `ui_implementation_before_visual_target`
- `provider_marketing_copied_as_truth`
- `credential_value_in_doc_prompt_or_log`
- `world_readiness_claim_without_release_proof`
