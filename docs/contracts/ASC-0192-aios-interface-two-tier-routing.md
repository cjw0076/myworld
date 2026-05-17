---
contract_id: ASC-0192
slug: aios-interface-two-tier-routing
status: accepted
goal: Fix the AIOS chat interface — replace keyword task-classification with two-tier LLM routing, and move the single-thread chat toward a chatbot+multi-agent surface, informed by the agent-multiplexer OSS study.
created: 2026-05-17 21:55 KST
accepted: 2026-05-17 21:55 KST
acceptance_authority: founder directive — "interface는 provider agent를 chatbot + multi Agent처럼 ... 답변 품질이 매끄럽지 않다 ... 작업 분류도".
origin: Founder reported the AIOS chat interface's answer quality and task classification are rough. Diagnosis: aios_chat_router.classify_intent was pure keyword matching (the same keyword/template anti-pattern the audit found in GenesisOS). Research: docs/research/AGENT_MULTIPLEXER_LANDSCAPE.md.
---

# ASC-0192 AIOS Interface — Two-Tier Routing

DNA references: Invariant 1 (recommendation-only — routing proposes), Invariant
7 (privacy — the classifier is a local model), Invariant 8 (classify before
committing — literally the routing step).

## Diagnosis

- **Task classification was keyword matching.** `classify_intent` matched a
  hardcoded word list (`implement`, `작업`, `구현`, `weather` …); a turn
  phrased outside the list was misclassified. This is the founder's "작업
  분류가 매끄럽지 않다".
- **Answer quality.** Every chat turn ran the full Gate → MemoryOS →
  CapabilityOS → GenesisOS/Hive → provider pipeline wrapped in an envelope —
  ceremony-heavy for a simple turn.
- **Not multi-agent.** `apps/control/chat.html` is a single thread with hidden
  substrate routing, not a roster where you see/use multiple agents.

## Research finding (AGENT_MULTIPLEXER_LANDSCAPE.md)

Agent multiplexers (Claude Squad, cmux, Crystal, vibe-kanban …) mostly do
**isolation + presentation**, not classification — the user still routes.
Real routing lives in the LLM-router sub-field: **two-tier** — a fast
pre-router classifies the turn; a post-generation quality gate escalates
misroutes. Route against a live registry (CapabilityOS), not hardcoded.

## Done in this contract

**Tier-1 pre-router (closed).** `classify_intent` is now two-tier:
- a local-LLM helper `cap_helper_classify_chat_intent` (qwen3:8b) classifies
  the turn's *intent* (multi_step / current_info / single_turn);
- the cheap/single **cost tier** is decided by a deterministic length signal
  — that boundary is a cost property, not a semantic one, and a model is
  unreliable on it;
- the keyword heuristic remains as the fallback when no local model is
  present — the layer degrades, it does not break.

## Remaining (named follow-on)

1. **Tier-2 quality gate** — a post-generation check that escalates a
   misrouted turn to a stronger persona/model (RouteLLM pattern).
2. **Route against CapabilityOS live** — query the cost/health/route matrix
   per turn instead of any remaining hardcoded route.
3. **Multi-agent surface** — `apps/control/` gains a roster + detail-tabs
   (Claude Squad), a one-line status digest per agent (cmux), an
   out-of-band event channel (done/blocked/needs-input), diff-first review,
   and kanban columns mapped to the contract lifecycle (vibe-kanban).

## Named Exit

Closed when: tier-1 done (this commit); the remaining three items are tracked
as their own follow-on contracts.

## Stop Conditions

- A local model classifies worse than keywords on a class → keep keywords for
  that class (the cheap/single split already does exactly this).
