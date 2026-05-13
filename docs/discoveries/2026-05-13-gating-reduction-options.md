# Reducing Operator Gating in AIOS — Options for Founder Decision

Founder turn 2026-05-13: "30% gating 줄이는 작업 잡고, contract 문법이나
시스템 체계 자체를 설계해도 좋아."

Operator (claude) 4-OS query:
- MemoryOS: trace=rtrace_20eb7fffe9644c6d, selected=0 (no prior accepted memory)
- CapabilityOS top: cap_hivemind_execution_harness (46), cap_memoryos_context_build (26)
- GenesisOS: branches[inversion="goal might be symptom", alien_domain="city planning", constraint_removal]
- Hive: aios_invoke passed, dispatch_ready packets ready

**Genesis inversion gives pause**: is "reduce gating" the right framing, or is
the right framing "make autonomy risk-aware"? They sound similar but produce
different contracts.

## What "30% gating" actually consists of (audited)

1. **Send trigger** — operator runs `aios_dispatch.py send` after invocation
2. **Founder GO for proposed contracts** — operator reviews + flips status
3. **memoryOS auto-writeback** — broken (ASC-0091 in flight)
4. **Closeout commit** — codex usually does it but sometimes orphan-dirty
5. **ID collision renumber** — operator manually renumbers (6+ times today)

Of these, only #1 and #4 are pure mechanical operations. #2 and #5 are
genuine operator judgment. #3 is a known fix.

## 5 branches for the actual reduction

### B1 — Auto-send when policy allows (smallest)

After `aios_invoke --execute`, automatically run `aios_dispatch.py send`
for each packet IF:
- ASC-0034 action policy returns `allow`
- ASC-0060 scope-aware policy is `myworld_local_operator_scope` or
  similarly bounded
- No `_from_desktop/dain/minyoung` paths
- No new external authority claims

Effect: removes #1 for low-risk packets. Operator still sees them in
monitor; can stop/hold any time.

Risk: low. Just promotes existing decision logic from "operator runs
manually" to "auto-runs when policy says allow".

### B2 — Closeout auto-writeback (ASC-0091 closure)

Already proposed. Just needs founder GO. Removes #3 directly.

### B3 — Auto-renumber on collision (close ID race)

`aios_dispatch.py create` could acquire a lock on next-N ID. Or
`aios_contract_autodraft.py` could use a UUID-based ID instead of
sequential N. Either removes #5.

Trade-off: sequential IDs are nicer for humans. UUID would break that.
Lock is the cleaner answer.

### B4 — Tiered contract grammar (founder-opened option)

Today every contract is the same shape (~150-300 lines, 4 sections,
work packets). For micro-fixes (typo, regex extension, ID renumber)
this is over-spec'd. Propose 3 tiers:

- **micro**: <30 lines, no work packets, single-step, recommendation-only
  scope; can be auto-issued by operator without founder GO
- **standard**: current shape; founder GO for vision-level
- **major**: requires Hive deliberation (ASC-0084/0089 pattern); cannot
  ship without 5+ round verdict

Each tier maps to autonomy: micro can auto-accept + auto-send; major
cannot auto-anything.

This DOES change AIOS's grammar, which founder explicitly opened up.

### B5 — Risk-aware autonomy envelope (Genesis-inspired)

Don't reduce gating uniformly. Each contract carries an explicit
`autonomy_envelope`:
- `dispatch`: `auto | operator_send | hive_verdict_required`
- `accept`: `auto | operator_review | founder_go | hive_unanimous`
- `merge`: `auto | operator_commit | founder_signoff`

Set per contract, defaulting based on:
- repos touched (myworld-only → looser; multi-OS → tighter)
- privacy paths involved
- reversibility (per ASC-0084 invariant 8)

Effect: gating becomes a property of the work, not of the operator.
The 30% claim becomes meaningless because each contract has its own
gating.

## My (claude operator) recommendation

**B2 (auto-writeback) + B4 (tiered grammar) + B5 (autonomy envelope)** as a
pair, in that order. Reasons:

- B2 is already proposed and well-scoped, low risk, immediately useful.
- B4 changes contract shape but keeps existing contracts valid (only
  introduces a new tier; doesn't remove the standard one). Lets operator
  ship micro-fixes (like ID renumbers) at the speed they actually need.
- B5 ties autonomy to risk in the schema itself, which is what founder's
  "risk-aware autonomy" intuition points at. But B5 alone, without B4,
  forces every existing contract to gain new fields. With B4, micro
  contracts inherit a default loose envelope and standard/major contracts
  inherit tighter.

NOT recommending B1 standalone (too narrow without B5's envelope schema).
NOT recommending B3 standalone (real fix is via ASC-0076 closeout
reconciliation, in flight).

## What founder needs to decide

Pick one or more:
- "GO B2" → flip ASC-0091 to accepted
- "GO B4" → I draft tiered-contract-grammar contract for AIOS approval (Hive deliberation? or operator scope?)
- "GO B5" → I draft autonomy-envelope contract
- "GO B2+B4+B5" → all three as a coordinated trio
- "GO different" → reframe with founder's preferred direction
- "Hive 토론" → route this options doc to Hive for adversarial verdict (ASC-0084 pattern)

NOT auto-accepting any of these. Surfaced for founder pick.
