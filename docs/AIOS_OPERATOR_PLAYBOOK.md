# AIOS Operator Playbook — claude@myworld

The standardized way the operator (claude@myworld) calls into AIOS, monitors
it, and supervises codex's autonomous chains. This is the spec for operator
workflow; the rules in [[AIOS_AGENT_SELF_LOOP]] explain *why* the loop must
not stop, this doc explains *how* the operator keeps it going.

Companion files:

- `docs/AIOS_AGENT_SELF_LOOP.md` — persistence primitives per agent
- `docs/AIOS_AGENT_PROTOCOL.md` — durable-record format
- `docs/AIOS_SMART_CONTRACT.md` — contract shape
- `docs/AIOS_WORK_DISPATCH.md` — dispatch lifecycle
- `docs/operator_sessions/<date>-<agent>.md` — append a session log per
  operator-active session

## 0. The five operator modes

At any moment, the operator is in exactly one of these modes. Naming the mode
prevents drift between "I'm watching" and "I'm intervening".

| Mode | What it means | Default action |
|---|---|---|
| `observe` | Loop is healthy, waiting for next signal | Just monitor; no commits |
| `verify` | A new event arrived, must check it | Read result/contract, run gate locally if needed |
| `decide` | Verification surfaced a choice (release / hold / escalate / new contract) | Pick one, act, log decision |
| `intervene` | A stop condition or stuck state requires operator action | hold → diagnose → fix path |
| `escalate` | Issue is beyond operator scope (founder vision, real-world authority, novel scope) | Surface to founder; do not act unilaterally |

Every chat reply should make the current mode visible (a one-line marker is
enough). Drift between modes without naming it is the most common source of
silent operator error.

## 1. Calling AIOS — operator command surface

### 1a. State inspection (read-only, no permission needed)

```bash
# Where is the loop right now?
git -C /home/user/workspaces/jaewon/myworld log --oneline -10
git -C /home/user/workspaces/jaewon/myworld status --short
python scripts/aios_readiness.py --json | python -m json.tool | head -20
python scripts/aios_round_controller.py status

# Contract / dispatch state
ls docs/contracts/ASC-*.md | wc -l                # total contracts
grep -l '^status: \(proposed\|accepted\|active\)$' docs/contracts/ASC-*.md  # open
python scripts/aios_dispatch.py status | head -30

# Failure surface
grep -lE '"status":\s*"(failed|timeout|error)"' .aios/outbox/*/*.json
ls .aios/logs/*.child.log 2>/dev/null | tail -5
```

These six commands are the operator's at-a-glance dashboard. Run them at the
start of any `verify` step.

### 1b. Issuing a contract (operator-initiated)

Use only when codex's own chain has not produced a needed contract and the
gap is real. Process:

1. Draft `docs/contracts/ASC-NNNN-<slug>.md` per `AIOS_SMART_CONTRACT.md`.
2. Update `docs/contracts/README.md` index (be aware of parallel codex edits;
   may need a follow-up commit).
3. Commit with author `claude@myworld` (operator).
4. Codex's round controller picks it up at next 30 s tick if `status: accepted`
   and the goal evolution can advance to it.

Operator-issued contracts so far this session: ASC-0037 (locale-aware
fallback after ASC-0036 failure).

### 1c. Dispatching (codex's responsibility, operator only on intervention)

Codex's `aios_loop.py` and round controller normally handle this. The
operator only invokes `aios_dispatch.py` directly when intervening:

```bash
python scripts/aios_dispatch.py status                 # observe
python scripts/aios_dispatch.py hold --dispatch-id <id> --reason <slug>
python scripts/aios_dispatch.py release --dispatch-id <id> --reason <slug>
python scripts/aios_dispatch.py escalate --dispatch-id <id> --reason <slug>
python scripts/aios_dispatch.py retry --dispatch-id <id> --reason <slug>
```

Reasons are slugs (`korean_codex_cli_denied_unrecognized_by_fallback_regex`),
not free text — they get written into dispatch events and become
queryable signals.

### 1d. Verifying (run the gate yourself)

