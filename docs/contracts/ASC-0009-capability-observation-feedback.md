---
contract_id: ASC-0009
slug: capability-observation-feedback
status: accepted
goal: Consume task-radar entries and dispatch result packets to record CapabilityOS observations and fallback plans.
created: 2026-05-11 KST
accepted: 2026-05-11 KST by claude acting operator
closed: pending
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST.
origin: auto-proposed by `scripts/aios_doc_scout.py` (ASC-0007 output).
---

# ASC-0009 CapabilityOS Observation Feedback

## Control Plane Position

Issued and accepted by `claude@myworld`. CapabilityOS owns the implementation. The control plane delivers the dispatch result corpus and the radar; CapabilityOS converts those into capability cards / observations.

## Goal

ASC-0002 closed CapabilityOS V1 as recommendation-only against a static fixture catalog. ASC-0009 makes it **learn from real AIOS dispatches**: every closed contract's result packet (`.aios/outbox/<repo>/*.result.json`) and every signal in `docs/AIOS_TASK_RADAR.md` becomes a capability observation that updates the catalog's confidence/evidence_refs without changing the recommendation-only invariant.

V1 scope:
- Ingest `aios.dispatch.result.v1` packets and radar JSON.
- Emit a `CapabilityObservation` (new dataclass) per (capability_id, dispatch_id) pair: `outcome`, `latency_seconds`, `child_agent`, `repo`, `evidence_refs`.
- Update `CapabilityCard.evidence_refs` and a derived `confidence` field. Do NOT auto-add new capabilities; only observe existing ones.
- Optionally surface "needs new capability" gaps in a separate file for operator review (= future ASC-NNNN).

Explicitly does **not**:
- execute any tool (recommendation-only invariant from ASC-0002 stays).
- modify hivemind or memoryOS source.
- auto-add capabilities — operator must approve catalog changes.

## Open Design Questions

To be answered by `codex@CapabilityOS` (WP-0009-A):

- **Q1 — Observation shape**: minimum fields. Recommend: `capability_id, dispatch_id, contract_id, child_agent, repo, outcome (passed|failed|timeout|skipped), latency_seconds, evidence_refs[], observed_at`.
- **Q2 — Confidence update rule**: how does observation outcome update `CapabilityCard.confidence`? Recommend: simple Beta(α=passed+1, β=failed+1) mean. Justify simpler alternatives.
- **Q3 — CLI surface**: `capabilityos observe-results --inbox <path>` consuming `.aios/outbox/`? Or direct ingest from `dispatches.jsonl`? Recommend the outbox path because it is the canonical L4 evidence.
- **Q4 — "Needs new capability" gap output**: separate JSON file (`CapabilityOS/data/observed_gaps.json` if `data/` is gitignored) or stdout only? Recommend stdout-only for V1.
- **Q5 — Schema versioning**: new `aios.capability_observation.v1` schema, or extend existing card? Recommend a new sibling schema for non-destructive evolution.

## Scope (stub — WP-0009-A fills)

- repos: `[CapabilityOS, myworld]` — myworld provides the result corpus and radar; CapabilityOS implements observation ingestion.
- allowed_files: _to be filled — at minimum `CapabilityOS/capabilityos/observation.py` (new), `CapabilityOS/capabilityos/cli.py` (extend), `CapabilityOS/capabilityos/schema.py` (extend), `CapabilityOS/tests/test_observation.py` (new), `CapabilityOS/tests/fixtures/capabilities.json` (extend evidence_refs)._
- forbidden_files: `hivemind/**`, `memoryOS/**`, `myworld/scripts/aios_doc_scout.py`, `_from_desktop/**`, `dain/**`, raw exports, secrets, weights.

## Per-OS Responsibility (stub)

- **capabilityos.must_produce**: observation dataclass + CLI + ingestion + tests; updated catalog with evidence_refs from real ASC-0001..0007 closeouts.
- **myworld.must_produce**: nothing further; result packets and radar already exist.
- **hive_mind / memoryos**: not in scope.
- **operator.must_produce**: closeout review, confirm recommendation-only invariant intact.

## Verification Gate (stub)

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_observation.py -v
python -m capabilityos.cli observe-results --inbox /home/user/workspaces/jaewon/myworld/.aios/outbox --json
python -m capabilityos.cli audit --json
```

Expected evidence:
- pytest passes.
- observe-results returns N observations matching the count of `.aios/outbox/*/*.result.json` files with `status in {passed, done}`.
- audit `execution_enabled` remains `[]` and `recommendation_only` remains `true`.
- catalog gains evidence_refs entries pointing to real result packets and contract paths.

## Stop Conditions (stub)

- `execution_creep`: any code path executes a tool or makes a network call.
- `auto_catalog_grow`: V1 adds new capabilities without operator approval.
- `child_repo_source_edit`: ASC-0009 modifies hivemind, memoryOS, or other child repo source.
- `observation_overwrite`: ingestion mutates existing observations instead of appending.
- `confidence_overclaim`: confidence score not bounded by evidence count (e.g. 1.0 from a single passing run).
- `private_data_in_observation`: observations carry raw stdout, log bodies, secrets.

## Receipts

_filled at closeout._

## Work Packets

### WP-0009-A — Codex@CapabilityOS implements observation feedback

- target_agent: codex
- target_repo: CapabilityOS
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: ASC-0002 closed (V1 catalog), ASC-0007 closed (radar shape stable)
- brief: |
    Fill ASC-0009 stub sections and answer Q1–Q5. Implement
    `observe-results` CLI + observation schema + tests in CapabilityOS.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0002-capabilityos-executable-surface.md
      3. /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md
      4. /home/user/workspaces/jaewon/myworld/docs/discoveries/2026-05-11-jaewon-search.md
      5. /home/user/workspaces/jaewon/myworld/CapabilityOS/capabilityos/schema.py
      6. /home/user/workspaces/jaewon/myworld/CapabilityOS/capabilityos/cli.py
      7. /home/user/workspaces/jaewon/myworld/.aios/outbox/ (real result packets)

    Constraints:
    - Recommendation-only invariant from ASC-0002 must stay.
    - No auto-add of capabilities.
    - Append-only observations (no overwrite).
    - Confidence update rule must be evidence-bounded (Beta or equivalent).

    After drafting + implementing:
    - Update WP-0009-A status, fill `result` with commit SHA(s).
    - Issue WP-0009-B for claude review.
- result: pending
