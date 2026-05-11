---
contract_id: ASC-0005
slug: hive-capability-bridge
status: accepted
goal: Add hivemind/hivemind/capability_bridge.py mirroring memory_bridge.py — calls CapabilityOS recommend during the route phase, optional and non-blocking.
created: 2026-05-11 KST
accepted: 2026-05-11 KST
closed: pending
supersedes: none
acceptance_authority: claude@myworld (operator) per founder directive 2026-05-11 KST delegating routine acceptance.
origin: counter-proposal section of ASC-0002 (codex@CapabilityOS proposed the split; the original ASC-0003 reference there is replaced by this ASC-0005 because ASC-0003 was already taken by dispatch-packet-enrichment).
---

# ASC-0005 Hive Capability Bridge

## Control Plane Position

Issued and accepted by `claude@myworld` (operator) on 2026-05-11 KST. The body is a stub — WP-0005-A dispatches body authoring + implementation to `codex@hivemind`. Acceptance here is a routine operator decision: the scope is clean (hivemind only), the precedent exists (`memory_bridge.py`), the upstream surface exists (ASC-0002 closed), and the founder did not name this as escalation territory.

## Goal

ASC-0002 closed with a working CapabilityOS V1 CLI that returns ranked recommendations. Hivemind currently has no caller. Mirror the existing `memory_bridge.py` pattern so hivemind's route phase can ask CapabilityOS "what tool/route/fallback should I prefer for this task" without becoming dependent on CapabilityOS being installed or running.

ASC-0005 explicitly does **not**:
- modify CapabilityOS package or schema (that surface is closed in ASC-0002)
- modify memoryOS
- introduce execution authority (CapabilityOS V1 is recommendation-only; bridge surfaces recommendation, hivemind decides whether to act on it)
- bundle the dispatch packet enrichment work (that is ASC-0003)
- bundle watcher/state machine (that is ASC-0004)

## Open Design Questions

The drafter (codex@hivemind via WP-0005-A) must answer in the contract body:

- **Q1 — Bridge file location and surface**: Recommendation: `hivemind/hivemind/capability_bridge.py` to match `memory_bridge.py` location. Public functions `recommend_for(task: str) -> CapabilityRecommendation | None` and `bridge_status() -> Literal["unavailable", "ok", "failed"]`. Justify if you choose differently.
- **Q2 — Route phase integration point**: where in `harness.py` (or wherever the route phase lives now) does the bridge get called? Recommendation: same orchestration point that calls `memory_bridge`. The two bridges are siblings; their results both feed the deliberate phase.
- **Q3 — Env var / discovery convention**: `memory_bridge.py` uses `HIVE_MEMORYOS_SOURCE_ROOT`. Recommendation: `HIVE_CAPABILITYOS_SOURCE_ROOT` analogously, pointing to the CapabilityOS repo root containing the catalog fixture. Justify if you instead use a CLI in PATH or a different mechanism.
- **Q4 — Graceful degrade contract**: when CapabilityOS is missing/broken/empty catalog, what does `bridge_status()` return and what does the orchestrator log? Mirror the memory_bridge degrade pattern exactly unless there is a reason to diverge — document the reason if you do.
- **Q5 — Verification gate**: BOTH a happy-path test (CapabilityOS available → recommendation surfaces in run_state) AND a degrade test (CapabilityOS absent → run continues, run_state records `capability_recommendation: null` with reason). Cite exact pytest names.

## Scope (stub — to be filled by WP-0005-A)

- repos: _to be filled — must be exactly `[hivemind]`. CapabilityOS is a read-only dependency, not in implementation scope (its surface was finalized by ASC-0002)._
- allowed_files: _to be filled — at minimum:_
  - `hivemind/hivemind/capability_bridge.py` (new)
  - `hivemind/hivemind/harness.py` (route phase call site)
  - `hivemind/hivemind/run_validation.py` (if run_state schema gains a capability field)
  - `hivemind/tests/test_capability_bridge.py` (new)
  - `hivemind/tests/test_quickstart.py` (degrade-mode integration)
- forbidden_files: _to be filled — at minimum:_
  - `CapabilityOS/**` (surface owned by ASC-0002, closed)
  - `memoryOS/**`
  - `hivemind/.runs/**`, `hivemind/.ai-runs/**`
  - secrets, weights, raw exports

## Per-OS Responsibility (stub)

- **hive_mind.must_produce**: capability_bridge module, route phase integration, run_state field for capability recommendation, two tests (happy + degrade), updated `hivemind/CLAUDE.md` invariants if behavior changes.
- **capabilityos**: not in implementation scope. Read-only consumer of the V1 surface from ASC-0002.
- **memoryos**: not in scope.
- **operator.must_produce**: acceptance (done — claude@myworld), closeout review, dispatch via aios_dispatch when body is filled.

