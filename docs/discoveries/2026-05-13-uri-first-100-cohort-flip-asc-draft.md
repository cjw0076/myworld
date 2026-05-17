# Uri First-100 Cohort Graduation Flip — ASC Draft — 2026-05-13

Founder-lane authored by `claude@uri` per founder elevation iter 41 (2026-05-13). Draft surface for operator pair (claude@uri + codex@myworld) to convert into a numbered ASC. References `myworld/docs/contracts/ASC-0035-policy-gated-dispatch.md` (closed 2026-05-12) + `uri/capabilities/asc-0035-self-ingest-dispatch-alignment-2026-05-13.md` (iter 25).

## Why this discovery

URI-017 Sprint 015 packet (iter 34) listed ASC-0035 first-100 cohort flip as a `chair pickup dependency`. Founder-lane elevation iter 41 authorizes claude@uri to draft the ASC. codex@myworld assigns the next ASC number (estimated ASC-0085+, after ASC-0084 Hive AIOS DNA debate close) and creates the contract file under `myworld/docs/contracts/`.

## ASC scope (paste-ready into contract file)

```
# ASC-NNNN Uri First-100 Cohort Graduation Flip

- status: proposed
- created: 2026-05-13 KST
- proposed by: claude@uri (founder lane proxy per iter 41 elevation)
- scope: myworld + uri
- depends_on: ASC-0035 policy-gated dispatch (closed); URI-017 Sprint 015 (in chair queue)
```

## Goal

Define the trigger conditions and procedure for flipping ASC-0035 action-policy classification of `uri_self_ingest_page_sync_*` actions from `escalate` (first-100-students audit window) to `allow` (post-graduation routine).

Without this flip, every routine Notion page sync after the first-100 students would still emit an `escalate` evidence packet to the operator pair — unsustainable signal volume.

## Trigger conditions (all 5 required)

1. **Sprint 015 (URI-017) shipped** — Notion OAuth real connector live.
2. **First 100 students by chronological `signup_at`** have completed initial ingest activity (≥1 Notion page synced, no Korean PIPA incidents).
3. **4-week audit window** after Sprint 015 ship with provider-loop receipts inspected by operator pair (claude@uri + codex@myworld).
4. **PIPA lawyer review** of Item 5 (제3자 제공 금지) + Item 6 (3rd-party info in pages) closed with **no further restrictions** on `uri_self_ingest_page_sync_*`.
5. **Zero `escalate` events** fired for volume anomaly (`≥10 new pages` per single sync) at any unexpected user, OR investigation closed cleanly for each fired event.

If any condition fails, cohort stays in `escalate` mode. Next operator pair retry after the failing condition addressed.

## Procedure

When all 5 trigger conditions met:

1. Operator pair updates `myworld/scripts/aios_action_policy.py` rules:
   - `uri_self_ingest_page_sync_manual` matcher: `escalate` → `allow`
   - `uri_self_ingest_page_sync_scheduled` matcher: `escalate` → `allow`
2. Volume anomaly (`uri_self_ingest_volume_anomaly` ≥10 pages) **stays `escalate` permanently** — separate operator-checkpoint trigger (never flipped).
3. Full-account-delete **stays `escalate` permanently** — audit-forever requirement.
4. OAuth callback + per-page revoke remain `allow` (already allowed per ASC-0035 alignment iter 25; no change needed).
5. Operator pair runs `python scripts/aios_action_policy.py evaluate --example uri_self_ingest_page_sync_manual --json` and verifies `decision=allow`.
6. Operator pair appends ledger entry to `myworld/docs/AIOS_AGENT_LEDGER.md` + this ASC closeout.

## Stop conditions

- Cohort flip executed without all 5 trigger conditions met.
- Volume anomaly threshold relaxed below 10 pages without separate ASC.
- Full account delete classification downgraded from `escalate` (would lose audit trail).
- Per-page revoke classification changed (must remain `allow` per PIPA 철회권).
- PIPA Item 5 / Item 6 lawyer findings reopen restrictions on routine sync.
- 4-week audit window shortened without separate operator-pair decision.

## Verification (per-flip)

- `python scripts/aios_action_policy.py evaluate --example uri_self_ingest_page_sync_manual --json` returns `{"decision": "allow", "reason": "uri_first_100_cohort_graduated"}` (post-flip).
- `python scripts/aios_action_policy.py evaluate --example uri_self_ingest_volume_anomaly --json` returns `{"decision": "escalate"}` (unchanged).
- `python scripts/aios_action_policy.py evaluate --example uri_self_ingest_delete_account --json` returns `{"decision": "escalate"}` (unchanged).
- Audit log file written: `myworld/.aios/audit/uri-self-ingest-cohort-flip-<YYYYMMDD>.json` with trigger evidence:
  - Sprint 015 ship date + URI-017 receipt path
  - First-100 cohort completion date + signup_at range
  - 4-week audit window start/end + receipts inspected count
  - PIPA lawyer review document path + sign-off date
  - Volume anomaly events count + investigation outcomes
- ASC closeout includes pointer to audit log + ledger entry.

## Carry into Sprint 016+

- Post-flip, Sprint 016 (URI-018) account-backed sync inherits `allow` classification for routine `uri_cloud_sync_put/get` per same cohort-graduation pattern.
- Future self-ingest sources (LMS / 공부 파일 / 공식 학교 URL) get their own cohort-flip ASCs as they ship (Sprint 016c+).
- Pattern reusable: every new external connector starts in `escalate` for first-100, graduates via similar ASC.

## Operator pair next action

1. **codex@myworld**: assign next ASC number (estimated 0085+ after ASC-0084); create `myworld/docs/contracts/ASC-NNNN-uri-first-100-cohort-flip.md` using the scope/goal/triggers above; mark status `accepted`.
2. **claude@uri**: maintain trigger condition watch — when Sprint 015 ships + 4-week audit window starts, surface progress to this discovery's update section.
3. **Founder**: PIPA 변호사 retainer (parallel to Sprint 015 chair pickup per iter-33 fork Option B).

## Lane separation reaffirmation

- claude@uri = ASC draft authorship (founder lane elevation iter 41) + trigger watch + audit log surface.
- codex@myworld = ASC number assignment + contract file creation + `aios_action_policy.py` rule update at flip time.
- Founder = PIPA lawyer retain decision + pilot Round 1 launch ops.
