# AIOS GitHub / Reddit Alignment Mining

created: 2026-05-20 KST  
owner: codex@myworld  
contract: ASC-0216  
evidence: `docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json`

## Mining Result

The best ideas to attach are not "train a model now." The strongest public
project and practitioner signals point to a four-layer substrate:

```text
trace everything important
  -> evaluate workflows, not prompts
  -> red-team boundaries
  -> turn failures/preferences into regression cases
```

AIOS already has contracts, dispatch packets, result packets, monitor state,
MemoryOS drafts, CapabilityOS routes, and GenesisOS challenge. The missing
piece is a first-class alignment mining loop that turns those artifacts into
evals and preference updates.

## Projects Worth Borrowing From

### Promptfoo

Source: https://github.com/promptfoo/promptfoo

Useful ideas:

- declarative eval configs;
- provider/model comparison matrices;
- red-team and vulnerability reports;
- CI/CD integration;
- local-first eval runs.

AIOS application:

- Create `docs/evals/aios/*.yaml` for contract and route eval cases.
- Add `aios eval run` that evaluates a contract/result pair against rubric
  assertions.
- Render a matrix in Control Center: candidate plan x provider x rubric axis.

Do not attach yet:

- Full promptfoo runtime dependency. Start with the config grammar and result
  receipt shape.

### Langfuse / Phoenix / Helicone Class

Sources:

- https://github.com/langfuse/langfuse
- https://github.com/Arize-ai/phoenix
- https://github.com/helicone/helicone

Useful ideas:

- OpenTelemetry-style spans;
- prompt and trace versioning;
- datasets and experiments;
- self-hosted observability;
- cost/latency tracking.

AIOS application:

- Introduce `aios.trace.span.v1` for dispatch, provider call, tool call,
  MemoryOS retrieval, CapabilityOS recommendation, GenesisOS challenge, and
  user@offline observation.
- Preserve local-first by writing spans to `.aios/traces/` first.
- Later expose OpenTelemetry export as optional, not default.

Decision:

- Borrow Phoenix/OpenTelemetry semantics, not a hosted observability platform.

### DeepEval / OpenAI Evals

Sources:

- https://github.com/confident-ai/deepeval
- https://github.com/openai/evals

Useful ideas:

- evals as tests;
- custom private evals;
- dataset-backed regression;
- model-graded evals with human calibration;
- agent-generated eval scaffolding.

AIOS application:

- Add `tests/evals/` for AIOS system behavior.
- Make `contract closed` require at least one eval category when the contract
  changes behavior, policy, routing, memory, or UI.
- Convert failed production traces into eval cases.

### Ragas

Source: https://github.com/vibrantlabsai/ragas

Useful ideas:

- RAG-specific metrics for retrieval relevance, faithfulness, and answer
  quality.

AIOS application:

- Use later for MemoryOS retrieval quality, not as the first generic AIOS eval
  engine.
- Define MemoryOS-specific metrics first: source coverage, freshness,
  provenance strength, review status, contradiction exposure.

### Garak / LLM Guard / Guardrails

Sources:

- https://github.com/NVIDIA/garak
- https://github.com/protectai/llm-guard
- https://github.com/guardrails-ai/guardrails

Useful ideas:

- adversarial probes;
- prompt-injection detection;
- harmful-language and leakage scanners;
- input/output validators;
- structured output validation and on-fail actions.

AIOS application:

- Add a pre-dispatch boundary scan for external web, provider, and private
  context routes.
- Add GenesisOS red-team packets that generate adversarial cases against
  contracts before close.
- Add output schema validation before downstream scripts consume LLM output.

### TRL / Alignment Handbook / OpenRLHF

Sources:

- https://github.com/huggingface/trl
- https://github.com/huggingface/alignment-handbook
- https://github.com/OpenRLHF/OpenRLHF

Useful ideas:

- SFT, reward model, DPO, ORPO, KTO, PPO, GRPO;
- reproducible alignment recipes;
- scalable RLHF/RLVR once data exists.

AIOS application:

