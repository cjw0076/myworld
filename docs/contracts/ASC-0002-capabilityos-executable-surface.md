---
contract_id: ASC-0002
slug: capabilityos-executable-surface
status: accepted
goal: Create the first recommendation-only CapabilityOS package and CLI surface.
created: 2026-05-11 KST
accepted: 2026-05-11 KST
closed: pending
supersedes: none
---

# ASC-0002 CapabilityOS Executable Surface

> Operator pre-accepted this stub at the index level (README.md `accepted` row).
> The body sections below are stubs — WP-0002-A dispatches body authoring to
> `codex@CapabilityOS`. Acceptance here means: "yes, dispatch Codex to fill
> this in," not "the contract body is finalized." Codex must still answer
> Q1–Q5 and surface a `## Counter-Proposal` if the stub goal is wrong.

## Control Plane Position

This contract stub is issued by `claude@myworld` as control plane. It is `proposed`. Body sections (Scope, Per-OS Responsibility, Verification Gate, Stop Conditions) are stubs — WP-0002-A dispatches the drafting work to `codex@CapabilityOS` (with hivemind read-only). The control plane does not fill the body itself.

## Goal

CapabilityOS is currently 0% code. Hivemind has a `memory_bridge.py` pattern that shows how an OS hook can be optional and non-blocking. ASC-0002 establishes the analogous surface for CapabilityOS:

1. CapabilityOS exposes a callable contract surface (CLI or Python entrypoint) that takes a task description and returns a recommendation payload.
2. hivemind's route phase can call this surface in the same non-blocking, graceful-degrade pattern as `memory_bridge.py` (continue if absent, record reason).
3. The recommendation payload is **minimal but real** — not a stub that returns nothing; it must contain at least one actionable field (recommended_capability id, fallback id, confidence).

ASC-0002 explicitly does **not** require:
- the full Capability Ontology JSON schema to be finalized
- the MVP Design-to-Code workflow to be implemented
- Surfer/Discriminator architecture
- any data ingestion pipeline

The goal is to make the third leg of the AIOS *real* — even if it returns a hand-curated recommendation list at first — so that ASC-0001-style dogfood loops can include CapabilityOS.

## Open Design Questions

The drafter (codex@CapabilityOS via WP-0002-A) must answer in the contract body:

- **Q1 — Surface shape**: CLI subcommand, Python entrypoint, or both? Recommendation: mirror `memoryos context build --for hive --json` shape (CLI + JSON), and let hivemind add a `capability_bridge.py` analog. Justify if you choose differently.
- **Q2 — Recommendation payload schema**: minimum viable fields. Suggested floor: `recommended_capability` (id + name + reason), `fallback` (id + reason), `confidence` (0..1), `evidence` (list of source refs or empty). Anything richer requires a separate contract.
- **Q3 — Data source for V1**: hand-curated YAML/JSON catalog committed in `CapabilityOS/data/`? Hivemind run history scrape? Hardcoded in code? V1 should be the smallest thing that lets ASC-0002 close.
- **Q4 — Verification gate**: what test in CapabilityOS proves the surface works, and what test in hivemind proves the bridge degrades gracefully when CapabilityOS is absent? Both required.
- **Q5 — Catalog write authority**: does ASC-0002 include any code that writes to the catalog, or is V1 read-only? Recommendation: read-only (write authority is a separate future contract).

## Scope (stub — to be filled by WP-0002-A)

- repos: _to be filled — must include `CapabilityOS`, may include `hivemind` for the bridge analog._
- allowed_files: _to be filled — be specific. CapabilityOS source, hivemind capability_bridge analog, route phase call site, tests on both sides._
- forbidden_files: _to be filled — at minimum: memoryOS/** (out of scope), .runs/**, raw exports, secrets, weights._

## Per-OS Responsibility (stub)

- **capabilityos.must_produce**: _to be filled — CLI/entrypoint, recommendation schema doc, V1 catalog (smallest viable), tests._
- **hive_mind.must_produce**: _to be filled — `capability_bridge.py` analog of `memory_bridge.py`, route phase integration, graceful degrade test._
- **memoryos**: not in scope.
- **operator.must_produce**: acceptance decision; checkpoint if scope creeps toward full ontology.

## Verification Gate (stub)

_to be filled by WP-0002-A — concrete commands for CapabilityOS-side surface test AND hivemind-side bridge test (graceful degrade + happy path)._

## Stop Conditions (stub)

_to be filled by WP-0002-A — at minimum:_
- ontology_scope_creep (full ontology spec demanded by V1)
- mvp_vertical_demand (Design-to-Code implementation demanded by V1)
- hivemind_blocking_dependency (route phase fails when CapabilityOS absent)
- schema_drift_with_existing_memory_bridge (CapabilityOS surface diverges from memory_bridge pattern without justification)
- catalog_write_creep (V1 demands write API)

## Receipts

_filled at closeout._

## Work Packets

### WP-0002-A — Codex drafts ASC-0002 body

- target_agent: codex
- target_repo: CapabilityOS (writes), hivemind (reads only for bridge pattern)
- status: issued
- issued: 2026-05-11
- accepted: pending
- closed: pending
- depends_on: ASC-0001 closed (template precedent)
- brief: |
    Fill the stub sections of ASC-0002 (Scope, Per-OS Responsibility,
    Verification Gate, Stop Conditions) and answer Q1–Q5 in the body.

    Required reading, in order:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
         (Contract File Shape, Work Packets, Lifecycle sections)
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0001-memoryos-hivemind-loop.md
         (template — copy structure, not content)
      4. /home/user/workspaces/jaewon/myworld/hivemind/hivemind/memory_bridge.py
         (the pattern CapabilityOS surface should mirror)
      5. /home/user/workspaces/jaewon/myworld/CapabilityOS/README.md
      6. /home/user/workspaces/jaewon/myworld/CapabilityOS/docs/shared/capabilityOS.md
         (~1850-line ontology vision — extract V1-relevant minimum only;
          do not let full ontology bleed into ASC-0002)

    Constraints:
    - V1 must be the smallest thing that makes the loop dogfoodable like
      ASC-0001. Resist scope creep toward full Surfer/Discriminator or MVP
      vertical.
    - Mirror memory_bridge.py: optional, non-blocking, graceful degrade.
    - Verification gate must include both a CapabilityOS-side test (surface
      works) AND a hivemind-side test (degrades gracefully without
      CapabilityOS). Cite exact pytest names or CLI commands.
    - Recommendation payload schema must be minimal (Q2 floor) — extensions
      are a future contract.

    If a stronger contract topic surfaces during reading (e.g. Capability
    Ontology schema must come first), do not silently swap. Add a
    `## Counter-Proposal` section and stop; operator decides.

    After drafting:
    - Update this packet status `issued` → `done`, fill `closed`, fill
      `result` with commit SHA.
    - Issue WP-0002-B inline: target_agent claude, target_repo myworld,
      brief = "review filled ASC-0002 for V1 minimality, bridge pattern
      fidelity, gate concreteness, ontology-bleed prevention, and Q1–Q5
      answer completeness".
    - Do NOT append to docs/AIOS_AGENT_LEDGER.md until ASC-0002 is closed
      (per AIOS_AGENT_LEDGER convention: stable decision points only).

- result: pending
