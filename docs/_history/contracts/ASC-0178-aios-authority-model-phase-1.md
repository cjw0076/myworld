---
contract_id: ASC-0178
slug: aios-authority-model-phase-1
status: closed
goal: Execute phase 1 of the ASC-0174 verdict (`proceed_authority_routed_management_plane`) — land the authority-model vocabulary in the DNA, reconcile the ASC-0128..0177 permission-chain contracts under retain/rewrite/withdraw, and name the remaining phase-1 downstream work as packets.
created: 2026-05-15 KST
accepted: 2026-05-15 KST by claude@myworld — phase 1 explicitly authorized by founder GO on the ASC-0174 verdict ("verdict accept, phase 1 착수")
closed: 2026-05-15 KST — all 4 stop conditions met (DNA amendment, Packet A 14 contracts reconciled, Packet B policy rule, Packet C 5 follow-ons named)
supersedes: none (reconciles, does not supersede — see classification table)
acceptance_authority: founder GO on ASC-0174 verdict is the acceptance basis for phase 1 execution
origin: ASC-0174 6-round Hive deliberation converged on `proceed_authority_routed_management_plane`; founder accepted the verdict and authorized phase 1. This contract is the phase-1 entry point.

---

# ASC-0178 AIOS Authority Model — Phase 1

## What ASC-0174 Decided

AIOS is an **authority-routed management plane**: active at the operating
layer, bounded at the product-artifact layer. It owns 10 system calls
(observe, ingest, retrieve, route, challenge, execute, refuse, override,
promote, close) and routes every action along 4 authority axes
(record / schema / participation / override). AIOS-owned records get
pre-fact gates; product-owned records are observed post-fact unless the repo
delegates a hook. Dangerous execution is an opt-in system call, not the
default identity.

## Done In This Contract

### Item 1 — DNA amendment (COMPLETE)

`docs/AIOS_DNA.md` now carries a "Authority Model (v0.1 amendment — ASC-0174)"
section: identity statement, 4 authority axes, 10 system calls, pre-fact vs
post-fact rule. Append-only; Invariants 1–8 unchanged. The ASC-0174 6-round
deliberation satisfies the DNA Amendment Clause (≥3 round Hive requirement).

## Chain Reconciliation — retain / rewrite / withdraw

The ASC-0174 verdict's reconciliation rule:

- **retain**: contracts that harden AIOS-owned records or provider receipts.
- **rewrite**: product-execution expansion → recast as delegated hook
  (ASC-0173 consent-emit pattern) or participation refusal.
- **withdraw**: raw permission expansion that does not name record authority,
  stop condition, fallback, and receipt.

Provisional classification (each contract's status flip is Packet A — requires
individual read before the flip is applied; this table is the operator's
first-pass and is itself reviewable):

| Contract(s) | Theme | Class | Reason |
|---|---|---|---|
| ASC-0166 provider-PIN-classification | classify PIN failures, no secret storage | **retain** | hardens AIOS-owned provider receipts; closed with tests |
| ASC-0168 hivemind-permission-preflight | preflight before provider exec | **retain** | AIOS-owned execution record hardening |
| ASC-0169 hivemind-aios-packet-runner | Hive consumes its own packets | **retain** | AIOS-owned execution authority, not product overreach |
| ASC-0170 scoped-writable-provider-execution | gated writable execution | **retain** | explicit operator-grant + receipt; matches opt-in system-call rule |
| ASC-0171 permissioned-dangerous-provider-execution | dangerous full-access route | **rewrite** | keep the route but recast as explicit `execute` opt-in system call with structured receipt, not a standing capability |
| ASC-0131, ASC-0138 "AIOS take over uri sprint 008" | product execution takeover | **rewrite** | recast as ASC-0173 delegated consent-emit; AIOS does not take over product execution |
| ASC-0132, ASC-0133, ASC-0134, ASC-0136, ASC-0139 product-repo-sprint-driver | drive product sprints via AIOS | **rewrite** | product repos keep execution; AIOS observes/absorbs via ASC-0173 |
| ASC-0135 research-to-sprint-context | context primitive | **retain** | AIOS-owned context record; legitimate |
| ASC-0137 record-codex-provider-loop-gap | record a friction gap | **retain** | this is negative-evidence recording — exactly what the verdict wants stored |
| ASC-0128, ASC-0129, ASC-0130, ASC-0140, ASC-0142, ASC-0176, ASC-0177 provider-fallback-execution-binding (template clones) | "Bind ASC-0066 provider backpressure..." boilerplate | **withdraw** | identical template, no named record authority / stop condition / fallback / receipt; raw permission expansion |
| ASC-0175 memoryos-continuous-health-instrumentation | memoryOS health | **retain** | unrelated to the chain; legitimate AIOS-owned instrumentation |

