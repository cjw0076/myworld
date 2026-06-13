# AIOS Serving Interface Route Map

**Contract**: ASC-0251  
**Status**: draft  
**Date**: 2026-06-13  

This document maps each serving interface route to its data sources, authority
constraints, and AIOS control-plane records.

---

## Route Index

| Route | Path | Primary data source | Auth required | Profile |
|---|---|---|---|---|
| Task Inbox | `/tasks` | `aios.user_task.v1` store | user session | `end_user_serving` |
| Active Job | `/tasks/:id` | job timeline + stage receipts | user session (owner) | `end_user_serving` |
| Memory Viewer | `/memory` | MemoryOS (user-scoped) | user session | `end_user_serving` |
| Artifact Review | `/artifacts` | artifact store (user-scoped) | user session | `end_user_serving` |
| Approval Queue | `/approvals` | approval gate log | user session | `end_user_serving` |
| Account / Settings | `/settings` | account store | user session | `end_user_serving` |
| Admin: Users | `/admin/users` | account store | operator session | `build_control` |
| Admin: Audit | `/admin/audit/:id` | ledger summary (redacted) | operator session | `build_control` |
| Support: Incident | `/support/incident/:id` | job timeline (redacted) | support session | `build_control` |

---

## Route Details

### GET `/tasks`

**Purpose**: Show the user's task inbox.

**Data shape** (per row):

```json
{
  "task_id": "utask-abc123",
  "title": "Summarize last week's reports",
  "status": "running",
  "created_at": "2026-06-13T08:00:00Z",
  "last_activity_at": "2026-06-13T08:05:00Z",
  "pending_approvals": 1
}
```

**AIOS source**: `aios.user_task.v1` records filtered to `user_id = session.user_id`.

**Never includes**: raw contract bodies, provider logs, other users' tasks.

---

### GET `/tasks/:id`

**Purpose**: Full timeline view for one job.

**Data shape** (stage row):

```json
{
  "stage_id": "stage-001",
  "name": "Fetch report files",
  "status": "complete",
  "started_at": "2026-06-13T08:01:00Z",
  "ended_at": "2026-06-13T08:02:00Z",
  "output_summary": "Fetched 3 files (PDF, 2× DOCX)",
  "receipt_id": "rcpt-xyz"
}
```

**Approval gate shape**:

```json
{
  "stage_id": "stage-003",
  "name": "Send summary email",
  "status": "needs_approval",
  "action_summary": "AIOS wants to send an email to reports@company.com",
  "risk_label": "external_communication",
  "approval_id": "gate-789"
}
```

**AIOS source**: `aios.stage_receipt.v1` records for the job, plus approval gate
log filtered to `job_id = params.id, user_id = session.user_id`.

**Never includes**: raw stdout/stderr of provider calls, raw memory body, other
users' job data.

---

### GET `/memory`

**Purpose**: View and manage the user's accepted and pending memories.

**Sections**:

1. `pending_review` — drafts awaiting user acceptance.
2. `accepted` — accepted memories (sorted by date, newest first).
3. `rejected` — user-rejected drafts (tombstone records only).

**Memory row shape**:

```json
{
  "memory_id": "mem-001",
  "label": "User prefers weekly digest format",
  "status": "accepted",
  "proposed_at": "2026-06-13T08:02:00Z",
  "accepted_at": "2026-06-13T08:03:00Z",
  "provenance": {
    "job_id": "utask-abc123",
    "stage_id": "stage-002",
    "receipt_id": "rcpt-xyz"
  },
  "body_preview": "User prefers weekly digest…"
}
```

**Actions**:
- Draft: Accept (→ `memoryos.draft_accept.v1`), Reject (→ `memoryos.draft_reject.v1`).
- Accepted: Export, Request Deletion.

**AIOS source**: MemoryOS graph filtered to `user_id = session.user_id`,
`namespace = "user"`.

**Never includes**: system or operator memories; other users' memories.

---

### GET `/artifacts`

**Purpose**: View and download artifacts produced for the user.

**Artifact row shape**:

```json
{
  "artifact_id": "art-001",
  "name": "weekly_digest_2026-06-13.pdf",
  "producing_job_id": "utask-abc123",
  "produced_at": "2026-06-13T08:04:00Z",
  "format": "pdf",
  "size_bytes": 124288,
  "status": "ready"
}
```

**Actions**: Download, Reject (→ removes from user-visible store, records
`aios.artifact_access_log.v1` with `action=rejected`).

**AIOS source**: artifact store filtered to `user_id = session.user_id`.

---

### GET `/approvals`

**Purpose**: Show all pending approval gates in urgency order.

**Approval row shape**:

