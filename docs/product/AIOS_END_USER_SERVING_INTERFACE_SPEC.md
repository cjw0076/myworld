# AIOS End-User Serving Interface Spec

**Contract**: ASC-0251  
**Status**: draft  
**Date**: 2026-06-13  

---

## 1. Product Boundary

The end-user serving interface is a **separate product entry point** from the
operator Control Center (`apps/control/`). The Control Center is a cockpit for
operators. The serving interface is a cabin for users: they do not need to see
the cockpit, they need a seat, a service button, a clear itinerary, and a way
to inspect what happened to their belongings.

| Concern | Control Center (operator) | Serving Interface (user) |
|---|---|---|
| Primary user | Operator / developer | End user |
| Visibility | Full AIOS control plane | One task stream |
| Contract visibility | All contracts | None (job progress only) |
| Provider internals | Exposed | Hidden |
| Memory scope | All accepted memory | Own memories only |
| Action authority | Full operator authority | Delegated per-task authority |
| Runtime profile | `build_control` / `live_agent_runtime` | `end_user_serving` (new label) |

---

## 2. User Roles

### 2.1 End User

- Creates tasks.
- Monitors job progress.
- Approves or rejects sensitive actions.
- Inspects, exports, or deletes their own memories.
- Downloads or rejects artifacts produced for them.
- Does not see: provider logs, raw contracts, operator state, other users' data.

### 2.2 Operator / Admin

- Manages workspace settings and user accounts.
- Reviews job audit trails without crossing user privacy boundaries.
- Pauses or cancels jobs on behalf of users.
- Configures rate/cost limits, provider routes, and consent gates.
- Can see: operator-visible ledger summaries, runtime events (no user content).

### 2.3 Support Reviewer

- Responds to user-reported issues.
- Can view job timelines and error summaries for a specific user-granted session.
- Cannot access provider logs, contract bodies, or other users' memories.
- Evidence: only what a support-visible receipt contains (stage names, status
  codes, error type — not raw message bodies or tool outputs).

### 2.4 Agent Worker

- Executes tasks on behalf of a user.
- Acts under the authority scope of the user's task, not the operator.
- Cannot persist memory without a draft/review cycle.
- Produces signed receipts for every action (provider call, file write,
  external request).

---

## 3. User-Facing Routes

### 3.1 Task Inbox (`/tasks`)

- Lists all tasks for the current user.
- Each entry: task title, status badge (queued / running / needs approval /
  done / failed), created time, last activity.
- Actions: New Task, Re-run Failed, Archive.

### 3.2 Active Job / Session (`/tasks/:id`)

- Full timeline of stages for one job.
- Each stage: name, status, started/ended times, output summary (not raw body).
- Paused stages show the approval widget.
- Completed stages show artifact download/reject button.
- Sensitive action items surface inline: "AIOS wants to send an email — approve?"

### 3.3 Memory Viewer and Controls (`/memory`)

- Lists accepted memories tagged to the user.
- Each memory: label, date accepted, provenance chain (what task produced it).
- Actions: Export, Request Deletion, Inspect Draft Lifecycle.
- Draft memories appear in a separate "pending review" section.
- User can reject a draft before acceptance.

### 3.4 Artifact Review (`/artifacts`)

- Lists produced artifacts: files, reports, summaries, exports.
- Each artifact: name, producing job, date, size, format tag.
- Actions: Download, Reject (removes from user-visible store), Inspect Provenance.

### 3.5 Approval Queue (`/approvals`)

- Surfaces all pending approval gates that need user action.
- Ordered by urgency (unblocking a running job = top).
- Each gate: what AIOS wants to do, which task it belongs to, risk label,
  Approve / Reject / Ask for Clarification.

### 3.6 Account / Workspace Settings (`/settings`)

- Display name, email, notification preferences.
- Connected providers (which AIOS is allowed to call on their behalf).
- Active consent grants and per-provider rate limits.
- Export all my data / Delete my account.

