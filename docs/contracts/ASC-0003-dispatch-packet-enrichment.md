---
contract_id: ASC-0003
slug: dispatch-packet-enrichment
status: closed
goal: Enrich aios_dispatch.py JSON packets so child agents do not have to re-derive their task slice from the contract body.
created: 2026-05-11 KST
accepted: 2026-05-11 22:20 KST by codex acting operator
closed: 2026-05-11 22:20 KST
supersedes: none
---

# ASC-0003 Dispatch Packet Enrichment

## Control Plane Position

This contract was issued by `claude@myworld` after the ASC-0001 dogfood pass
surfaced concrete friction in the dispatch packet shape. It was accepted and
closed by `codex@myworld` under delegated acting-operator authority.

## Goal

The current `aios.dispatch.v1` packet (built by `scripts/aios_dispatch.py`) carries the contract's `goal`, `scope`, and a generic `required_reading` list — but **not** the per-OS `must_produce` items, the verification commands, or any per-repo tailoring of required reading. This forced `claude@myworld` to re-derive the task slice for both verification gates during the ASC-0001 dogfood run.

ASC-0003 enriches the packet so that a child agent receiving it has everything needed to act, without re-reading the entire contract body.

ASC-0003 does **not** include:
- a watcher/executor that reads packets and runs them automatically (separate future contract; the biggest gap from dogfood findings)
- changes to the dispatch model (create/send/collect/stop semantics stay)
- changes to the contract file shape itself

## Open Design Questions

The drafter (codex@myworld via WP-0003-A) must answer in the contract body:

