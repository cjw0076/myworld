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

## Files

Runtime packets stay under `.aios/` and are not committed:

```text
.aios/goal_inbox/<repo>/rg_*.json
.aios/goal_routes/<repo>/route_*.json
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

## Operating Rule

When a lower repo hits AIOS-relevant friction, it should submit a repo-goal
packet instead of asking the human operator to relay context manually. myworld
then uses the standard operating loop: MemoryOS context, CapabilityOS route,
Hive plan, smart contract, dispatch, watcher, collect, verify, learn.
