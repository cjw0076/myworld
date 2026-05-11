---
contract_id: ASC-0012
slug: child-repo-durability-closeout
status: closed
goal: Turn ASC-0008, ASC-0009, and ASC-0010 child-repo working-tree implementations into repo-local durable commits or explicit holds.
created: 2026-05-11 22:50 KST
accepted: 2026-05-11 22:50 KST by codex acting operator
closed: 2026-05-11 22:55 KST
supersedes: none
---

# ASC-0012 Child Repo Durability Closeout

## Control Plane Position

ASC-0008, ASC-0009, and ASC-0010 passed verification and were closed at the
control-plane level, but the implementation repos still contain dirty
working-tree changes. This contract prevents a false durable closeout by
requiring each child repo to either commit its owned implementation slice or
return an explicit hold reason.

`myworld` owns coordination only. Each child repo owns its own git commit or
hold decision.

## Goal

Stabilize child repo work after the radar feedback loop:

- `memoryOS`: ASC-0008 doc-radar ingest implementation.
- `CapabilityOS`: ASC-0009 observation feedback implementation, plus any
  still-uncommitted CapabilityOS V1 files required by that implementation.
- `hivemind`: ASC-0010 radar review implementation, plus ASC-0005 bridge files
  if they are still required by the current dirty tree.

Each repo must produce either:

- a repo-local commit SHA containing only the intended owned slice; or
- a result packet with `status=held` and a reason such as `unrelated_dirty_file`
  or `commit_scope_ambiguous`.

## Scope

repos:

- `memoryOS`
- `CapabilityOS`
- `hivemind`

allowed_files:

- `memoryOS/memoryos/cli.py`
- `memoryOS/memoryos/importers.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/store.py`
- `memoryOS/tests/test_doc_radar_ingest.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `CapabilityOS/README.md`
- `CapabilityOS/AGENTS.md`
- `CapabilityOS/CLAUDE.md`
- `CapabilityOS/pyproject.toml`
- `CapabilityOS/capabilityos/__init__.py`
- `CapabilityOS/capabilityos/__main__.py`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/capabilityos/observation.py`
- `CapabilityOS/capabilityos/schema.py`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/tests/test_observation.py`
- `CapabilityOS/tests/fixtures/capabilities.json`
- `hivemind/hivemind/capability_bridge.py`
- `hivemind/hivemind/hive.py`
- `hivemind/hivemind/local_workers.py`
- `hivemind/hivemind/radar_classifier.py`
- `hivemind/hivemind/run_validation.py`
- `hivemind/tests/test_capability_bridge.py`
- `hivemind/tests/test_radar_review.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `hivemind/docs/RADAR_REVIEW.md`
- `hivemind/docs/radar_review.json`
- `docs/contracts/ASC-0012-child-repo-durability-closeout.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/data/**`
- `CapabilityOS/data/**`
- `hivemind/data/**`
- `.aios/**`
- `.runs/**`
- `.ai-runs/**`
- `raw_exports/**`
- `exports/**`
- `logs/**`
- `weights/**`
- `**/*secret*`
- `**/*credential*`
- `.env`
- `.env.*`

## Per-OS Responsibility

- **memoryos.must_produce**: commit SHA for ASC-0008 implementation or hold
  reason; verification command output.
- **capabilityos.must_produce**: commit SHA for CapabilityOS V1 plus ASC-0009
  observation feedback or hold reason; recommendation-only audit output.
- **hive_mind.must_produce**: commit SHA for ASC-0010 radar review and any
  required bridge files or hold reason; radar-review verification output.
- **operator.must_produce**: release only if commits are scoped and tests pass;
  hold if unrelated dirty files cannot be separated safely.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/memoryOS
python -m pytest tests/test_doc_radar_ingest.py -v

cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py tests/test_observation.py -v
python -m capabilityos.cli audit --json

cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_capability_bridge.py tests/test_radar_review.py -v
python -m hivemind.hive radar-review --radar /home/user/workspaces/jaewon/myworld/docs/AIOS_TASK_RADAR.md --top 10 --json
```

Expected evidence:

- each target repo either has a commit SHA for its owned slice or an explicit
  hold result;
- no raw data, `.ai-runs`, `.runs`, logs, exports, weights, or secrets are
  committed;
- tests pass for committed slices;
- result packets cite commit SHA or hold reason.

## Stop Conditions

- `unrelated_dirty_file`: a target file contains pre-existing unrelated changes
  that cannot be safely separated.
- `private_runtime_commit`: commit would include raw data, runtime logs,
  `.ai-runs`, `.runs`, exports, weights, or secrets.
- `test_gate_failed`: target repo tests fail after staging the intended slice.
- `scope_ambiguous`: worker cannot determine which dirty lines belong to the
  contract.
- `cross_repo_commit_attempt`: one repo worker tries to commit another repo.

## Receipts

Closed 2026-05-11 22:55 KST by `codex@myworld` acting operator.

- `memoryOS`: committed `52ea40e` (`Add doc radar ingest`) for ASC-0008.
  Verification `python -m pytest tests/test_doc_radar_ingest.py -v` passed
  3/3. Result packet `.aios/outbox/memoryOS/asc-0012.memoryOS.result.json`.
- `CapabilityOS`: committed `a1fd15d` (`Add CapabilityOS recommendation
  surface`) covering CapabilityOS V1 plus ASC-0009. Verification `python -m
  pytest tests/test_cli.py tests/test_observation.py -v` passed 9/9 and
  `python -m capabilityos.cli audit --json` preserved
  `recommendation_only=true`. Result packet
  `.aios/outbox/CapabilityOS/asc-0012.CapabilityOS.result.json`.
- `hivemind`: committed `6320492` (`Add capability bridge and radar review
  gates`) covering ASC-0005 and ASC-0010 scoped files. Verification `python -m
  pytest tests/test_capability_bridge.py tests/test_radar_review.py -v` passed
  6/6, py_compile passed, and radar-review smoke returned 10 entries. Result
  packet `.aios/outbox/hivemind/asc-0012.hivemind.result.json`.
- dispatch collect/release succeeded with reason
  `asc_0012_child_repo_durability_verified`.
- Stop conditions triggered: none.
- Left uncommitted by design:
  - `memoryOS/docs/AGENT_WORKLOG.md` pre-existing unrelated hunk and
    `memoryOS/data/README.md` under forbidden `data/**`.
  - `hivemind/.ai-runs/shared/comms_log.md` under forbidden `.ai-runs/**` and
    `hivemind/hivemind/harness.py` ambiguous pre-existing change.

## Work Packets

### WP-0012-A — Codex@memoryOS durability closeout

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:50 KST
- closed: 2026-05-11 22:55 KST
- depends_on: ASC-0008
- brief: |
    Commit only the memoryOS-owned ASC-0008 doc-radar ingest slice or return
    `held` with a precise reason. Do not stage `memoryOS/data/**`.
- result: committed `52ea40e`; result packet passed.

### WP-0012-B — Codex@CapabilityOS durability closeout

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:50 KST
- closed: 2026-05-11 22:55 KST
- depends_on: ASC-0009
- brief: |
    Commit CapabilityOS V1 plus ASC-0009 observation feedback as a scoped
    CapabilityOS repo commit, or return `held` with a precise reason. Preserve
    recommendation-only invariant.
- result: committed `a1fd15d`; result packet passed.

### WP-0012-C — Codex@hivemind durability closeout

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:50 KST
- closed: 2026-05-11 22:55 KST
- depends_on: ASC-0005, ASC-0010
- brief: |
    Commit Hive-owned bridge/radar-review implementation files or return
    `held` with a precise reason. Do not stage `.ai-runs/**`.
- result: committed `6320492`; result packet passed.