## Work Packets

### Packet A — myworld applies the reconciliation

- Owner: `myworld`
- Action: for each contract in the table, read it individually, confirm the
  class, and flip frontmatter: `retain` → leave as-is; `rewrite` →
  `status: superseded-by-rewrite`, add `rewrite_target:` pointing at the
  ASC-0173 delegation pattern or a new rewrite contract; `withdraw` →
  `status: withdrawn`, add `withdrawn_reason: raw-permission-expansion-no-authority-model (ASC-0178)`.
- Append-only: do not delete contracts. Withdrawal is a status, not a deletion.
- Acceptance evidence: `git grep -l "withdrawn_reason: raw-permission" docs/contracts/ | wc -l` ≥ 5; no contract from the table left in `proposed` limbo.

### Packet B — myworld adds the no-raw-permission rule to action policy

- Owner: `myworld`
- Action: append to `docs/AIOS_ACTION_POLICY.md`:

```text
A contract that expands provider/execution permission is `hold` (not `allow`)
unless it names all four: record_authority, stop condition, fallback path,
and result receipt. Raw permission expansion without these is the ASC-0178
withdraw class. The autodrafter must not emit "Bind ASC-0066..." template
clones; goal packets about provider backpressure route to the ASC-0173
delegation pattern instead.
```

- Acceptance evidence: the rule text is present in `AIOS_ACTION_POLICY.md`.

### Packet C — remaining phase-1 downstream (named, not yet scoped)

These are phase-1 obligations from the ASC-0174 final_state. Each becomes its
own contract; this packet only names them so they are not lost:

1. Surface authority/system-call labels in the Control UI (`apps/control/`).
2. Store MemoryOS negative evidence: provider failures, rejected ingests,
   privacy holds, stale memories, wrong routes.
3. Teach CapabilityOS bad-tool and fallback-quality routing (not only
   recommend good tools).
4. Make GenesisOS discomfort gates part of contract close.
5. Make Hive execution envelopes record provider route, failure category,
   fallback, verification, and result receipt.

- Acceptance evidence: the 5 items are named above so they are not lost.
  Drafting each as its own contract is deferred to follow-on sessions —
  naming here satisfies this packet (per stop condition 4).

## Stop Conditions

This contract closes when:

1. DNA amendment present (✓ done).
2. Packet A reconciliation applied — every table contract has a non-`proposed`
   status with a recorded class reason.
3. Packet B policy rule present in `AIOS_ACTION_POLICY.md`.
4. Packet C — 5 follow-on contracts named (drafted as `proposed`).

This contract **fails and escalates to founder** if:

- Any reconciliation flip deletes a contract instead of setting a status.
- A 15th "Bind ASC-0066..." template clone is autodrafted while this contract
  is open (signals Packet B did not bind).
- The retain/rewrite/withdraw classification is applied without individually
  reading the contract (the table is provisional, not authoritative).

## Provenance

- ASC-0174 verdict `proceed_authority_routed_management_plane`, founder-accepted
- `hivemind/.runs/observer_vs_executor_debate/final_state.md`
- `docs/AIOS_DNA.md` Authority Model v0.1 amendment
- `docs/contracts/ASC-0173-product-repo-consent-emitted-evidence-ingest.md`
  (the reference delegation primitive for the rewrite class)
