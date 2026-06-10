---
contract_id: ASC-0188
slug: gate-chair-conversational-activation-policy
status: closed
goal: Let external Gate Chair candidates become operator-promotable when they match or beat the internal baseline with no runtime failures, while preserving timeout/access failures as MemoryOS negative-evidence drafts.
created: 2026-05-17T14:18:00+09:00
accepted: 2026-05-17T14:18:00+09:00
closed: 2026-05-17T14:18:00+09:00
---

# ASC-0188 Gate Chair Conversational Activation Policy

## Why

AIOS chat had a Gate/Chair layer, but the active Chair remained the
deterministic `internal_evidence_synthesizer`. The founder's complaint was
correct: a chat surface can have routing receipts and still fail to feel like a
provider-grade conversational gate.

The previous promotion rule was too strict for this purpose. It required a
provider/local Chair to beat the internal baseline. For activation as a
conversational runtime, the safer rule is:

- external runtime observed;
- no failed Chair runs;
- score matches or beats the deterministic internal baseline;
- operator-confirmed promotion still required.

A tie does not prove better reasoning. It proves that a provider-like Chair can
be attached without degrading the current eval, and therefore may be promoted
when the operator wants a more natural Gate.

## Scope

- repos: `myworld`
- allowed_files:
  - `scripts/aios_gate_chair_eval.py`
  - `tests/test_aios_gate_chair_eval.py`
  - `docs/AIOS_CONTROL_APP.md`
  - `docs/contracts/ASC-0188-gate-chair-conversational-activation-policy.md`
  - `docs/contracts/README.md`
  - `docs/AGENT_WORKLOG.md`
- forbidden_files:
  - `.env`
  - provider credentials, PINs, API keys, raw provider transcripts
  - child repo source files

## Responsibilities

### myworld.must_produce

- Gate Chair eval reports with:
  - `promotion_ready=true` only when current runtime is external, has no failed
    current Chair runs, and `scores.current >= scores.internal`;
  - `current_failure_count`;
  - readiness reasons that distinguish below-baseline, runtime failure, and
    tie-but-promotable cases.
- Candidate matrix summaries with the same `>= baseline` eligibility rule.
- A broader runtime-disclosure check so provider responses that mention
  `Gate Chair runtime`, `chair_runtime.json`, or
  `chair_candidate_runtime.json` are not false negatives.
- Compact/redacted Gate Chair prompts and persisted turn receipts:
  - selected MemoryOS items are capped before being sent to the Chair;
  - private markers, PINs, API keys, and emails are redacted from prompt
    previews and response previews;
  - `provider_meta.command` and `chair_meta.command` keep only the executable
    plus redacted argument marker, never raw provider argv or prompt text.

### memoryos.must_produce

- Timeout/access/backpressure eval failures remain draft-first negative
  evidence. They are sent to MemoryOS review and are not auto-accepted.

### capabilityos.must_produce

- No new route is added in this contract. CapabilityOS should treat the new
  eval evidence as routing signal for future provider selection.

### hive_mind.must_produce

- No Hive execution change. Hive remains the executor for work; Gate Chair is
  only the conversational routing/synthesis layer.

### genesisos.must_produce

- No direct change. GenesisOS still supplies friction and branch context for
  Gate prompts.

## Verification Gate

```bash
python -m py_compile scripts/aios_gate_chair_eval.py scripts/aios_chat_router.py scripts/aios_local_app.py
python -m unittest tests.test_aios_gate_chair_eval tests.test_aios_chat_router tests.test_aios_local_app -v
python scripts/aios_gate_chair_eval.py --candidate-matrix --candidate claude --candidate codex --candidate gemini --json
python scripts/aios_gate_chair_eval.py --mode both --json
python scripts/aios_gate_chair_eval.py --mode current --prompt 'AIOS에는 gate 역할의 Agent가 있나? 아니면 시스템 답변밖에 못하나?' --json
```

Pass criteria:

- Tests prove tied external candidates with zero failures become
  `promotion_ready`.
- Live matrix writes a report under `.aios/evals/gate_chair_matrix/`.
- Live single eval does not promote a provider if any current Chair run times
  out or fails.
- Failure draft is sent to MemoryOS review and remains `needs_more_evidence`.
- Gate Chair/provider turn artifacts do not persist raw command argv, PINs, API
  keys, emails, or raw private provider prompts.

## Receipts

- candidate_matrix:
  `.aios/evals/gate_chair_matrix/fe4408ac3749b4de/report.json`
- single_eval_timeout:
  `.aios/evals/gate_chair/0e5c3debdf207a41/report.json`
- memory_review_request:
  `.aios/inbox/memoryOS/mdrev-516592f120c5324c.memoryOS.json`
- memory_review_result:
  `.aios/outbox/memoryOS/mdrev-516592f120c5324c.memoryOS.result.json`
- current_chair_live_eval:
  `.aios/evals/gate_chair/78ebcc65c91c076c/report.json`
- redacted_chair_turn:
  `.aios/chat/gate-chair-eval-78ebcc65c91c076c-current-1/gate_chair_turns.jsonl`
- promotion_ready_eval:
  `.aios/evals/gate_chair/d43d018641cbb600/report.json`
- active_runtime_config:
  `.aios/gate/founder/chair_runtime.json`
- active_chat_smoke:
  `.aios/chat/gate-chair-active-smoke/gate_chair_turns.jsonl`

## Stop Conditions

- `provider_chair_promoted_with_failed_run`
- `tie_claimed_as_reasoning_improvement`
- `runtime_failure_not_reviewed_by_memoryos`
- `provider_secret_or_pin_written_to_artifact`
- `internal_baseline_bypassed`
- `verification_gate_failed`

## Work Packets

### WP-0188-A — Codex@myworld adjusts Gate Chair activation policy

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-17
- accepted: 2026-05-17
- closed: 2026-05-17
- brief: |
    Make external Gate Chair candidates promotable when they match or beat the
    internal baseline without failures. Keep runtime failure evidence as
    MemoryOS draft-first negative evidence. Do not promote a timed-out
    provider Chair.
- result: this contract and the receipts listed above.
