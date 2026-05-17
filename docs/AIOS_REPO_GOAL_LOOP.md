# AIOS Repo Goal Loop

Lower repos can ask the myworld control plane for routed AIOS work by
submitting a repo-goal packet. This is the first executable surface for the
self-resonant repo loop: child repos report goals or friction, myworld returns
a MemoryOS/CapabilityOS/Hive route, and the route becomes a contract candidate.

## Commands

Submit a goal or friction packet:

```bash
python scripts/aios_repo_goal.py submit \
  --repo hivemind \
  --kind friction \
  --goal "child watcher provider fallback was ambiguous" \
  --summary "Need a routed packet with MemoryOS, CapabilityOS, and Hive evidence" \
  --evidence-ref "docs/AGENT_WORKLOG.md" \
  --json
```

Create a route packet from the latest pending goal:

```bash
python scripts/aios_repo_goal.py route --repo hivemind --json
```

Inspect counts:

```bash
python scripts/aios_repo_goal.py status --repo all --json
```

Process all repo-goal packets into reviewable outcomes:

```bash
python scripts/aios_goal_inbox_processor.py --json
python scripts/aios_goal_inbox_processor.py report --json
```

## Files

Runtime packets stay under `.aios/` and are not committed:

```text
.aios/goal_inbox/<repo>/rg_*.json
.aios/goal_routes/<repo>/route_*.json
.aios/primitives/goal_inbox_run/gir_*.json
.aios/primitives/goal_inbox_run/index.json
.aios/capability_gaps/rg_*.json
```

## Goal Packet

`submit` writes `aios.repo_goal.v1`:

- `goal_id`
- `source_repo`
- `kind`: `goal`, `friction`, `blocker`, `improvement`, or `observation`
- `goal`
- `summary`
- `evidence_refs`
- `priority`
- `status: pending_route`

Submissions must not include secrets, raw exports, `.env` paths, or absolute
private evidence paths.

## Route Packet

`route` writes `aios.repo_goal_route.v1`:

- MemoryOS task and required context
- CapabilityOS task, recommended route IDs, and risk notes
- Hive task, execution owner, and verification hint
- stop conditions
- recommended contract slug
- next action

The route is recommendation-only. It does not dispatch, execute, accept memory,
bind tools, or edit child repos.

## Processor Stage

`scripts/aios_goal_inbox_processor.py` is the bridge from "child repo spoke"
to "operator can act." It reads every packet under `.aios/goal_inbox/<repo>/`
without deleting or modifying the packet, classifies it, and writes one
processing receipt under `.aios/primitives/goal_inbox_run/`.

Classifications:

- `auto_promote_distinct`: the packet maps to an AIOS capability theme and
  becomes its own `status: proposed` contract candidate in `docs/contracts/`.
  The generated contract body cites the originating packet so the citizen
  voice is not collapsed into a generic theme.
- `merge_with_justification`: the packet is explicitly merged with an existing
  contract only when a merge target and justification are recorded.
- `needs_operator_review`: the packet is valid but ambiguous and becomes a
  triage note under `docs/operator_queue/`.
- `reject_out_of_scope`: the packet is malformed or references forbidden
  secret/raw/private surfaces and becomes a rejection note under
  `docs/operator_queue/`.
- `defer_capability_gap`: the packet needs CapabilityOS route/card review
  before promotion and becomes a local `.aios/capability_gaps/` record.

The processor is idempotent. It stores processed goal ids in
`.aios/primitives/goal_inbox_run/index.json`; repeated runs preserve each
packet's explicit response while still writing a fresh receipt. Receipts report
`silently_skipped: 0`; silent skip is not a valid response.

## Operating Rule

When a lower repo hits AIOS-relevant friction, it should submit a repo-goal
packet instead of asking the human operator to relay context manually. myworld
then uses the standard operating loop: MemoryOS context, CapabilityOS route,
Hive plan, smart contract, dispatch, watcher, collect, verify, learn.
