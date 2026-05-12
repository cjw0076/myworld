# AIOS Smart Contracts

This directory holds AIOS smart contracts — the machine-checkable work agreements that bind Hive Mind, MemoryOS, CapabilityOS, and the operator on a specific goal.

Read these first:

- `../AIOS_SMART_CONTRACT.md` — minimal contract shape and invariants
- `../AIOS_AGENT_PROTOCOL.md` — durable record format
- `../WORKSTREAMS.md` — Codex/Claude lead split and default task flow

## Naming

`ASC-NNNN-<short-slug>.md` — sequential, append-only. Once an ID is assigned, never re-use it. Superseded contracts get a new ID and a `supersedes:` field.

## Contract File Shape

Each contract file should contain at minimum:

1. **Frontmatter / header** — `contract_id`, `status` (proposed | accepted | active | closed | superseded), `goal`, `created`, `accepted` (when operator approves), `closed` (when verification gate passes or contract is cancelled).
2. **Scope** — `repos[]`, `allowed_files[]`, `forbidden_files[]`. Be specific; broad globs are a smell.
3. **Per-OS responsibility** — what `hive_mind`, `memoryos`, `capabilityos`, and `operator` each must produce. Use the `must_produce` lists from `AIOS_SMART_CONTRACT.md`.
4. **Verification gate** — concrete check that decides done vs. not done (test name, CLI command, artifact existence). No verification gate = no contract.
5. **Stop conditions** — explicit triggers that pause for operator checkpoint. Default set in `AIOS_SMART_CONTRACT.md` invariants.
6. **Receipts** — once executed, link to receipts/traces/observations in each OS, not paste them.
7. **Work Packets** — every dispatch issued under this contract. See section below.

## Work Packets

A work packet is a single, durable dispatch from the control plane to one specific agent (e.g. `codex@hivemind`, `codex@memoryOS`, `claude@myworld` for review). Every dispatch lives as an entry in the `## Work Packets` section of the contract that authorized it — never in chat alone.

Packet ID convention: `WP-<contract_number>-<letter>` (e.g. `WP-0001-A`, `WP-0001-B`). Letters are append-only within a contract; do not re-use.

Packet entry shape:

```md
### WP-NNNN-X — <one-line title>

- target_agent: <codex|claude|local-llm|operator>
- target_repo: <hivemind|memoryOS|CapabilityOS|myworld>
- status: issued | accepted | done | rejected | superseded
- issued: <YYYY-MM-DD>
- accepted: <YYYY-MM-DD or pending>
- closed: <YYYY-MM-DD or pending>
- depends_on: <other WP id, or none>
- brief: |
    <self-contained instruction. Assume target agent has not seen any chat
    context. Cite file paths for required reading. State what artifact the
    agent must produce and where.>
- result: <link to artifact / receipt / trace once closed>
```

Status transitions:
- `issued` → `accepted`: target agent acknowledges and begins.
- `accepted` → `done`: target agent posts the result link.
- `issued` or `accepted` → `rejected`: target agent declines with reason in `result`.
- any → `superseded`: a new packet replaces this one; new packet's `depends_on` field cites this packet's id.

Packets are append-only. Edits limited to status/accepted/closed/result fields. Brief content does not change after `issued`.

## Lifecycle

```
proposed   -> Claude or Codex drafts, posts for review
accepted   -> operator (재원) approves; status flips
active     -> Codex begins implementation under contract scope
closed     -> verification gate passes; receipts linked; ledger entry appended
superseded -> a newer contract replaces; this one becomes read-only reference
```

A `closed` contract gets a final entry in `../AIOS_AGENT_LEDGER.md` linking to its receipts.

## Operator Acceptance

Default acceptance is a frontmatter status flip in the contract file:

1. Operator approves the proposed contract.
2. Contract `status` changes from `proposed` to `accepted`.
3. `accepted` is filled with the approval timestamp.
4. The accepted snapshot is committed in git.

Do not write proposal-time ledger entries. Write one ledger entry only when the
accepted snapshot or closeout is ready, so the ledger records a stable contract
decision rather than draft churn.

## Index

