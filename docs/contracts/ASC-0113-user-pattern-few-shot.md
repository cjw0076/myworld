---
contract_id: ASC-0113
slug: user-pattern-few-shot
status: closed
goal: Capture user (founder + future users) activity logs across all substrates, extract behavior patterns, and inject them as few-shot examples into every substrate call so AIOS responses progressively match user style without per-turn fine-tuning. Layer 1 of organism arc — the body's nervous system that learns its host.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude as verifier (founder GO "few shot 학습")
closed: 2026-05-13 KST
acceptance_authority: claude@myworld (verifier role) per founder direct delegation.
origin: founder vision "사용자의 로그, 작업방식을 흡수하고 user의 행동 패턴을 few shot 학습". Builds on ASC-0111 (founder behavior ingestion) and ASC-0112 (chat wrapper).
---

# ASC-0113 User Pattern Few-Shot Learning (L1 of organism arc)

DNA references: Invariant 2 (draft-first — patterns are draft until reviewed),
Invariant 5 (provenance — patterns trace to specific user turns),
Invariant 7 (private data never sent — patterns must not leak founder PII).

## Why Now

Founder behavior ingestion (ASC-0111) captures WHAT founder said.
But substrates don't USE this. Each Claude/Codex/Ollama call still
starts from generic system prompt. AIOS reads founder once, then
forgets behaviorally.

ASC-0113 closes the gap: extract patterns from accumulated user
activity, inject as few-shot examples in every substrate call. Over
time the substrate's outputs match user style without changing the
model.

This is what makes AIOS "alive" — body that adapts to its host.

## Required Reading

- `docs/contracts/ASC-0111-founder-behavior-ingestion.md`
  (depends — provides directive corpus)
- `docs/contracts/ASC-0112-aios-chat-wrapper.md`
  (depends — provides chat history corpus)
- `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`
  (operator self-observation — also a pattern source)
- `memoryOS/memoryos/store.py` (for stable_id pattern storage)
- `scripts/aios_invoke.py` (where few-shots get injected)

## Scope

repos: `myworld`, `memoryOS`

allowed_files:

- `scripts/aios_pattern_extractor.py`
- `scripts/aios_few_shot_injector.py`
- `scripts/aios_chat_router.py` (extend to call injector)
- `scripts/aios_invoke.py` (extend to include patterns in plan)
- `tests/test_aios_pattern_extractor.py`
- `tests/test_aios_few_shot_injector.py`
- `tests/test_aios_chat_router.py`
- `tests/test_aios_invoke.py`
- `docs/AGENT_WORKLOG.md`
- `memoryOS/memoryos/cli.py` (new `extract-patterns` if needed)
- `memoryOS/memoryos/schema.py`
- `memoryOS/tests/test_pattern_extract.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `docs/AIOS_USER_PATTERNS.md`
- `docs/contracts/ASC-0113-user-pattern-few-shot.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `~/.claude/**` (claude private — don't drag into shared corpus)
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `hivemind/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

`aios_pattern_extractor.py`:
- inputs: founder_directive drafts (ASC-0111), chat history (ASC-0112),
  operator session log
- extracts:
  - language preference (Korean/English ratio, formality)
  - decision style (terse / verbose / question-first)
  - response pattern preferences (what founder accepts/rejects)
  - reframe patterns (founder's habitual reframes)
- output: `aios.user_pattern.v1` — `{user_id, patterns[], confidence,
  evidence_refs}`

`aios_few_shot_injector.py`:
- inputs: a substrate prompt about to be sent
- looks up patterns for current user
- injects up to N (default 3) verbatim user turns + agent successful
  responses as few-shot examples
- never injects: secrets, private founder context, raw private docs
- records: `{prompt_hash, patterns_injected[], substrate}` for audit

Integration:
- `aios_chat_router.py` calls injector before substrate call
- `aios_invoke.py` includes patterns in plan output

### memoryOS.must_produce

- `extract-patterns` subcommand (or extend existing) that aggregates
  founder_directive drafts into `MemoryObject(type=user_pattern,
  status=draft, origin=pattern_extracted)`
- patterns are draft until operator reviews — reuses existing review CLI

### child repos: no other change

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m py_compile scripts/aios_pattern_extractor.py scripts/aios_few_shot_injector.py scripts/aios_chat_router.py scripts/aios_invoke.py
python -m unittest tests/test_aios_pattern_extractor.py tests/test_aios_few_shot_injector.py tests/test_aios_chat_router.py tests/test_aios_invoke.py
python scripts/aios_pattern_extractor.py --write .aios/patterns/founder/patterns.json --json
python scripts/aios_few_shot_injector.py --substrate-prompt "test prompt" --user founder --json
python scripts/aios_chat_router.py --message "summarize pattern injection" --conversation asc-0113-chat-smoke --json
python scripts/aios_invoke.py --goal "AIOS should inject founder user patterns into plan" --write .aios/invocations/asc-0113-smoke --json
python -m unittest discover -s tests -p 'test_aios_*.py'
cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m py_compile memoryos/cli.py memoryos/schema.py
python -m pytest tests/test_pattern_extract.py tests/test_retrieval.py -q
python -m pytest tests/test_sprint4.py -q
```

Pass criteria (DNA-cited):

- ≥5 patterns extracted from current 1.5-day corpus (Inv 5: provenance)
- Each pattern cites source directives (Inv 2: draft-first, must trace)
- Injector excludes private/secret content (Inv 7: never sent)
- Pattern memory drafts stay status=draft until review (Inv 2)

## Stop Conditions

- `pattern_includes_pii`: PII / secrets / private exports never enter pattern
- `pattern_auto_accept`: patterns must remain draft
- `pattern_overrides_invariant`: few-shot must not coax substrate to violate
  DNA invariants (especially 1, 6, 7)
- `pattern_silently_changes_response`: chat reply must record
  `patterns_injected: [...]` so user can see what shaped the response
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- myworld_result: `.aios/outbox/myworld/asc-0113.myworld.result.json`
- memoryos_result: `.aios/outbox/memoryOS/asc-0113.memoryOS.result.json`
- memoryos_commit: `memoryOS/8a0a4be`
- pattern_artifact: `.aios/patterns/founder/patterns.json`
- pattern_audit: `.aios/patterns/founder/injections.jsonl`
- evidence:
  - `python -m py_compile scripts/aios_pattern_extractor.py scripts/aios_few_shot_injector.py scripts/aios_chat_router.py scripts/aios_invoke.py`
    exited 0.
  - `python -m unittest tests/test_aios_pattern_extractor.py tests/test_aios_few_shot_injector.py tests/test_aios_chat_router.py tests/test_aios_invoke.py`
    passed 14/14.
  - `python scripts/aios_pattern_extractor.py --write .aios/patterns/founder/patterns.json --json`
    extracted 6 draft patterns from 86 founder directives, 12 chat messages,
    and 80 self-observation rows.
  - `python scripts/aios_few_shot_injector.py --substrate-prompt "test prompt" --user founder --json`
    injected 3 draft patterns and wrote an audit row.
  - `python scripts/aios_chat_router.py --message "summarize pattern injection" --conversation asc-0113-chat-smoke --json`
    returned `patterns_injected` and `pattern_injection_audit`.
  - `python scripts/aios_invoke.py --goal "AIOS should inject founder user patterns into plan" --write .aios/invocations/asc-0113-smoke --json`
    wrote Hive plan `user_patterns.status=draft`.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 265/265.
  - `cd memoryOS && python -m pytest tests/test_pattern_extract.py tests/test_retrieval.py -q`
    passed 3/3.
  - `cd memoryOS && python -m pytest tests/test_sprint4.py -q` passed 964/964.

## Work Packets

### WP-0113-A — codex@myworld extractor + injector + integration

- target_agent: codex
- target_repo: myworld
- status: done
- depends_on: ASC-0111 closed, ASC-0112 closed
- brief: extractor + injector + wire into chat_router + invoke. Tests
  for 5+ pattern extraction and PII exclusion. Dogfood: extract from
  current session, show top 5 patterns.
- result: `scripts/aios_pattern_extractor.py`,
  `scripts/aios_few_shot_injector.py`, chat router integration, invoke plan
  integration, docs, tests, and dispatch result completed.

### WP-0113-B — codex@memoryOS pattern memory type

- target_agent: codex
- target_repo: memoryOS
- status: done
- depends_on: WP-0113-A
- brief: support type=user_pattern + origin=pattern_extracted in
  schema. Existing review lifecycle applies.
- result: MemoryOS commit `8a0a4be` preserves `type=user_pattern` and
  `origin=pattern_extracted` through `import-run` as draft MemoryObjects.