```json
{
  "approval_id": "gate-789",
  "job_id": "utask-abc123",
  "job_title": "Summarize last week's reports",
  "action_summary": "AIOS wants to send an email to reports@company.com",
  "risk_label": "external_communication",
  "created_at": "2026-06-13T08:03:30Z",
  "blocking_stage": "Send summary email"
}
```

**Actions**: Approve (→ `aios.approval_receipt.v1` + resumes job), Reject
(→ marks gate rejected, job moves to `failed`), Ask for Clarification (→ opens
a text field that creates a `aios.clarification_request.v1`).

**AIOS source**: approval gate log filtered to
`user_id = session.user_id, status = "pending"`.

---

### GET `/settings`

**Purpose**: Account management and consent controls.

**Sections**:

1. **Profile**: display name, email, notification preferences.
2. **Connected Providers**: list of providers AIOS may call on behalf of the
   user (e.g., email, calendar, file storage). Per-provider revoke control.
3. **Consent Grants**: active consent gates, expiry times, scope.
4. **Rate / Cost Limits**: daily token budget, per-provider spend limit.
5. **Data Controls**: Export all my data, Delete my account.

**AIOS source**: account store for `user_id = session.user_id`, consent grant
table, provider connection table.

---

### GET `/admin/users`

**Purpose**: Operator lists and manages user accounts.

**Data shape** (per row):

```json
{
  "user_id": "usr-001",
  "display_name": "Alice",
  "email": "alice@example.com",
  "created_at": "2026-06-01T00:00:00Z",
  "active_jobs": 2,
  "last_activity_at": "2026-06-13T08:00:00Z"
}
```

**Never includes**: user memory body, artifact content, job message bodies.

---

### GET `/admin/audit/:id`

**Purpose**: Operator views a redacted audit trail for a specific job.

**Shape**: job timeline with stage names + status codes + error types. No raw
message bodies, no user memory content.

**Authority**: operator session only. Support reviewers may not use this route;
they use `/support/incident/:id` instead.

---

### GET `/support/incident/:id`

**Purpose**: Support reviewer views a job timeline for a reported incident.

**Shape**: stage names + status + error type + `incident_id`. No raw message
bodies, no memory body, no cross-user data.

**Access requires**: user must have granted a support consent for this incident
(or operator must have issued an override receipt).

---

## Authority Constraint Summary

| Role | Can see | Cannot see |
|---|---|---|
| End User | Own jobs, own memories, own artifacts, own approvals | Other users, operator state, provider logs, raw contracts |
| Operator | All job timelines (redacted), all user account metadata, full audit | Raw memory bodies, user artifact content, provider credentials |
| Support Reviewer | Specific incident timeline (redacted), approval history for incident | Memory bodies (without explicit consent), cross-user data, operator system state |
| Agent Worker | User's task context, user's accepted memories (read) | Cross-user workspaces, operator authority scope |

---

## Prototype Fixture Schema

For browser testing and prototype development, each route must accept
`?mock=true` and return the following fixture structures:

### `/tasks?mock=true`

```json
{
  "tasks": [
    {"task_id": "utask-mock-001", "title": "Mock task 1", "status": "running", "pending_approvals": 1},
    {"task_id": "utask-mock-002", "title": "Mock task 2", "status": "complete", "pending_approvals": 0}
  ]
}
```

### `/tasks/utask-mock-001?mock=true`

```json
{
  "task_id": "utask-mock-001",
  "title": "Mock task 1",
  "stages": [
    {"stage_id": "s1", "name": "Fetch data", "status": "complete"},
    {"stage_id": "s2", "name": "Process", "status": "running"},
    {"stage_id": "s3", "name": "Send email", "status": "needs_approval",
     "approval_id": "gate-mock-001", "action_summary": "AIOS wants to send an email to test@example.com",
     "risk_label": "external_communication"}
  ]
}
```

### `/memory?mock=true`

```json
{
  "pending_review": [
    {"memory_id": "mem-mock-001", "label": "User prefers bullet points", "status": "draft"}
  ],
  "accepted": [
    {"memory_id": "mem-mock-002", "label": "User timezone is Asia/Seoul", "status": "accepted"}
  ]
}
```

### `/approvals?mock=true`

```json
{
  "approvals": [
    {"approval_id": "gate-mock-001", "job_title": "Mock task 1",
     "action_summary": "AIOS wants to send an email to test@example.com",
     "risk_label": "external_communication"}
  ]
}
```

### `/artifacts?mock=true`

```json
{
  "artifacts": [
    {"artifact_id": "art-mock-001", "name": "mock_output.pdf", "format": "pdf",
     "size_bytes": 1024, "status": "ready"}
  ]
}
```

---

*This route map is a design artifact. No backend implementation is included in
ASC-0251. A follow-on prototype contract will build the `apps/serving/` entry
using this spec as its target.*
