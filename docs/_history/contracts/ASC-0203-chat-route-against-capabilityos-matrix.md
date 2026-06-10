---
contract_id: ASC-0203
slug: chat-route-against-capabilityos-matrix
status: closed
closed: 2026-05-18 KST
closeout_authority: claude@myworld operator — Named Exit met; 45 router tests pass.
goal: Make the chat router pick a substrate from the CapabilityOS recommendation matrix (id / cost / confidence / rank) instead of substring-matching the capability payload's JSON dump.
created: 2026-05-18 KST
proposed_by: claude@myworld
accepted: 2026-05-18 KST
acceptance_authority: claude@myworld operator — routine ASC-0192 follow-on, no escalation rule triggers; bounded change to one router function with test coverage.
origin: ASC-0192 follow-on item 2 ("route against CapabilityOS live"). Operator review of aios_chat_router.choose_substrate found provider_candidates_from_capability does `json.dumps(payload).lower()` then `"ollama" in text` / `"claude" in text` — it ignores the structured `recommendations` array (id, cost, confidence, kind, rank) that CapabilityOS actually emits. The same keyword anti-pattern ASC-0192 removed from tier-1 classification still governs route selection.
---

# ASC-0203 Chat — Route Against the CapabilityOS Matrix

DNA references: Invariant 1 (recommendation-only — CapabilityOS recommends, the
router chooses), Invariant 8 (classify/route before committing).

## The problem (operator-verified)

The capability artifact (`<invocation>/capability/route.json`) is a structured
matrix:

```
recommendations: [
  {id: cap_hivemind_execution_harness, cost: free, confidence: 0.8, kind: harness},
  {id: cap_aios_readiness_scorer,      cost: free, confidence: 0.7, kind: harness},
  ...
]
```

`provider_candidates_from_capability` discards all of it — it stringifies the
whole payload and tests `"ollama" in text`. Consequences:

- **Rank ignored** — a low-confidence mention and the top recommendation are
  treated identically; order is `[ollama, claude, codex, gemini]` hardcoded.
- **Cost ignored** — `cost: free` vs a paid route never influences selection.
- **False positives** — any incidental "claude"/"codex" substring anywhere in
  the payload (a description, an evidence path) injects that provider as a
  candidate.

## Required outcome

1. `provider_candidates_from_capability` parses `recommendations`: for each
   rec, map `id` + `domains` → a substrate (`ollama_qwen` / `claude` /
   `codex` / `gemini`), preserving the recommendation rank order.
2. Within rank, a `cost: free` recommendation is preferred (local-first stays
   the AIOS default; ASC-0192 stop condition); `confidence` breaks ties.
3. The JSON-substring scan is kept **only as the fallback** when the payload
   carries no `recommendations` array — the layer degrades, it does not break
   (same pattern as tier-1's keyword fallback).
4. `choose_substrate` behavior is unchanged for the override / gate-decision /
   multi_step paths — this contract only sharpens the capability-driven branch.

## Named Exit

Closed when: `provider_candidates_from_capability` ranks substrates from the
`recommendations` matrix; a payload with a structured matrix routes by
rank+cost, not substring order; a payload without `recommendations` still
yields candidates via the fallback; `tests/test_aios_chat_router.py` covers
all three and passes.

## Stop Conditions

- If the capability matrix recommends only non-executing/abstract cards (no
  mappable substrate), fall back to `local_llm` — never return an empty route.

## Work Packets

### codex@myworld

Implement items 1-4 in `scripts/aios_chat_router.py`; add the three test
cases to `tests/test_aios_chat_router.py`.

## Implementation Receipts

Executed by claude@myworld operator (same loop iteration as the ASC-0192
follow-on review).

- `scripts/aios_chat_router.py` — `provider_candidates_from_capability`
  rewritten: when the payload carries dict `recommendations`, each rec is
  mapped to a substrate by `id`+`domains` (`_capability_rec_substrate`,
  new), the rec rank (CapabilityOS confidence order) is preserved, and a
  stable sort stable-prefers `cost: free`. A matrix that maps to no provider
  card returns `["ollama_qwen"]` (stop condition — never empty). A payload
  with no dict `recommendations` degrades to the prior JSON-substring scan.
- `tests/test_aios_chat_router.py` — three cases added:
  `test_capability_matrix_routes_by_rank_and_cost` (free local stable-preferred
  over a higher-confidence metered card; harness card dropped),
  `test_capability_matrix_with_no_provider_card_defaults_local` (stop
  condition), `test_capability_payload_without_matrix_uses_substring_fallback`.
- verification: `python -m unittest tests.test_aios_chat_router` → 45 passed
  (42 prior + 3 new); `python -m py_compile scripts/aios_chat_router.py
  tests/test_aios_chat_router.py` passed; `git diff --check` clean.
- note: two prior tests pass `recommendations` as a list of free-text
  strings (a legacy fixture shape, not the real CapabilityOS dict matrix).
  The implementation only engages the matrix path when ≥1 dict rec is
  present, so those tests still exercise the substring fallback and pass
  unchanged.

ASC-0192 follow-on item 2 is now done. Items 1 (ASC-0193, closed) and 3
(multi-agent surface) remain; item 3 still needs its own follow-on contract
before ASC-0192 closes.
