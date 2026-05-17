---
contract_id: ASC-0078
slug: aios-work-visibility-layer
status: closed
goal: Make AIOS work inspectable while it runs by exposing contracts, active packets, command summaries, changed files, receipts, and next actions through one redacted work-view surface.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder observation that AIOS hides the actual work content from the operator.
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: founder/operator approval in chat
origin: founder said "AIOS를 쓰면 작업 내용을 볼 수가 없구나" after contract execution moved into AIOS artifacts.
depends_on:
  - ASC-0076 contract-closeout-reconciliation
---

# ASC-0078 AIOS Work Visibility Layer

## Why Now

AIOS has contracts, dispatch packets, result packets, ledgers, monitor
assessments, and local runtime state. That is enough for machines, but not
enough for an operator who wants to understand the work as it happens.

If the user cannot see the work, AIOS becomes another opaque agent wrapper.
The control plane needs a first-class work view: what is active, what changed,
what commands ran, what evidence exists, what is blocked, and what happens
next.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_work_view.py`
- `tests/test_aios_work_view.py`
- `docs/AIOS_WORK_VISIBILITY.md`
- `docs/contracts/ASC-0078-aios-work-visibility-layer.md`
- `docs/contracts/README.md`
- `docs/AIOS_CONTRACT_EXECUTION_ORDER.md`
- `docs/AIOS_AGENT_LEDGER.md`

read_only_sources:

- `docs/contracts/*.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `.aios/state/dispatches.jsonl`
- `.aios/outbox/**/*.json`
- `.aios/inbox/**/*.json`
- `.aios/state/monitor_assessment.latest.json`
- `git status --short`

forbidden_files:

- raw provider stdout/stderr bodies
- private transcripts
- raw exports
- `.env`
- `.env.*`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- child repo source edits
- network access
- provider execution

## Work View V1

Commands:

```bash
python scripts/aios_work_view.py status --json
python scripts/aios_work_view.py status
python scripts/aios_work_view.py contract ASC-0067 --json
python scripts/aios_work_view.py tail --limit 20
```

The V1 view must show:

- active accepted contracts with empty `closed`.
- held/retry/escalated dispatches.
- latest result packets per repo.
- changed files grouped by likely contract when possible.
- latest monitor health.
- current recommended next action.
- redacted command/evidence summaries, never raw private output.

Schema:

- `aios.work_view.v1`

Required top-level fields:

- `generated_at`
- `root`
- `health`
- `active_contracts`
- `dispatch_summary`
- `latest_results`
- `changed_files`
- `blocked`
- `next_actions`

## Verification Gate

```bash
python -m py_compile scripts/aios_work_view.py
python -m unittest tests/test_aios_work_view.py
python scripts/aios_work_view.py status --json
python scripts/aios_work_view.py contract ASC-0067 --json
python scripts/aios_work_view.py tail --limit 5
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `status --json` includes accepted/unclosed contracts.
- held dispatches are visible as blocked work.
- latest outbox result packets are summarized by path and status.
- changed files are listed without reading private/raw contents.
- hard-ban files are never opened.
- command evidence is summarized by command name/status only.
- missing runtime files degrade gracefully.
- monitor health remains clear or is surfaced as blocked.

## Stop Conditions

- `private_file_read`
- `raw_provider_output_exposed`
- `secret_path_exposed`
- `child_repo_source_modified`
- `work_view_claims_completion_without_closed_contract`
- `blocked_dispatch_hidden`
- `verification_gate_failed`

## Work Packets

### WP-0078-A — codex@myworld implements work visibility CLI

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: ASC-0076 classification matrix
- brief: |
    Implement a read-only work visibility CLI and tests. It must make current
    AIOS work understandable without exposing secrets or raw provider output.
- return_to: `.aios/outbox/myworld/asc-0078.myworld.result.json`
- result: pending

### WP-0078-B — claude@myworld reviews operator UX semantics

- target_agent: claude
- target_repo: myworld
- status: proposed
- depends_on: WP-0078-A
- brief: |
    Review whether the work view tells a human what is happening, what changed,
    what is blocked, and what comes next without requiring knowledge of AIOS
    internals.
- return_to: `.aios/outbox/myworld/asc-0078.claude-review.result.json`
- result: pending
