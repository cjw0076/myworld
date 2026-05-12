---
contract_id: ASC-0063
slug: uri-content-relevance-filter
status: accepted
goal: Filter Uri-originated markdown so AIOS absorbs only cross-OS-relevant insights (pivots, friction surfaced to myworld, AIOS-protocol observations) and skips product-internal material (route configs, page specs, sprint deliverables) without losing audit trail.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated)
closed:
acceptance_authority: claude@myworld (operator) per founder directive "uri쪽에서 계속 md 파일 주입하고있는데 필요한 것만 잘 걸러내야 해 이것 또한 aios의 역할".
origin: founder operational observation 2026-05-13 KST. uri/ submodule is actively generating product docs as the team builds Uri's personal-agent loop. doc_scout currently has no Uri-aware filter and treats every md as a candidate signal — polluting AIOS task radar with product-internal noise.
---

# ASC-0063 Uri Content Relevance Filter

## Why Now

Uri repo is doing real product work (campus personal agent loop). It
generates two distinct classes of docs:

**Class A — AIOS-relevant** (should flow up):
- `uri/docs/AGENT_WORKLOG.md` — what Uri agents are doing
- `uri/docs/URI_*` north-star / operating model docs
- `uri/docs/MEMORY_POLICY.md`, `LEGAL_ETHICAL_GUARDRAILS.md` — cross-OS contract
- Anything that maps to existing AIOS shared-language terms (contract,
  dispatch, memory draft, capability route, hive execution)
- Cross-OS friction notes already proven valuable (e.g. Uri pivot
  discovery 2026-05-12)

**Class B — Uri-internal** (should stay in uri/):
- Product specs (`products/digital-campus/*`)
- Route configs (`*ROUTE_ARCHITECTURE.md`, page specs)
- Sprint deliverables
- Hive packets (`uri/hive/packets/URI-*`)
- Service concept docs
- UI/UX mockups

The current `aios_doc_scout.py` treats both classes identically. AIOS
task radar gets polluted; pulse signals become noisy; memory drafts
contain irrelevant entries.

This contract adds a Uri-aware relevance classifier that gates which
Uri md files flow into AIOS pipelines, and routes the borderline cases
to operator review.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_doc_scout.py`
- `scripts/aios_uri_filter.py`
- `tests/test_aios_uri_filter.py`
- `docs/AIOS_URI_FILTER_POLICY.md`
- `docs/contracts/ASC-0063-uri-content-relevance-filter.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `uri/**` (filter reads uri but never writes)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `scripts/aios_uri_filter.py` — classifier with three outcomes per md file:
  - `aios_relevant` → flow into doc scout signals normally
  - `uri_internal` → silently skip (logged in filter receipt)
  - `operator_review` → write to `.aios/uri_review_queue/<file-hash>.md`
    for human triage
- Classification rules (V1, simple + auditable):
  - **aios_relevant** if path matches whitelist:
    - `uri/docs/URI_NORTHSTAR.md`
    - `uri/docs/AGENT_WORKLOG.md`
    - `uri/docs/MEMORY_POLICY.md`
    - `uri/docs/AIOS_*.md`
    - `uri/docs/CAPABILITY_MAP.md`
    - `uri/docs/LEGAL_ETHICAL_GUARDRAILS.md`
    - `uri/AGENTS.md`
    - file body contains ≥2 AIOS shared-language terms from
      `docs/AIOS_SHARED_LANGUAGE.md` (contract, dispatch, draft,
      capability, hive)
  - **uri_internal** if path matches denylist:
    - `uri/products/**`
    - `uri/hive/packets/**`
    - `uri/research/**`
    - `uri/capabilities/**` (uri-local capability docs)
    - `uri/memory/**` (uri-local memory store)
  - **operator_review** otherwise
- `aios_doc_scout.py` calls `aios_uri_filter.classify(path)` before
  emitting a signal. Counts per outcome go into scout receipt.
- Tests: synthetic files for each path, verify outcome. Real
  `uri/docs/URI_NORTHSTAR.md` → `aios_relevant`. Real
  `uri/products/digital-campus/ROUTE_ARCHITECTURE.md` → `uri_internal`.
- `docs/AIOS_URI_FILTER_POLICY.md` — written rules, how to extend,
  how operator can promote a file from review_queue to whitelist.

### uri repo

- No source change. Filter reads only.

## Verification Gate

```bash
python -m py_compile scripts/aios_uri_filter.py
python -m unittest tests/test_aios_uri_filter.py
python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --limit 80 --json > /tmp/radar.json
python -c "
import json
d = json.load(open('/tmp/radar.json'))
# Check uri filter counts in receipt
counts = (d.get('uri_filter_counts') or {})
print('uri_filter counts:', counts)
assert counts.get('aios_relevant', 0) > 0, 'should classify at least one uri doc as relevant'
assert counts.get('uri_internal', 0) > 0, 'should classify at least one as internal'
"
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Synthetic files classify per the rules.
- Real Uri repo scan produces at least one of each category.
- Operator_review queue file is created for borderline real cases.
- Full test suite green.

## Stop Conditions

- `filter_writes_to_uri`: filter must read-only.
- `filter_drops_silently`: every `uri_internal` skip must be counted in
  receipt; no silent drops.
- `whitelist_bypass`: filter cannot mark a file `aios_relevant` if it
  matches the denylist (denylist wins on conflict).
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0063-A — codex@myworld implements Uri filter + scout integration

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Implement `aios_uri_filter.py` with the V1 rules, wire it into
    `aios_doc_scout.py` so each uri md is classified before becoming
    a signal, add tests, write the policy doc. Dogfood: run scout on
    real workspace and report counts. Operator review queue starts
    empty until first real run surfaces a borderline file.
- result: pending