| ID | Slug | Status | Goal |
| --- | --- | --- | --- |
| ASC-0001 | memoryos-hivemind-loop | closed | Codify the existing MemoryOS <-> Hive Mind memory loop as a gated cross-OS contract. |
| ASC-0002 | capabilityos-executable-surface | closed | Create the first recommendation-only CapabilityOS package and CLI surface. |
| ASC-0003 | dispatch-packet-enrichment | closed | Enrich aios_dispatch.py JSON packets so child agents do not have to re-derive their task slice from the contract body. |
| ASC-0004 | dispatch-watcher-and-state-machine | closed | Add release/hold/retry/escalate state machine to aios_dispatch and a V1 watcher that auto-runs verification gates from inbox packets. |
| ASC-0005 | hive-capability-bridge | closed | Add hivemind/hivemind/capability_bridge.py mirroring memory_bridge.py — calls CapabilityOS recommend during route phase, optional and non-blocking. |
| ASC-0006 | aios-l6-repeatable-proof | closed | Add a machine-readable AIOS readiness gate that proves or blocks L6 repeatable completion. |
| ASC-0007 | workspace-doc-scout-task-radar | closed | Add a control-plane doc scout that searches jaewon workspace docs and turns signals into an AIOS task radar and next contract candidates. |
| ASC-0008 | workspace-doc-ingest-memoryos | closed | Turn ASC-0007 doc scout signals into reviewed MemoryOS context records with provenance, without raw export ingestion. |
| ASC-0009 | capability-observation-feedback | closed | Consume task-radar entries and dispatch result packets to record CapabilityOS observations and fallback plans. |
| ASC-0010 | hive-semantic-quality-gate | closed | Add a Hive verification packet that reviews top task-radar candidates for executable next steps before broad dispatch. |
| ASC-0011 | control-plane-loop-policy | closed | Decide which doc-radar candidates become accepted contracts and which remain held through a checkable policy. |
| ASC-0012 | child-repo-durability-closeout | closed | Turn ASC-0008, ASC-0009, and ASC-0010 child-repo working-tree implementations into repo-local durable commits or explicit holds. |
| ASC-0013 | workspace-instruction-index | closed | Index AGENTS, CLAUDE, CODEX, CURRENT, and repo ownership rules into a control-plane instruction map. |
| ASC-0014 | control-plane-monitor-hygiene | closed | Remove monitor false positives for normal contract closeout and repo-suffixed legacy result dispatch ids. |
| ASC-0015 | child-repo-dirty-triage | closed | Resolve the remaining memoryOS and hivemind dirty files left after ASC-0012 and ASC-0014. |
| ASC-0016 | monitor-reconciliation-registry | closed | Add an audited monitor reconciliation registry for known legacy dispatch-history drift. |
| ASC-0017 | control-plane-monitor-sidecar | closed | Keep the MyWorld control-plane observer available as a long-running sidecar. |
| ASC-0018 | loop-policy-source-hygiene | closed | Prevent loop policy from accepting already-closed contract documents as new executable work. |
| ASC-0019 | monitor-assessment-brain | closed | Give the control-plane monitor an assessment layer that maps alerts to owner, severity, and next action. |
| ASC-0020 | hive-worklog-gap-cleanup | closed | Turn Hive worklog and gap-radar signals into one current executable Hive packet without re-opening closed work. |
| ASC-0021 | hive-arrival-pack | closed | Add a Hive arrival-pack surface that gives incoming agents a compact, privacy-safe run brief from live run state. |
| ASC-0022 | aios-goal-evolution-loop | closed | Add a goal-level AIOS evolution loop that turns one active north-star goal into the next best contract candidate with evidence. |
| ASC-0023 | hive-source-read-registry | closed | Add a Hive source-read registry so runs can record which agents read which source artifacts and surface divergent interpretations. |
| ASC-0024 | goal-planner-source-hygiene | closed | Keep the goal evolution planner from selecting broad history/index documents as direct implementation candidates and advance completed preferred-next items. |
| ASC-0025 | child-watcher-provider-fallback | closed | Make child watcher implementation runs recover once from provider access-denied by trying an allowed alternate agent and recording structured fallback evidence. |
| ASC-0026 | capability-observation-aware-routing | closed | Make CapabilityOS recommendations consume prior observation outcomes so later routing decisions reflect real AIOS result history. |
| ASC-0027 | memory-feedback-directives | closed | Make accepted MemoryOS context produce explicit next-run feedback directives and have Hive render them into context_pack.md. |
| ASC-0028 | capability-route-binding | closed | Bind child watcher provider fallback selection to CapabilityOS observation-aware provider route recommendations. |
| ASC-0029 | persistent-control-loop | closed | Add a persistent control-plane round controller so AIOS continuation does not depend on a chat turn staying open. |
| ASC-0030 | capabilityos-web-research-route | closed | Add a recommendation-only CapabilityOS web research route so AIOS can deliberately use broad internet search with source and privacy guardrails. |
| ASC-0031 | web-evidence-execution-loop | closed | Dogfood CapabilityOS web-route by producing and validating a cited web evidence receipt for AIOS capability routing. |