---

## 4. Runtime Profile: `end_user_serving`

The existing `runtime_profile_state` in `aios_dispatch.py` defines two modes:
`build_control` and `live_agent_runtime`. The serving interface needs a third
label that sits between them.

```
build_control          — operator context; live child execution blocked by default
live_agent_runtime     — full AIOS agent pulse/loop; live child execution allowed
end_user_serving       — user-delegated execution scope; per-user sandbox required
```

`end_user_serving` constraints:
- Live child execution is allowed **only within a user-scoped workspace**.
- No provider call may bypass the approval queue if the action is marked
  `requires_user_approval`.
- Every result packet must include a `user_id` and `session_id` field.
- Memory writes require a draft/review cycle before acceptance; no silent write.
- File access is sandboxed to a per-user workspace; no cross-user path access.

The `end_user_serving` label is a future `RUNTIME_PROFILES` addition to
`aios_dispatch.py`. It is not implemented in this contract; this spec defines
its semantics so the implementation contract has an unambiguous target.

### 4.1 How a User Task Becomes an AIOS Work Packet

```
User submits task form
  → Serving API validates input (rate limit, consent gates)
  → Creates aios.user_task.v1 packet with user_id, session_id, task_body
  → Dispatched to Hive under end_user_serving profile
  → Hive executes with user-scoped authority
  → Each stage emits an aios.stage_receipt.v1
  → Approval gates surface to /approvals if flagged
  → Final artifact emitted to /artifacts
  → Memory drafts emitted to MemoryOS (draft state only)
  → Job timeline written to user_id task store
```

### 4.2 How a Job Resumes After Interruption

- Each stage is checkpointed via `aios_run_log` with a `call_id`.
- On resume, the harness replays completed stages from the log (no re-execution).
- The serving API keeps a job state machine: `queued → running → paused →
  resuming → complete | failed`.
- Resume is triggered by:
  - User approval of a pending gate.
  - Operator un-pause.
  - System retry after transient provider error.

---

## 5. Memory Boundary

### 5.1 Per-User Memories

- MemoryOS stores accepted memories tagged with `user_id`.
- No memory from user A is accessible from user B's task context.
- Operator memories and system memories are in separate namespaces.

### 5.2 Visible Provenance

- Each memory on `/memory` shows:
  - Which task produced it (job ID, task title).
  - Which stage wrote it (stage name, receipt ID).
  - Date proposed → date accepted.
  - Who approved it (user self-accept, or operator-review flag).

### 5.3 Draft / Review / Accepted Lifecycle

```
agent writes memory draft
  → draft appears in user's "pending review" section at /memory
  → user sees label + source + proposed content (no raw body if sensitive)
  → user accepts (→ accepted) or rejects (→ rejected, never stored)
  → operator-review flag can force a second review step
```

Auto-accept is prohibited under `end_user_serving`. The user must see a draft
before it becomes accepted.

### 5.4 Export / Delete Request Path

1. User clicks "Export all my data" at `/settings`.
2. Serving API creates an `aios.export_request.v1` packet.
3. MemoryOS and artifact store package all user-scoped records into a signed
   zip (no operator-private fields).