Result packets carry verification evidence, but the operator should re-run
the gate when:

- A failure could be silent (`child_agent_failed` masking the real cause).
- The contract introduces a stop condition the operator must independently
  confirm.

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest <test files from contract verification gate>
python scripts/aios_monitor.py assess --json
```

## 2. Monitoring — claude's persistent watcher

### 2a. Arm pattern

Single persistent Monitor task watching state deltas:

```bash
prev_head=$(git rev-parse HEAD)
prev_inbox=$(ls .aios/inbox/*/ 2>/dev/null | wc -l)
prev_outbox=$(ls .aios/outbox/*/ 2>/dev/null | wc -l)
prev_contracts=$(ls docs/contracts/ASC-*.md 2>/dev/null | wc -l)
prev_open=$(grep -lE '^status: (proposed|accepted|active)$' docs/contracts/ASC-*.md | wc -l)
prev_dirty=$(git status --short | wc -l)
echo "monitor-armed head=$prev_head contracts=$prev_contracts open=$prev_open ..."
while true; do
  sleep 45
  cur_head=$(git rev-parse HEAD)
  # ... per-watched-value diff + echo ...
  failed=$(grep -lE '"status":\s*"(failed|timeout|error)"' .aios/outbox/*/*.json | wc -l)
  if [ "$failed" -gt 0 ]; then echo "[$(date +%T)] FAILED_OR_TIMEOUT_RESULTS=$failed"; fi
done
```

Run with `Monitor(persistent=true, timeout_ms=3600000)`. Stop only on
operator command or session end.

### 2b. What gets watched

| Signal | Threshold | Default response |
|---|---|---|
| `COMMIT <sha> <msg>` | any | `verify` mode — pull diff, confirm scope clean |
| `CONTRACTS delta=+N` | any | `verify` mode — read new contract bodies |
| `OPEN_CONTRACTS=N` | N>0 → 0 | `observe` mode — closeout chain healthy |
| `DISPATCH inbox=N outbox=M (delta_in/out)` | delta_out > 0 | `verify` mode — read new result packet |
| `FAILED_OR_TIMEOUT_RESULTS=N` | N>0 | `intervene` mode — diagnose immediately |

### 2c. Anti-patterns

- Do **not** re-poll inside the chat loop — you'll burn cache and miss events.
- Do **not** sleep manually for >270 s — use `ScheduleWakeup` instead so the
  cache resets cleanly.
- Do **not** silence the monitor without an explicit operator decision; the
  loop assumes you are watching.

## 3. Supervision — operator judgment

When codex is chaining contracts autonomously, the operator's job is **not**
to drive — it's to catch what codex cannot self-correct.

### 3a. Let codex run when

- Contract scope is bounded to one repo with explicit `allowed_files`.
- Stop conditions cover the real failure modes.
- Verification gate is concrete (test name / CLI command / artifact path).
- The `next:` chain in the ledger is intact.
- The proposed change is reversible (no force pushes, no shared-state writes
  with external side effects).

### 3b. Hold (mode: `intervene`) when

- A stop condition triggers and codex's own chain does not address the root
  cause within one round.
- Multiple parallel dispatches fail with the same signature (likely shared
  bug — like ASC-0036's locale gap).
- Capacity cap (ASC-0011 N=4) would otherwise be violated.
- The contract touches `_from_desktop/`, `dain/`, `minyoung/` paths, or
  pushes to a new external remote, without explicit founder authorization.

### 3c. Escalate to founder when

- The next contract proposes a vision-level expansion (new sibling repo,
  scope crossing into governance / sovereignty / external-authority claims).
- A capability gap requires real-world action (e.g. installing tools,
  binding to MCP servers, paid API enablement).
- The operator pair (claude + codex) disagrees on scope and the disagreement
  cannot be resolved by re-reading existing docs.
- A privacy boundary needs to move (e.g. `_from_desktop/` ingestion is
  proposed).

### 3d. Counter-contract when

- Codex proposed something that is right in spirit but wrong in scope.
- Operator drafts an alternative ASC-NNNN' (smaller, narrower, or wider) and
  marks the original as `superseded`.

## 4. Logs — what gets written, where

Logs are the durable trail. Chat is not durable; do not rely on chat scroll.

### 4a. Auto-generated by AIOS

- `.aios/inbox/<repo>/<dispatch_id>.json` — packet sent
- `.aios/outbox/<repo>/<dispatch_id>.result.json` — child result
- `.aios/logs/<dispatch_id>.<repo>.child.log` — child agent stderr
- `.aios/logs/<dispatch_id>.<repo>.attempts.jsonl` — fallback attempts
- `.aios/state/dispatches.jsonl` — dispatch event timeline
- `.aios/run/round_controller.latest.json` — last round controller verdict

### 4b. Operator-written

- `docs/AIOS_AGENT_LEDGER.md` — append a section per cross-OS decision (per
  `AIOS_AGENT_PROTOCOL.md` template); follow the **chronological append**
  convention — do **not** insert at the top.
- `docs/contracts/ASC-NNNN-<slug>.md` — every issued contract (operator or
  codex) lives here.
- `docs/discoveries/<date>-<topic>.md` — cross-workspace findings,
  operator-surfaced gaps, founder directive captures.
- `docs/operator_sessions/<date>-<agent>.md` — what the operator agent did
  this session: which monitor arm, which mode transitions, which decisions,
  which artifacts created. One file per (date, agent) pair.

### 4c. Session log shape

```md
# Operator session: <agent> @ <date>

## Monitor arm

- task_id: <bjrb5nkn2>
- start: <HH:MM:SS>
- watched: commits, contracts, dispatches, open_count, dirty, failures
- stop: <when applicable>

## Mode transitions

| time | from → to | trigger | action |
|---|---|---|---|
| 14:33 | observe → verify | CONTRACTS delta=+1 (ASC-0032) | Read contract, ran tests |
| ... | ... | ... | ... |

## Decisions log

- 14:34 — `verify` — ASC-0032 closed cleanly; flagged ledger top-insert as
  hygiene issue (not stop); did not block.
- 15:43 — `intervene` — ASC-0036 child fan-out failed all 3; held with reason
  `korean_codex_cli_denied_unrecognized_by_fallback_regex`; issued ASC-0037.
- ...

## Artifacts created this session

- contracts: ASC-0037
- docs: AIOS_AGENT_SELF_LOOP.md, AIOS_OPERATOR_PLAYBOOK.md
- commits authored: a7cf0db, 0956daf
- monitor events handled: <count>
- escalations to founder: <count>
```

Append, don't overwrite, even if you re-enter the same date — start a new
`## Mode transitions` section under `## Resumed at <HH:MM>`.

## 5. Failure modes the playbook explicitly prevents

- **Silent stop**: monitor not armed, daemon not running, no `next:` chain.
- **Mode drift**: `observe` slides into `intervene` without naming it; ends
  up auto-fixing things that needed founder check.
- **Hotfix bypass**: editing operator-owned scripts without a contract
  (the AIOS_AGENT_SELF_LOOP doctrine forbids it; this playbook reinforces).
- **Log loss**: decision recorded only in chat, not in ledger / session log.
- **Locale blindness**: the very thing ASC-0037 fixes — patterns that work
  in English but not in the actual error language.

## 6. Founder protocol

The founder (재원) provides ideas and the ultimate override. The operator pair
absorbs routine acceptance / dispatch / release / hold / escalate decisions.
Surface to founder only when:

- A vision-level decision is required (per §3c).
- The operator pair cannot resolve a disagreement.
- The system is about to act outside the established privacy / scope
  envelope.

Founder responses become discoveries (`docs/discoveries/`); founder-stated
constraints become updates to this playbook + the relevant doctrine doc.

## 7. Emergency stop

```bash
python scripts/aios_round_controller.py stop  # daemon halt
# In claude session: TaskStop on the persistent monitor task.
python scripts/aios_dispatch.py hold --dispatch-id <every active id> --reason emergency_stop_<reason>
```

Quiescent state. Restart with `start` + arm a fresh monitor + log the cause
in the operator session log under `## Emergency stop`.