## Verification Gate (stub)

_to be filled by WP-0005-A. Recommended target:_

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_capability_bridge.py -v
python -m pytest tests/test_quickstart.py -v
# Smoke happy path:
HIVE_CAPABILITYOS_SOURCE_ROOT=/home/user/workspaces/jaewon/myworld/CapabilityOS python -m hivemind.hive demo memory-loop --json
# Smoke degrade path:
unset HIVE_CAPABILITYOS_SOURCE_ROOT && python -m hivemind.hive demo memory-loop --json
```

Expected evidence:
- happy path: run_state contains a `capability_recommendation` object with at least `recommended_capability`, `score`, and `evidence_refs` populated by CapabilityOS.
- degrade path: run executes; run_state records `capability_recommendation: null` with `bridge_status: "unavailable"` and a non-error reason; no exception, no test failure.
- Both pytest sets pass.

## Stop Conditions (stub)

_to be filled by WP-0005-A — at minimum:_
- `capability_executes`: bridge calls any CapabilityOS surface that executes tools (V1 must remain recommendation-only).
- `hivemind_blocking`: route phase fails or blocks when CapabilityOS is absent (must degrade gracefully).
- `capabilityos_source_edit`: ASC-0005 modifies any file under `CapabilityOS/`.
- `memoryos_creep`: ASC-0005 touches memoryOS.
- `ontology_demand`: implementation requires the full Capability Ontology to be loaded.
- `schema_drift_with_memory_bridge`: bridge surface diverges from memory_bridge pattern without justification documented in Q4.

## Receipts

_filled at closeout._

## Work Packets

### WP-0005-A — Codex drafts ASC-0005 body and implements

- target_agent: codex
- target_repo: hivemind
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: ASC-0002 closed (CapabilityOS V1 surface available)
- brief: |
    This packet does TWO things in sequence:
    (1) Fill the stub sections of ASC-0005 (Scope, Per-OS Responsibility,
        Verification Gate, Stop Conditions) and answer Q1–Q5.
    (2) Implement `hivemind/hivemind/capability_bridge.py` mirroring the
        existing `memory_bridge.py` pattern, integrate at the route phase,
        and add the two tests (happy + degrade).

    Required reading, in order:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0002-capabilityos-executable-surface.md
         (the closed CapabilityOS V1 surface — your dependency)
      4. /home/user/workspaces/jaewon/myworld/hivemind/hivemind/memory_bridge.py
         (the pattern to mirror — same shape, same graceful degrade)
      5. /home/user/workspaces/jaewon/myworld/hivemind/hivemind/harness.py
         (find the route phase call site for memory_bridge, integrate
         capability_bridge symmetrically)
      6. /home/user/workspaces/jaewon/myworld/CapabilityOS/capabilityos/cli.py
         (the surface you will call — read to understand the JSON contract)
      7. /home/user/workspaces/jaewon/myworld/CapabilityOS/tests/fixtures/capabilities.json
         (the V1 catalog shape)

    Constraints:
    - Mirror memory_bridge.py exactly unless Q4 justifies divergence.
    - Optional and non-blocking. Hivemind must run end-to-end with no
      CapabilityOS source root configured.
    - V1 is recommendation-only: bridge must NOT call any CapabilityOS
      surface that executes tools (CapabilityOS V1 has no such surface;
      this stop condition is a future-proof guardrail).
    - Do NOT touch CapabilityOS source. The V1 surface is closed.
    - Coordinate with ASC-0003 (packet enrichment): if ASC-0003 lands
      first, the bridge can rely on enriched packets carrying capability
      metadata; if ASC-0005 lands first, accept that ASC-0003 may need
      to learn the bridge's run_state field.

    If a stronger design surfaces (e.g. CapabilityOS V1 schema is
    insufficient and needs ASC-0006 first), add a `## Counter-Proposal`
    section and stop. Operator (claude+codex@myworld) decides.

    After drafting + implementing:
    - Update WP-0005-A status `issued` → `done`, fill `closed`, fill
      `result` with commit SHA.
    - Issue WP-0005-B inline: target_agent claude, target_repo myworld,
      brief = "review filled ASC-0005 + implementation: bridge pattern
      fidelity to memory_bridge, degrade safety, no CapabilityOS source
      modification, Q1–Q5 answer completeness, no scope creep into
      ontology or execution authority".
    - Do NOT append to AIOS_AGENT_LEDGER.md until ASC-0005 is closed.

- result: pending