- Later backend only.
- Prerequisites:
  - reviewed preference pairs in MemoryOS;
  - behavior spec;
  - eval harness;
  - red-team gate;
  - rollback path for model/prompt changes.

## Reddit Practitioner Signals

### Signal 1: Prompt evals are too narrow

Source:
https://www.reddit.com/r/AI_Agents/comments/1t9xlfw/are_most_llm_eval_tools_still_too_promptfocused/

Practitioner pattern:

- failures emerge from stale context, schema mismatch, assumption drift, and
  long workflow state;
- canary inputs, schema validation, and output-distribution tracking matter
  more than isolated prompt scores.

AIOS implication:

- Eval `contract trajectories`, not only prompts.
- Store before/after state and dispatch traces as eval inputs.

### Signal 2: Production agents need failure-to-eval loops

Source:
https://www.reddit.com/r/AIAgentsInAction/comments/1tb1u66/everyone_says_they_have_ai_agents_in_production/

Practitioner pattern:

- step-level traces and production-failure promotion into eval cases are key;
- frozen eval sets go stale as the world changes.

AIOS implication:

- Every failed or manually corrected AIOS run should be promotable into an eval
  case and a MemoryOS draft.

### Signal 3: Observability and evals are different organs

Source:
https://www.reddit.com/r/LangChain/comments/1rjn3pn/llm_observability_is_the_new_logging_quick/

Practitioner pattern:

- tracing shows what happened;
- evals decide whether quality regressed;
- agent workflows need multi-step tool-call traces, not only single-call logs.

AIOS implication:

- Keep `trace`, `eval`, `preference`, and `policy update` as linked but
  separate records.

## Apply To AIOS

### Immediate Attachment

Build an `AIOS Alignment Mining Spine`:

```text
.aios/traces/*.jsonl
docs/evals/aios/*.yaml
docs/evidence/*eval*.json
MemoryOS preference drafts
CapabilityOS route observations
Control Center eval matrix
```

Minimal first flow:

```text
closed or failed contract
  -> extract trace
  -> run rubric eval
  -> ask user@offline for preference when ambiguous
  -> write preference/eval receipt
  -> create next regression case
```

### Recommended Implementation Order

1. `ASC-0217-aios-eval-spine`
   - myworld + hivemind.
   - Add local eval case format and runner.
   - Input: contract path + result packet + optional trace.
   - Output: eval receipt with rubric scores and failing assertions.

2. `ASC-0218-aios-trace-span-schema`
   - myworld + hivemind.
   - Define local span schema for dispatch, tool, provider, memory, route,
     genesis, and user@offline events.

3. `ASC-0219-red-team-boundary-probes`
   - GenesisOS + hivemind.
   - Add garak/promptfoo-inspired adversarial probes for web, private context,
     provider output, and closure overclaim.

4. `ASC-0220-preference-to-regression`
   - memoryOS + myworld.
   - Convert user accept/reject, A/B preference, and field observation into
     reviewed preference drafts and regression eval cases.

5. `ASC-0221-control-center-alignment-matrix`
   - myworld UI.
   - Show trace -> eval -> preference -> policy update path in the Control
     Center.

6. `ASC-0222-local-dpo-readiness-check`
   - CapabilityOS + hivemind.
   - Do not train yet; only assess whether enough reviewed preference pairs
     and stable eval gates exist for TRL/DPO.

## What Not To Do

- Do not install Langfuse/Phoenix/Promptfoo as a platform dependency yet.
- Do not send private traces to any hosted service.
- Do not let model-graded evals override `user@offline` preference.
- Do not fine-tune from unreviewed MemoryOS drafts.
- Do not evaluate only final answers; evaluate the workflow path.

## Decision

Create ASC-0217 next, not the DPO pilot.

The practical next build is:

```text
AIOS local eval spine
  -> trace-aware
  -> preference-aware
  -> red-team-ready
  -> export-compatible later
```

This gives AIOS the same learning surface that RLHF systems need, while
keeping the first implementation local, inspectable, and contract-bound.
