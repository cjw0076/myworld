# AIOS Hivemind v0 — first empirical results (the smallest honest test)

> The falsification experiment from [[docs/AIOS_HIVEMIND_DESIGN.md]] §"v0 — the SMALLEST
> HONEST test", run for real. Thesis under test: does **pooled+verified** (multiple agents
> on hand-decomposed leaves, each oracle-checked) beat a **single** agent on the whole task,
> under EQUAL compute, with a REAL machine oracle for both leaves and the whole — and how
> often does the **composition gap** (all leaves pass ∧ the whole fails) occur. Harness:
> `scripts/aios_hivemind_probe.py`; agent substrate: local `qwen3-coder:30b`.

## Run 1 — coding domain (pytest oracle)

Task `coding_iface`: a 2-module pipeline deliberately built with WEAK leaf contracts (the
producer's unit test is key-name-agnostic; the consumer hard-codes the key `value`) so a
composition gap is *possible*. Budget 6 (equal across arms), 3 trials.

```
solve_rate_A (single agent, whole task)      = 1.0
solve_rate_B (pooled + per-leaf verified)    = 0.0
composition_gap_rate_B                        = 1.0
```

**Reading (honest):** on this task the single agent WON decisively and the composition gap
was TOTAL. Every Arm-B trial: both leaves passed their own oracle, yet the integration test
failed — the producer emitted one key, the consumer expected another; neither leaf agent
could see the mismatch. The single agent, writing both modules at once, naturally kept them
consistent. This is the MASFT "inter-agent misalignment / incorrect-verification" failure
and the architect's "composition is the hardest part" — reproduced empirically, 100%.

**What it does and does NOT show:**
- DOES: the composition gap is real and, with under-specified leaf contracts, *decisive* —
  it sank pooled+verified entirely. The interface contract is the load-bearing variable.
- Does NOT: show pooling never helps. The decomposition here was deliberately
  contract-weak. The natural next experiment: add an explicit shared interface contract to
  the leaf prompts + leaf oracles and re-measure — does the gap close and does B then beat A?
- Caveat: small (3 trials), one model, a task *designed* to expose the gap. Directional, not
  definitive. The value is that it isolates the mechanism, not that it ranks pooled vs single
  in general.

## Run 2 — Lean / formal-proof domain (lean oracle)

Task `lean_compose`: parent `theorem t : ∀ n, n + n = 2 * n` (provable directly by `omega`),
hand-decomposed into two *insufficient* leaves `p0 : 0+0=2*0`, `p1 : 1+1=2*1` (each Lean-checks,
but two instances cannot prove the universal — composition gap verified real: parent_compose.lean
exits 1 while p0/p1/direct-proof exit 0). Cross-domain replication of the same thesis.

```
solve_rate_A (single, direct proof of the universal)  = 0.0
solve_rate_B (pooled: p0,p1 then compose)             = 0.0
composition_gap_rate_B                                 = 1.0
```

**Reading (honest):** the composition gap is again TOTAL (leaves p0/p1 Lean-checked, the
parent-from-leaves rejected — by construction). BUT this run is dominated by an **agent
capability ceiling**, not just the gap: `qwen3-coder:30b` could not produce even the direct
`omega` proof of `∀ n, n+n=2*n` (Arm A = 0), although that proof checks
(`solution/t_direct.lean` exits 0). So Arm A and Arm B are both 0 — the A-vs-B comparison is
**degenerate** because the substrate is below the task's floor.

**Lesson (a real one):** the experiment is only valid when the agent is ABOVE the task's
capability floor. qwen3-coder is above the floor for the trivial coding task (Arm A = 1.0)
but BELOW it for Lean (Arm A = 0.0). A meaningful Lean A-vs-B needs a stronger agent
substrate (a frontier model, or a Lean-specialized prover) — route via multi-substrate, not
local qwen, for the formal-proof domain.

## Cross-domain synthesis

| domain | agent capable (Arm A) | solve_A | solve_B | composition_gap_B | clean A-vs-B? |
|---|---|---|---|---|---|
| coding (pytest) | yes (1.0) | 1.0 | 0.0 | 1.0 | YES — pooled loses to single |
| Lean (lean) | NO (0.0, below floor) | 0.0 | 0.0 | 1.0 | degenerate (agent ceiling) |

Two robust facts across both domains: (1) **the composition gap is real** (gap_rate = 1.0
both times — leaves verify, the whole does not); (2) **the instrument works** — it measures
the gap and ranks the arms whenever the agent is above the task floor.

The clean coding result is a *negative on the naive thesis, positive on the team's
diagnosis*: pooled+verified is not free lunch — success is gated entirely by whether the
decomposition carries strong enough interface/goal contracts to close the composition gap.
This matches every office-hour source (MASFT incorrect-verification 9.1%; Meta-Agent =
IO-contracts + re-decomposition; the gap is THE unsolved part).

## Next experiments (the real research loop the probe now enables)

1. **Close-the-gap test (coding):** add an explicit shared interface contract to the leaf
   prompts + a contract-level leaf oracle; re-measure. Does composition_gap_B drop and does
   B then beat A? This directly tests the design's composition mechanism.
2. **Capable-agent Lean run:** swap the substrate to a frontier model for `lean_compose` so
   Arm A is non-zero; then the A-vs-B + gap comparison becomes meaningful in the formal domain.
3. **Good vs bad decomposition:** same task, a contract-strong decomposition vs the current
   contract-weak one — quantify how much of B's failure is the decomposition, not pooling.
