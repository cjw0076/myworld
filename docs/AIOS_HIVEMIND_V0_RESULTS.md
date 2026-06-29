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

*(result pending — run in progress)*

## Interpretation so far

The first data point is a clean *negative on the naive thesis and a clean positive on the
team's diagnosis*: pooled+verified is not free lunch — its success is gated entirely by
whether the decomposition carries strong enough interface/goal contracts to close the
composition gap. This matches every source pulled in the office-hour (MASFT incorrect-
verification 9.1%; Meta-Agent's whole point is IO-contracts + re-decomposition; the gap is
the unsolved part). The probe is now the instrument to measure whether any proposed
contract/composition mechanism actually closes the gap — which is the real research loop.