- **Q1 — Per-OS responsibility extraction**: how does the parser locate each repo's `must_produce` block in the contract? Recommendation: parse `## Per-OS Responsibility` (or the legacy `## Responsibilities`) section and split by `### <Repo>` subheadings; fall back to `extract_bullet_list` style if a `must_produce:` bullet block is present. Justify the rule and add a regression test for both ASC-0001's `### Hive Mind` style and ASC-0002's stub style.
- **Q2 — Verification command extraction**: how does the parser pull commands from `## Verification Gate`? Recommendation: extract every fenced code block tagged `bash` under that section, in order, and emit them as `verification_commands[]`. Skip "Operational smoke equivalent" subsections unless explicitly asked.
- **Q3 — Schema versioning**: keep `aios.dispatch.v1` with new optional fields (backward compatible) or bump to `aios.dispatch.v2` (clean break)? Recommendation: keep v1 + add optional fields. Bump only if a field becomes required.
- **Q4 — Per-repo `required_reading` tailoring**: should each repo get only the docs relevant to its slice (e.g. memoryOS doesn't need `AIOS_WORK_DISPATCH.md` repeated)? Recommendation: keep a small "AIOS frame" base list (NORTHSTAR, AGENT_PROTOCOL, SMART_CONTRACT, the contract file) and append per-repo extras from a contract-level `required_reading_by_repo:` block if present, otherwise empty.
- **Q5 — Result packet schema**: define `aios.dispatch.result.v1` (target_repo, dispatch_id, contract_id, status, executed_at, agent_assigned, agent_executed, executed_reason, evidence, stop_conditions_triggered) so `collect` can validate result packets instead of accepting any JSON. Reject malformed results with a clear error.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_loop.py`
- `tests/test_aios_dispatch.py`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0003-dispatch-packet-enrichment.md`
- `docs/contracts/README.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `.runs/**`
- `raw_exports/**`
- `weights/**`
- `.env`
- `.env.*`

## Design Answers

### Q1 — Per-OS responsibility extraction

The parser supports both contract shapes currently in the tree:

- legacy `## Responsibilities` with `### <Repo>` subheadings and a
  `must_produce:` bullet block, used by ASC-0001;
- compact `## Per-OS Responsibility` bullets such as
  `**capabilityos.must_produce**: ...`, used by ASC-0002.

Repo names are matched through aliases (`Hive Mind`, `hive_mind`, `memoryOS`,
`CapabilityOS`) so packets are not tied to one spelling.

### Q2 — Verification command extraction

Packets include `verification_commands[]` extracted from fenced `bash` blocks
under `## Verification Gate`, selected by the command's preceding `cd` path for
the target repo. `Operational smoke equivalent` blocks are excluded. The
watcher still performs its own safe-command checks before execution.

### Q3 — Schema versioning

The packet remains `aios.dispatch.v1`. New fields are optional:
`result_schema_version`, `must_produce`, `verification_commands`, and
`result_contract`. No existing field was renamed or removed.

### Q4 — Per-repo required reading

V1 keeps the small AIOS frame list plus the contract path. The new
`must_produce` and `verification_commands` fields carry the repo-specific slice
without bloating `required_reading`.

### Q5 — Result packet schema

`collect` now validates packets that declare
`schema_version: aios.dispatch.result.v1`. Required fields are:
`target_repo`, `dispatch_id`, `contract_id`, `status`, `evidence`, and
`stop_conditions_triggered`. Malformed v1 packets are rejected with a clear
error instead of silently collected.

## Per-OS Responsibility

- **myworld (control plane).must_produce**: enriched packet with Q1/Q2/Q4
  fields, result packet schema validation (Q5), updated dispatch docs,
  regression tests covering ASC-0001-style responsibility extraction and
  malformed result rejection.
- **hive_mind, memoryos, capabilityos**: not in scope.
- **operator.must_produce**: accepted and closed by delegated acting operator;
  checkpoint if scope creeps to watcher/executor.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py
python scripts/aios_dispatch.py create docs/contracts/ASC-0001-memoryos-hivemind-loop.md --force --dispatch-id asc-0001-replay
python scripts/aios_dispatch.py send --repo memoryOS --agent codex --dispatch-id asc-0001-replay --force
python scripts/aios_dispatch.py watch --repo memoryOS --once --dispatch-id asc-0001-replay
```

Expected evidence:

- unit tests pass;
- the replay MemoryOS packet contains `must_produce`,
  `verification_commands`, `result_schema_version`, and `result_contract`;
- replay verification result is collected and released.

## Stop Conditions

- breaking_change_without_version_bump (any field rename/removal must bump schema_version)
- contract_parser_overfits_to_one_contract (parser must work for ASC-0001 AND ASC-0002 stub shape)
- watcher_executor_scope_creep (auto-running packets is a separate contract)
- packet_size_explosion (per-repo packet should stay under ~10KB; if larger, reduce or use refs)
- privacy_leak_via_packet (no raw transcript content, secrets, or local-only paths in packet)

## Receipts

Closed 2026-05-11 22:20 KST by `codex@myworld` acting operator.

- Implemented optional packet enrichment in `scripts/aios_dispatch.py`.
- Mirrored enrichment in `scripts/aios_loop.py` so automatic dispatch packets
  are not weaker than manual packets.
- Updated `scripts/aios_child_watcher.sh` result packets to declare
  `aios.dispatch.result.v1`.
- Updated `docs/AIOS_WORK_DISPATCH.md`.
- Verification:
  - `python -m py_compile scripts/aios_dispatch.py scripts/aios_loop.py scripts/aios_monitor.py` passed.
  - `python -m unittest tests/test_aios_dispatch.py tests/test_aios_loop.py tests/test_aios_monitor.py` -> 12 tests OK.
  - `bash -n scripts/aios_child_watcher.sh scripts/aios_pingpong.sh` passed.
  - ASC-0001 enriched MemoryOS replay created packet
    `.aios/inbox/memoryOS/asc-0001-enriched-replay.memoryOS.json` with
    `must_produce_count=73`, one MemoryOS verification command, and
    `result_schema_version=aios.dispatch.result.v1`.
  - Replay watcher result passed, collected, and released as dispatch
    `asc-0001-enriched-replay`.
- Stop conditions triggered: none.

## Work Packets

### WP-0003-A — Codex drafts ASC-0003 body and implements

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-11
- accepted: 2026-05-11 22:20 KST
- closed: 2026-05-11 22:20 KST
- depends_on: ASC-0001 closed (pattern precedent), operator acceptance of ASC-0003
- brief: |
    This packet does TWO things in sequence:
    (1) Fill the stub sections of ASC-0003 (Scope, Per-OS Responsibility,
        Verification Gate, Stop Conditions) and answer Q1–Q5.
    (2) Implement the agreed enrichment in scripts/aios_dispatch.py with
        regression tests in tests/test_aios_dispatch.py.

    Required reading, in order:
      1. /home/user/workspaces/jaewon/myworld/docs/AIOS_SMART_CONTRACT.md
      2. /home/user/workspaces/jaewon/myworld/docs/contracts/README.md
      3. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0001-memoryos-hivemind-loop.md
         (the contract whose dispatch this is enriching)
      4. /home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0002-capabilityos-executable-surface.md
         (stub — parser must handle this shape too)
      5. /home/user/workspaces/jaewon/myworld/scripts/aios_dispatch.py
         (the file being modified)
      6. /home/user/workspaces/jaewon/myworld/tests/test_aios_dispatch.py
         (the test surface to extend)
      7. /home/user/workspaces/jaewon/myworld/.aios/inbox/memoryOS/asc-0001.memoryOS.json
         (the v1 packet shape — what's missing)
      8. /home/user/workspaces/jaewon/myworld/.aios/outbox/memoryOS/asc-0001.memoryOS.result.json
         (the ad-hoc result packet shape that needs schematizing)

    Constraints:
    - Keep `aios.dispatch.v1` (per Q3 recommendation) — add optional fields,
      do not break consumers. Bump only if a field becomes REQUIRED.
    - Parser must handle BOTH ASC-0001 (`## Responsibilities` + `### Hive Mind`
      headings) AND ASC-0002 (stub form `## Per-OS Responsibility` +
      `**capabilityos.must_produce**:` bullets). Add fixtures for both.
    - Do not add a watcher or auto-executor. That is a separate future
      contract (largest gap from ASC-0001 dogfood findings).
    - The verification gate must include a golden fixture comparison so
      future packet shape drift is caught immediately.
    - If a stronger design surfaces (e.g. richer schema warrants a clean v2),
      add a `## Counter-Proposal` section and stop; operator decides.

    After drafting + implementing:
    - Update WP-0003-A status `issued` → `done`, fill `closed`, `result`
      with commit SHA(s).
    - Issue WP-0003-B inline: target_agent claude, target_repo myworld,
      brief = "review filled ASC-0003 + implementation: parser correctness
      across ASC-0001 and ASC-0002 shapes, schema-version discipline,
      Q1–Q5 answer completeness, no scope creep into watcher/executor".
    - Run the full ASC-0001 dispatch replay as part of verification. Confirm
      the enriched packet for memoryOS now contains the K57 K43.2 must_produce
      list AND the pytest verification command.
    - Do NOT append to AIOS_AGENT_LEDGER.md until ASC-0003 is closed.

- result: implemented and verified; see Receipts.
