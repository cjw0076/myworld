# AIOS Operating Loop

This file standardizes how an acting operator uses AIOS itself while building
AIOS. The loop must leave durable evidence, not only chat summaries.

## Standard Call Sequence

For every meaningful AIOS task:

1. **Sense**
   - Run monitor and goal evolution.
   - Search relevant myworld docs, contracts, ledgers, child repo instructions,
     and current worktrees.
   - Record dirty repo state before dispatching new child work.

2. **Remember**
   - Call MemoryOS for accepted context before planning when history matters.
   - Preferred command:

```bash
python -m memoryos.cli --root . context build --for hive --task "<task>" --json --explain
```

   - Record `trace_id`, selected memory IDs, and feedback directives in the
     contract or receipt.

3. **Route**
   - Call CapabilityOS before choosing tools, providers, or fallback routes.
   - Preferred command:

```bash
python -m capabilityos.cli recommend --task "<task>" --observations-inbox ../.aios/outbox --json
```

   - Record top capability IDs, risk notes, and fallback IDs.

4. **Hive**
   - Use Hive Mind for execution planning or verification surfaces.
   - Preferred dry-run command:

```bash
python -m hivemind.hive ask "<task>" --json
```

   - Record `run_id`, route source, prepared artifacts, and open questions.

5. **Contract**
   - Open or update an ASC contract with exact repos, files, required outputs,
     verification gate, and stop conditions.
   - Include the MemoryOS trace, CapabilityOS route, and Hive run evidence
     when those calls shaped the work.

6. **Dispatch**
   - Use `scripts/aios_dispatch.py` or `scripts/aios_loop.py`.
   - Dispatch must pass the action policy gate before inbox delivery.
   - Every packet should carry allowed files, forbidden files, required reading,
     `must_produce`, verification commands, and result schema.

7. **Watch**
   - Use child watcher `once` before broad `start`.
   - The child prompt must require `semantic_handshake` from
     `docs/AIOS_SHARED_LANGUAGE.md`.
   - Provider access failures should route through CapabilityOS fallback logic.

8. **Collect**
   - Collect result packets before release.
   - Treat failed result packets as AIOS improvement material, not as noise.
   - Do not edit `.aios/state/dispatches.jsonl`; append transitions only.

9. **Verify**
   - Run the contract's narrow gate, then the current full myworld gate when
     the change affects shared control-plane behavior.
   - Run monitor assessment last.

10. **Learn**
   - Update contract receipts, goal evolution, and ledger.
   - If the task exposed friction in AIOS itself, add the next contract to the
     goal preferred-next chain.

## Required Evidence

Each closed AIOS contract should cite:

- MemoryOS `trace_id` or explicit reason MemoryOS was not needed.
- CapabilityOS recommendation ID(s) or explicit reason routing was not needed.
- Hive run ID, dry-run, watcher, or verification receipt.
- Dispatch ID(s), result packet path(s), and release or hold reason.
- Test commands and monitor assessment.
- Next contract candidate.

## Monitoring Rules

- Keep `scripts/aios_round_controller.py status` running unless intentionally
  stopped.
- Check `scripts/aios_monitor.py assess --json` before and after closeout.
- If monitor reports pending results, collect or run watcher before release.
- If monitor reports child repo dirty state, classify it as:
  - expected contract output,
  - generated cache to clean,
  - unrelated parallel-agent work to preserve,
  - or stop condition requiring owner triage.

## Failure Handling

- `provider_access_denied`: use CapabilityOS provider-route fallback once.
- `child_agent_failed`: inspect bounded logs, fix watcher/classifier if the
  failure is infrastructure, or issue a narrower packet if the task was
  ambiguous.
- `semantic_drift_unresolved`: stop and update shared language before
  proceeding.
- `repo_dirty`: do not overwrite; work with existing changes or isolate your
  own staged set.

## Product Direction

The long-term operating form is an on-premises, continuously evolving AIOS
application with a visualization-first control surface. This file is the text
protocol that the future control app should render as workflows, state
transitions, evidence cards, and feedback loops.
