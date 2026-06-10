---
contract_id: ASC-0031
slug: web-evidence-execution-loop
status: closed
goal: Dogfood CapabilityOS web-route by producing and validating a cited web evidence receipt for AIOS capability routing.
created: 2026-05-12 14:13 KST
accepted: 2026-05-12 14:13 KST
closed: 2026-05-12 14:16 KST
---

# ASC-0031 Web Evidence Execution Loop

## Why Now

ASC-0030 gave CapabilityOS a broad web research route, but route planning alone
does not prove AIOS can use web evidence. This contract executes one bounded
web research pass through the acting myworld operator, records cited evidence,
and adds a validator so future web research artifacts are machine-checkable.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_web_research_receipt.py`
- `tests/test_aios_web_research_receipt.py`
- `docs/evidence/ASC-0031-web-evidence.json`
- `docs/contracts/ASC-0031-web-evidence-execution-loop.md`
- `docs/contracts/README.md`
- `docs/goals/AIOS-GOAL-0001-make-something-great.md`
- `docs/goals/AIOS-GOAL-0001-evolution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.aios/logs/**`
- `.aios/outbox/**`
- `.aios/inbox/**`
- `.env`
- raw export paths
- browser caches or downloaded web archives

## Responsibilities

### myworld.must_produce

- A web evidence receipt JSON using CapabilityOS `web-route` policy.
- A validator that checks receipt shape, source URLs, cited claims, route
  contract, privacy guardrails, and no raw page bodies.
- Contract closeout, dispatch/release record, goal update, and ledger entry.

### capabilityos.must_produce

- No source change. ASC-0030 `web-route` output is the route authority.

### hive_mind.must_produce

- No source change. Future contracts may move execution into Hive harness; this
  contract validates the artifact shape first.

### memoryos.must_produce

- No source change. Future contracts may import selected web evidence into
  MemoryOS review as source artifacts or memory drafts.

## Research Question

What current public evidence supports AIOS treating broad web research as a
first-class capability route with source policy, tool routing, and guardrails?

## Verification Gate

```bash
python -m unittest tests/test_aios_web_research_receipt.py
python scripts/aios_web_research_receipt.py validate docs/evidence/ASC-0031-web-evidence.json
python -m unittest tests/test_aios_instruction_index.py tests/test_aios_loop_policy.py tests/test_aios_doc_scout.py tests/test_aios_readiness.py tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py tests/test_aios_goal_evolution.py tests/test_aios_child_watcher.py tests/test_aios_round_controller.py tests/test_aios_web_research_receipt.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Receipt validates.
- Receipt cites at least three public sources.
- Each source has URL, publisher, accessed_at, claims, and source type.
- Receipt references `capabilityos.web_research_route.v1`.
- Full myworld tests pass and monitor remains clear.

## Stop Conditions

- `uncited_claim`: receipt makes a web-derived claim without source URL.
- `raw_page_body_committed`: receipt stores copied raw page bodies instead of
  short claims/paraphrases.
- `privacy_violation`: receipt includes secrets, personal data, raw private
  exports, or credentialed pages.
- `capability_route_missing`: receipt does not reference the CapabilityOS
  `web-route` plan.
- `stale_source_policy`: current-topic source has no accessed date or source
  date when available.

## Receipts

- Web evidence receipt: `docs/evidence/ASC-0031-web-evidence.json`.
- Validator: `scripts/aios_web_research_receipt.py`.
- Dispatch: `.aios/inbox/myworld/asc-0031.myworld.json`.
- Result packet: `.aios/outbox/myworld/asc-0031.myworld.result.json`.
- Release: `python scripts/aios_dispatch.py release --dispatch-id asc-0031
  --reason asc_0031_web_evidence_execution_loop_verified`.
- Verification:
  - `python -m unittest tests/test_aios_web_research_receipt.py` passed 5/5.
  - `python scripts/aios_web_research_receipt.py validate
    docs/evidence/ASC-0031-web-evidence.json` passed.
  - Full myworld suite with the new web receipt tests passed 47/47.
  - Final `python scripts/aios_monitor.py assess --json` returned
    `health=clear`.

## Work Packets

### WP-0031-A — Codex@myworld executes and validates one web evidence pass

- target_agent: codex
- target_repo: myworld
- status: accepted
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: ASC-0030
- brief: |
    Use CapabilityOS `web-route` as the route authority, perform one bounded
    web research pass with public sources, write
    `docs/evidence/ASC-0031-web-evidence.json`, add a validator, and close the
    contract with verification evidence.
- result: `.aios/outbox/myworld/asc-0031.myworld.result.json`