4. Export link appears at `/artifacts` within a configurable SLA window.
5. "Delete my account" triggers `aios.deletion_request.v1`, which:
   - Marks all user memories as `deleted` (append-only — not physically
     removed, per DNA invariant #3).
   - Removes user from account store.
   - Revokes all consent grants.
   - Emits a final signed deletion receipt.

---

## 6. Serving Readiness Gates

Before the serving interface is open to real users, the following gates must
pass. These are not implemented in this contract; they define what a future
implementation contract must prove.

| Gate | What must be true |
|---|---|
| Session isolation | Two users cannot see each other's jobs, memories, or artifacts |
| File/workspace isolation | User file writes are sandboxed; no `../` traversal across user boundaries |
| Action approvals | Any action tagged `requires_user_approval` blocks until approved |
| Observability | Every stage emits a receipt; operator can audit without reading user content |
| Rate / cost controls | Per-user daily token budget enforced before task dispatch |
| Incident / support flow | Support can view job timeline summary for a specific incident_id without accessing raw memory bodies |

---

## 7. UI Proof Target (Without Building It Here)

A future prototype contract must demonstrate:

1. **New Task Flow**: User types a task title + description → task appears in
   `/tasks` with status `queued` → status transitions to `running` → at least
   one stage receipt appears in the timeline.

2. **Approval Gate Flow**: A running job requests a sensitive action → an item
   appears in `/approvals` → user approves → job resumes → stage marked
   `complete`.

3. **Memory Draft Review**: After job completes, a draft memory appears in
   `/memory` → user accepts → memory transitions to `accepted` state.

4. **Artifact Download**: After job completes, an artifact appears in
   `/artifacts` → user clicks download → file downloads → artifact is marked
   `reviewed`.

The prototype must verify these four flows with browser-visible UI before the
serving interface is considered product-ready. Mock data is acceptable for the
prototype; the serving API backend is out of scope for the prototype contract.

---

## 8. MyWorld Control-Plane Mapping

### 8.1 User Actions as AIOS Records

| User action | AIOS record type |
|---|---|
| Submit task | `aios.user_task.v1` dispatch packet |
| Approve gate | `aios.approval_receipt.v1` attached to ContractObject |
| Accept memory draft | `memoryos.draft_accept.v1` in MemoryOS |
| Reject memory draft | `memoryos.draft_reject.v1` in MemoryOS |
| Download artifact | `aios.artifact_access_log.v1` in serving log |
| Request deletion | `aios.deletion_request.v1` in ledger |

### 8.2 What the End User Must Never See

- Raw contract bodies (`docs/contracts/ASC-*.md`).
- Provider log lines (`stdout`/`stderr` of tool calls).
- Other users' job timelines or memories.
- Operator-only dispatch state (`.aios/inbox/`, `.aios/leases/`).
- Runtime profile raw files (`.aios/runtime_profile.json`).
- Raw `aios_dispatch.py status` output.

### 8.3 Support / Admin Evidence Boundary

Support reviewers access:
- Job timeline (stage names + status + error type — not message bodies).
- Approval queue history for a specific incident (approved/rejected + timestamp).
- Memory draft lifecycle (proposed/accepted/rejected — not memory body unless
  user-scented only via a secure redaction gate).

Support reviewers may **not** access:
- Raw memory bodies without explicit user consent grant.
- Operator system memories.
- Provider credentials or account material.

---

## 9. Acceptance Gates for a Future UI Build Contract

A follow-on UI build contract (`apps/serving/`) must satisfy:

1. **Route list**: All six routes from §3 are implemented and reachable.
2. **Mock data schema**: Each route accepts a `?mock=true` flag that returns
   deterministic fixture data.
3. **First workflow state machine**: The new-task state machine (§4.1) is
   implemented as a client-side state machine with at least six states.
4. **Accessibility**: All interactive elements have ARIA labels; keyboard
   navigation completes the new-task flow without a mouse.
5. **Responsive check**: Layout is usable at 375px width (mobile) and 1280px
   width (desktop).
6. **Browser verification**: The four UI proof flows from §7 pass in a
   headless browser test.

These gates are *not* satisfied by the Control Center. The serving interface
must be a separate origin or path prefix.

---

## 10. Open Questions (Not Blocking This Contract)

1. Authentication: OAuth2/OIDC, API keys, or AIOS-native session tokens?
2. Multi-tenant hosting: shared cluster or per-user isolated runtime?
3. Serving API transport: REST, SSE, WebSocket, or MCP?
4. Rate limiting: global token budget, per-provider, or per-task?
5. Audit retention: how long are user job timelines retained?

These questions are deferred to the first implementation contract.
