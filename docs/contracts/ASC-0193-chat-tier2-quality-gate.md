---
contract_id: ASC-0193
slug: chat-tier2-quality-gate
status: closed
goal: Design and build the tier-2 quality gate for the chat router — a post-generation check that escalates a misrouted or under-delivered turn to a stronger chair, once, with a named exit.
created: 2026-05-17 22:15 KST
accepted: 2026-05-17 22:20 KST
closed: 2026-05-17 23:08 KST
acceptance_authority: founder — "구현 들어가자".
proposed_by: claude@myworld
origin: ASC-0192 follow-on. Founder: "tier 2 품질 게이트부터 설계하자." Tier-1 (classify_intent) routes a turn; nothing yet catches a successful-but-weak response from a cheap route.
---

# ASC-0193 Chat Tier-2 Quality Gate

DNA references: Invariant 4 (named exit — the gate escalates at most once),
Invariant 1 (recommendation-only — the gate proposes an escalation, the
deterministic path enacts it), Invariant 8 (classify before committing).

## Where it sits

The chat router already generates via `execute_gate_chair_turn` and already
catches **hard** failures (empty output, timeout, provider error). It does
**not** catch a *successful-but-low-quality* response — a cheap chair that
under-delivered on a turn that needed more. Tier-2 is exactly that check,
inserted after a successful generation and before the envelope is finalized.

## Design

### 1. Signals — what marks a response inadequate

**Deterministic (cheap, runs every escalation-eligible turn):**
- refusal / deferral markers ("I can't", "I'm unable", "you should ask",
  "제가 할 수 없", "확인이 필요");
- a `multi_step` turn answered in one trivial line (length floor by intent);
- the response restates the question or is mostly hedging;
- the response declares it lacked tools / memory / info it needed.

**LLM judge (qwen3:8b — selective, see §3):** scores *adequate / inadequate*
+ a one-line reason for "does this response satisfy the user's turn?".
(qwen3:1.7b is too weak for judgement — established in ASC-0192.)

### 2. Verdict

`pass` or `escalate`. A deterministic signal short-circuits to `escalate`
without spending the judge. Bias toward `pass` — a false escalation wastes a
strong-model call; RouteLLM holds strong calls at 14-26% of turns.

### 3. When the LLM judge runs (the cost/quality choice)

NOT every turn. The judge runs only when **both**: the route used a cheap
tier (internal / ollama / local) AND the intent was non-trivial
(`multi_step` or `current_info`). A `cheap_single_turn` answered cheaply
rarely needs judging; a provider-tier turn is already strong. This keeps the
gate near-free on the common path.

### 4. Escalation action

On `escalate`: re-run `execute_gate_chair_turn` once with the next chair up
the ladder (internal/ollama → default local → strong local → provider).
Regenerate exactly once.

### 5. Named exit (Invariant 4)

Escalate **at most once**. If the escalated response also fails the gate,
deliver it with `quality: degraded` in the envelope — never loop. Every turn
ends in one of: `pass`, `escalated_pass`, `escalated_degraded`.

### 6. Negative evidence

Every escalation is recorded — (turn, intent, original route, gate reason,
escalated route, outcome) — to `.aios/chat/<id>/` and as a CapabilityOS
observation. A misroute caught by tier-2 is precisely the signal tier-1
routing should learn from (feeds the dream / self-evolve loop).

### 7. Visibility

The response envelope carries `quality_gate: {verdict, escalated, reason}`
so the operator sees when and why a turn was escalated.

## Scope

repos: `myworld` — `scripts/aios_chat_router.py`, `tests/test_aios_chat_router.py`,
this contract, the ledger.

## Named Exit

Closed when: a cheap-routed `multi_step` turn that produces a weak response is
demonstrably escalated once to a stronger chair and the envelope carries the
`quality_gate` record; a good response passes without escalation; the
at-most-once bound is tested.

## Stop Conditions

- The judge itself errors → fail-open to `pass` (do not block a turn on a
  judge bug); record the judge error.
- Escalation target unavailable → deliver the original with `quality:
  degraded`, do not loop.

## Close Evidence

- Implementation:
  - `scripts/aios_chat_router.py` adds deterministic adequacy signals, selective
    LLM judging, at-most-once escalation to `qwen3:30b-a3b`, quality-gate
    envelope fields, and `.aios/chat/<conversation>/quality_gate.jsonl`
    evidence for non-pass outcomes.
  - `tests/test_aios_chat_router.py` covers deterministic signals, eligibility,
    and provider-output sanitization exposed by live dogfood.
- Live escalation smoke:
  - command:
    `AIOS_LOCAL_AGENT_COMMAND="printf 'Done.'" AIOS_CHAT_PROVIDER_TIMEOUT=10 python scripts/aios_chat_router.py --conversation asc-0193-live-smoke-clean-v2 --message '@ollama AIOS Control Center의 MemoryOS 시각화가 실제 retrieval trace와 provenance를 더 잘 보여주도록 구현 계획을 세워줘. 단계, 검증, 실패 조건을 포함해줘.' --json`
  - result: envelope used `chosen_substrate: ollama_qwen`, `intent:
    multi_step`, `quality_gate.verdict: escalated_pass`,
    `quality_gate.escalated: true`, and `quality_gate.escalated_model:
    qwen3:30b-a3b`.
  - artifacts:
    `.aios/chat/asc-0193-live-smoke-clean-v2/messages.jsonl`,
    `.aios/chat/asc-0193-live-smoke-clean-v2/gate_decisions/ac7e3dfca39ffe0c.json`,
    `.aios/chat/asc-0193-live-smoke-clean-v2/quality_gate.jsonl`,
    `.aios/invocations/chat-11e6bc95360fd969/receipt.json`.
- Dogfood fix: the first live smoke showed escalated local model output carrying
  terminal control sequences and a `Thinking...` scratch block. The sanitizer
  now applies terminal cursor erase, removes ANSI/control bytes, removes the
  leading thinking block, and reflows soft-wrapped output before persistence.
- Verification:
  - `python -m unittest tests.test_aios_chat_router.Tier2QualityGateTest -v`
    passed 7/7 after the sanitizer fix.
  - The live smoke output no longer exposed ANSI escape bytes or the explicit
    thinking block in the final response.
