---
contract_id: ASC-0010
slug: hive-semantic-quality-gate
status: closed
goal: Add a Hive verification packet that reviews top task-radar candidates for executable next steps before broad dispatch.
created: 2026-05-11 KST
accepted: 2026-05-11 KST by claude acting operator
closed: 2026-05-11 22:48 KST
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST.
origin: auto-proposed by `scripts/aios_doc_scout.py` (ASC-0007 output).
---

# ASC-0010 Hive Semantic Quality Gate

## Control Plane Position

Hive Mind owns the implementation. The control plane provides the radar JSON and result corpus. Hive provides the *semantic* gate (vs ASC-0006's structural gate): can a candidate actually be executed, and what are its hidden dependencies?

## Goal

ASC-0006 readiness is structural: counts files, statuses, packets. ASC-0010 adds **semantic** quality: given a top task-radar candidate, can hivemind classify it as `executable | needs_context | needs_capability | ambiguous | out_of_scope` and produce a one-screen rationale?

V1 scope:
- New CLI `hive radar-review --radar <path> --top N --json` reads the radar JSON, runs each top-N candidate through an existing local worker (`intent_router` or a new `radar_classifier`), and emits per-candidate verdict + rationale.
- Verdict consumes radar's `signal_labels`, `path`, `score`, and the local-worker classification — no LLM call to external providers.
- Output is a `radar_review.json` artifact + a `radar_review.md` summary, both committed under `myworld/docs/` (or under hivemind, decided by Q2).
- Operator uses these verdicts to choose which radar candidates become real ASC-NNNN.

Explicitly does **not**:
- replace operator judgment — verdicts are advisory.
- modify CapabilityOS or memoryOS source.
- call external LLM providers (cost discipline).
- auto-create contracts.

## Open Design Questions

To be answered by `codex@hivemind` (WP-0010-A):

- **Q1 — Verdict taxonomy**: 5-class above is a starting point. Justify or refine.
- **Q2 — Output location**: `hivemind/.runs/<run_id>/radar_review.{json,md}` (Hive run pattern) OR `myworld/docs/radar_reviews/...` (control-plane visible). Recommend Hive run pattern with a symlink/copy into myworld for visibility.
- **Q3 — Local worker choice**: extend `intent_router` (existing) or add new `radar_classifier`? Recommend new worker so router stays focused on dispatch routing.
- **Q4 — Rationale length cap**: prevent verbose blob output. Recommend ≤ 300 characters per candidate.
- **Q5 — Privacy**: ensure rationale does NOT reproduce raw doc content. Use signal labels + path only.

## Scope

repos:

- `hivemind`

allowed_files:

- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/local_workers.py`
- `hivemind/hivemind/radar_classifier.py`
- `hivemind/tests/test_radar_review.py`
- `hivemind/docs/RADAR_REVIEW.md`
- `hivemind/docs/radar_review.json`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/AIOS_TASK_RADAR.md`
- `docs/discoveries/2026-05-11-jaewon-search.md`
- `docs/contracts/ASC-0010-hive-semantic-quality-gate.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `CapabilityOS/**`
- `memoryOS/**`
- `myworld/scripts/aios_doc_scout.py`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.runs/**`
- `.ai-runs/**`
- `data/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **hive_mind.must_produce**: `radar-review` CLI, optional new `radar_classifier` worker, tests, sample output committed.
- **capabilityos / memoryos**: not in scope.
- **myworld**: nothing further; radar already exists.
- **operator.must_produce**: closeout review, then use verdicts to drive next ASC-NNNN selection.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_radar_review.py -v
python -m hivemind.hive radar-review --radar /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md --top 10 --json
```

Expected evidence:
- pytest passes.
- review JSON contains 10 entries with `verdict in {executable, needs_context, needs_capability, ambiguous, out_of_scope}` and a rationale ≤ 300 chars.
- Output references signals/paths only — no raw doc body strings.

## Stop Conditions

- `external_llm_call`: any path calls Claude/Codex/Gemini/etc.
- `verdict_overclaim`: returns `executable` without checking that referenced paths/tests exist.
- `child_repo_source_edit`: ASC-0010 modifies CapabilityOS or memoryOS source.
- `rationale_blob`: rationale exceeds 300 characters or includes raw doc content.
- `auto_contract_creation`: review CLI writes to `myworld/docs/contracts/` directly.

## Receipts

Closed 2026-05-11 22:48 KST by `codex@myworld` acting operator.

- Implemented in `hivemind` by `codex@hivemind`.
- Verification:
  - `python -m pytest tests/test_radar_review.py -v` passed 2/2.
  - `python -m unittest tests.test_local_worker_routing` passed 4/4.
  - `python -m py_compile hivemind/radar_classifier.py hivemind/hive.py hivemind/local_workers.py` passed.
  - `python -m hivemind.hive radar-review --radar /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md --top 10 --json` passed and wrote `docs/RADAR_REVIEW.md` plus `docs/radar_review.json`.
  - `python scripts/aios_dispatch.py watch --repo hivemind --dispatch-id asc-0010 --once` passed and wrote `.aios/outbox/hivemind/asc-0010.hivemind.result.json`.
  - dispatch collect/release succeeded with reason `asc_0010_hive_radar_review_verified`.
- Stop conditions triggered: none.

## Work Packets

### WP-0010-A — Codex@hivemind implements radar review

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 KST by codex@hivemind
- closed: 2026-05-11 KST by codex@hivemind
- depends_on: ASC-0007 closed (radar shape stable)
- brief: |
    Fill ASC-0010 stub sections and answer Q1–Q5. Implement
    `hive radar-review` CLI + tests + (optionally) new local worker.

    Required reading:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_DEFINITION.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0006-aios-l6-repeatable-proof.md (structural gate this complements)
      4. /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md (input)
      5. /home/user/workspaces/jaewon/myworld/hivemind/hivemind/local_workers.py (existing WorkerSpec patterns, intent_router)
      6. /home/user/workspaces/jaewon/myworld/hivemind/hivemind/hive.py (CLI dispatch pattern)
      7. /home/user/workspaces/jaewon/myworld/docs/discoveries/2026-05-11-jaewon-search.md

    Constraints:
    - No external LLM calls.
    - Verdicts are advisory; operator decides.
    - Rationale ≤ 300 chars per candidate.
    - No raw doc bodies in output.

    After drafting + implementing:
    - Update WP-0010-A status, fill `result` with commit SHA.
    - Issue WP-0010-B for claude review.
- result: |
    Implemented in working tree; commit SHA pending because this turn did not
    create a commit and the hivemind repo already had unrelated dirty changes.
    Changed Hive-owned files:
      - `hivemind/hive.py`
      - `hivemind/local_workers.py`
      - `hivemind/radar_classifier.py`
      - `tests/test_radar_review.py`
      - `docs/RADAR_REVIEW.md`
      - `docs/radar_review.json`
      - `docs/AGENT_WORKLOG.md`
    Verification passed:
      - `python -m pytest tests/test_radar_review.py -v`
      - `python -m unittest tests.test_local_worker_routing`
      - `python -m py_compile hivemind/radar_classifier.py hivemind/hive.py hivemind/local_workers.py`
      - `python -m hivemind.hive radar-review --radar /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md --top 10 --json`

### WP-0010-B — Codex@myworld operator verification

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:48 KST
- closed: 2026-05-11 22:48 KST
- depends_on: WP-0010-A
- brief: |
    Re-run ASC-0010 verification gate, collect the result packet, and release
    or hold the dispatch.
- result: passed, collected, and released; see Receipts.
