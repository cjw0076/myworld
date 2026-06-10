---
contract_id: ASC-0164
slug: genesisos-child-watcher-surface
status: closed
goal: Make GenesisOS visible to the AIOS child watcher and monitor surfaces so GenesisOS implementation packets can actually run.
created: 2026-05-14 12:30 KST
accepted: 2026-05-14 12:30 KST
closed: 2026-05-14 12:36 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: ASC-0163 identified GenesisOS recombination implementation as next child-repo work; control-plane inspection showed dispatch supports GenesisOS but child watcher and monitor loops still omit it.
---

# ASC-0164 GenesisOS Child Watcher Surface

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 6 (operator override remains
possible).

## Plain Language

GenesisOS already has an inbox, but the always-on watcher and monitor were not
fully looking at it. In other words, AIOS could write a letter to GenesisOS but
could not reliably wake it or see its operating status.

## Assumptions

- The correct fix is MyWorld control-plane plumbing, not GenesisOS source code.
- A dispatch surface is incomplete unless create, send, watcher status,
  watcher execution, result collection, and monitor visibility all agree on
  the same repo set.
- Generated Python cache files should not block GenesisOS work like real dirty
  source changes.

## Distant-Domain Analogy

Treat GenesisOS like a city district that already has a street address but is
missing from bus routes and emergency maps. ASC-0164 adds it to the route map;
it does not redesign the buildings inside the district.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `scripts/aios_monitor.py`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_monitor.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0164-genesisos-child-watcher-surface.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `GenesisOS/**`
- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## AIOS Role Evidence

### MemoryOS

- context_pack: not_required_for_control_surface_fix
- retrieval_trace: not_required
- accepted_memory_ids: not_required
- draft_memory_policy: no memory acceptance in this contract

### CapabilityOS

- route: `capabilityos.provider_route.v1` already used by child watcher
  fallback; this contract preserves that surface for GenesisOS packets.
- recommended_tools: child watcher, monitor snapshot, focused tests
- fallback_plan: if provider auth/backpressure occurs, child watcher continues
  using existing CapabilityOS fallback route logic.
- authority: recommendation_only

### GenesisOS

- branch_set: ASC-0163 requires future GenesisOS recombination candidates.
- semantic_alignment_notes: GenesisOS cannot act as the Philosophy persona if
  it has a dispatch inbox but no watcher/monitor lifecycle.
- founder_signal: GenesisOS is the OS that feels discomfort; creative
  inventions come from discomfort becoming named need and testable
  recombination candidate.
- authority: advisory_only; this contract changes only MyWorld surfaces.

### Hive Mind

- execution_plan: codex@myworld fixes watcher/monitor enumerations and tests.
- provider_route: codex_cli
- verification_receipt: pending
- degraded_or_fallback_receipt: not_required

## myworld.must_produce

- Add GenesisOS to `scripts/aios_child_watcher.sh` supported repo paths,
  status loop, start-all loop, stop-all loop, usage text, and watcher execution
  path.
- Add GenesisOS to `scripts/aios_monitor.py` monitored child repo list.
- Add focused tests proving a GenesisOS packet can be consumed by the child
  watcher and that monitor snapshots include GenesisOS.
- Update dispatch docs so operator commands list GenesisOS child watcher usage.

## Out Of Scope

- Implementing GenesisOS recombination candidates.
- Implementing MemoryOS negative memories.
- Implementing CapabilityOS bad-tool observations.
- Implementing Hive richer failure receipts.

Those become child-repo contracts after this control-plane surface is closed.

## Verification Gate

```bash
bash -n scripts/aios_child_watcher.sh
python -m py_compile scripts/aios_monitor.py
python -m unittest tests/test_aios_child_watcher.py tests/test_aios_monitor.py
bash scripts/aios_child_watcher.sh status
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- `scripts/aios_child_watcher.sh status` prints a GenesisOS row.
- `scripts/aios_child_watcher.sh once --repo GenesisOS` is supported and can
  write a result packet in the focused test.
- `scripts/aios_monitor.py snapshot --json` includes GenesisOS in `repos`.
- Existing hivemind, memoryOS, and CapabilityOS watcher behavior is unchanged.
- No child repo source files are modified.

## Stop Conditions

- `genesisos_source_modified`
- `existing_child_repo_watcher_regression`
- `monitor_repo_false_positive`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0164.myworld.result.json`
- monitor closeout: `health=watch`, `watched.repos=4`, `watched.alerts=1`
  after collection. The remaining counted alert is
  `generated_cache_present` for GenesisOS Python cache files; it is low
  severity and outside this contract's permitted write scope.

## Work Packets

### WP-0164-A — codex@myworld adds GenesisOS watcher and monitor support

- target_agent: codex
- target_repo: myworld
- status: closed
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14 12:36 KST
- depends_on: ASC-0163
- brief: |
    Add GenesisOS to MyWorld child watcher and monitor repo loops so future
    GenesisOS implementation packets can run through AIOS. Do not edit
    GenesisOS source under this contract. Verify with focused watcher/monitor
    tests and monitor assessment.
- result: passed. GenesisOS is now visible in child watcher status, accepted by
    watcher execution tests, and included in monitor repo snapshots. No
    GenesisOS source files were modified.
