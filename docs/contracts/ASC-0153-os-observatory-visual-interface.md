---
contract_id: ASC-0153
slug: os-observatory-visual-interface
status: closed
goal: Show MemoryOS, CapabilityOS, GenesisOS, Hive Mind, and MyWorld operating activity as visual OS surfaces in the Control Center instead of raw logs.
created: 2026-05-14T03:27:27+09:00
accepted: 2026-05-14T03:27:27+09:00
closed: 2026-05-14T03:29:55+09:00
---

# ASC-0153 OS Observatory Visual Interface

## Why

The founder asked how much knowledge exists inside MemoryOS and how AIOS can
show MemoryOS visual knowledge, CapabilityOS searching/routing, GenesisOS
worldlines, Hive execution, and MyWorld control as operating-system activity
rather than plain logs.

GenesisOS divergence for this work recommended an `alien_domain` frame: treat
AIOS visibility like city infrastructure and zoning, where system districts,
routes, memory stores, and failure boundaries should be legible at a glance.

## Scope

- repos: `myworld`
- allowed_files:
  - `scripts/aios_control_snapshot.py`
  - `apps/control/index.html`
  - `apps/control/app.js`
  - `apps/control/styles.css`
  - `tests/test_aios_control_snapshot.py`
  - `tests/test_aios_local_app.py`
  - `docs/contracts/ASC-0153-os-observatory-visual-interface.md`
  - `docs/contracts/README.md`
  - `docs/AGENT_WORKLOG.md`
  - `docs/AIOS_AGENT_LEDGER.md`
- read_only_sources:
  - `memoryOS/memory/processed/nodes.jsonl`
  - `memoryOS/ontology/edges.jsonl`
  - `memoryOS/memory/objects.jsonl`
  - `memoryOS/memory/reviews.jsonl`
  - `memoryOS/memory/retrieval_traces.jsonl`
  - `memoryOS/ontology/hyperedges.jsonl`
  - `memoryOS/memory/sources.jsonl`
  - `CapabilityOS/capabilityos/cli.py`
  - `GenesisOS/genesisos/cli.py`
- forbidden_files:
  - `memoryOS/memory/raw_exports/**`
  - `memoryOS/private/**`
  - `CapabilityOS/.env`
  - `GenesisOS/.env`
  - provider auth files, PIN stores, raw private provider logs
  - child repo implementation files outside the read-only sources above

## Responsibilities

### myworld.must_produce

- `os_observatory` in `aios.control_snapshot.v1`.
- A Control Center section with:
  - MemoryOS knowledge graph counts.
  - CapabilityOS route/search planner counts and top routes.
  - GenesisOS branch/worldline visibility.
  - Hive latest invocation/dispatch status.
  - MyWorld monitor/contract/dispatch status.
- Browser data refreshed into:
  - `apps/control/aios-control-snapshot.json`
  - `apps/control/aios-control-data.js`

### memoryos.must_produce

- Existing append-only memory evidence only. This contract reads but does not
  modify MemoryOS.
- Review ledger overlay must be honored, so accepted/rejected counts use
  `memoryOS/memory/reviews.jsonl` over base object status.

### capabilityos.must_produce

- Recommendation-only evidence via:
  - `python -m capabilityos.cli list --json`
  - `python -m capabilityos.cli recommend --task ... --observations-inbox ../.aios/outbox --json`
- No tool execution from the UI.

### genesisos.must_produce

- Advisory frame only: worldline/divergence signals explain how to visualize
  AIOS as an operating system.
- GenesisOS does not select final UI truth.

### hive_mind.must_produce

- Existing invocation/dispatch evidence is surfaced. Hive does not execute new
  child work under this contract.

## Verification Gate

The contract is complete only if all commands pass:

```bash
python -m py_compile scripts/aios_control_snapshot.py
python scripts/aios_control_snapshot.py --check-app-js apps/control/app.js --json
python -m unittest tests/test_aios_control_snapshot.py tests/test_aios_local_app.py
python scripts/aios_local_app.py refresh --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Additional visual evidence is captured manually with Firefox headless and
recorded as `.aios/screenshots/aios-control-os-observatory.png`; the watcher
gate does not execute browser binaries.

## Stop Conditions

- `memory_review_overlay_missing`: accepted/rejected counts are calculated from
  `objects.jsonl` only and ignore `reviews.jsonl`.
- `raw_private_memory_read`: UI snapshot reads raw exports or private provider
  histories.
- `capability_executes_tool_from_ui`: CapabilityOS recommendation data causes
  tool execution instead of route display.
- `genesis_claim_promoted`: speculative GenesisOS branch is shown as final
  truth.
- `os_observatory_missing_from_snapshot`: refreshed snapshot lacks
  `os_observatory`.
- `visual_surface_regresses_to_log_dump`: UI renders raw JSON/log text instead
  of OS-level cards/lanes/metrics.
- `browser_visual_evidence_missing`: screenshot is not produced for the
  changed surface.

## Receipts

- MemoryOS observed counts at implementation time:
  - nodes: `198177`
  - edges: `305712`
  - memory_objects: `169`
  - accepted: `44`
  - draft: `117`
  - rejected: `8`
  - reviews: `52`
  - retrieval_traces: `749`
  - hyperedges: `34`
  - sources: `45`
- CapabilityOS observed counts:
  - capability_cards: `6`
  - observations: `48`
  - gaps: `97`
  - observed_capabilities: `3`
- Visual evidence:
  - `.aios/screenshots/aios-control-os-observatory.png`

## Work Packets

### WP-0153-A — Implement OS Observatory in MyWorld Control Center

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: none
- brief: |
    Add an OS Observatory to the Control Center that visualizes MemoryOS,
    CapabilityOS, GenesisOS, Hive Mind, and MyWorld activity from existing
    receipts and read-only stores. Do not modify child repo internals.
- result: `.aios/outbox/myworld/asc-0153.myworld.result.json`
