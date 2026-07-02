# AIOS headline A/B — does the behavioral-memory ledger measurably help an agent?

> The product's headline is **"your agents carry forward what worked."** That mechanism is
> built (`scripts/aios_agent_behavior.py`: ingest → record → `predict_behavior`) but its
> *outcome* was never measured. This is that measurement, run for real. Harness:
> `scripts/aios_headline_ab.py`; battery: `experiments/headline_ab/tasks/`; raw numbers:
> `docs/aios_headline_ab_results.json`. Honest-negative discipline applies — a null/mixed
> result is a first-class finding and is reported exactly as it came out (no post-hoc tuning).

## Setup (pre-registered, one design, one run)

Two arms, identical model / decoding / budget / oracle, differing in ONE thing:

- **Arm A (bare):** TEST task prompt → model → extract code → pytest oracle. Up to `R=2`
  attempts; on failure the oracle output is fed back once. Attempts counted.
- **Arm B (+ledger):** IDENTICAL, but the prompt is prefixed with a single generic behavioral
  guidance block **retrieved from a ledger seeded on a DISJOINT TRAIN set** via the real record
  path (`write_to_akashic` + `predict_behavior`, offline, isolated `AIOS_HOME`).

**No train/test leakage — by construction.** The ledger only ever contains behavioral
signatures of TRAIN runs (tool pattern / attempt count / a generic "what worked" note). It
contains no TEST task identifier and no solution code (a hermetic unit test asserts this in
`tests/test_aios_headline_ab.py`). The injected block is generic behavioral guidance, the same
text for every TEST task — never per-task-tailored (there is nothing task-specific to tailor).

| parameter | value |
|---|---|
| substrate | local ollama, **phi4-mini:latest (3.8B)** — see "Substrate choice" below |
| battery | 8 self-contained Python tasks, **3 TRAIN / 5 TEST, disjoint problems** |
| task kind | "counter-prior" specs (precise rules that contradict the convention prior) |
| R (attempts, feedback once) | 2 |
| trials / arm / TEST task | 8 → **N = 40 per arm** (pilot at trials=3, N=15, first) |
| decoding | temperature 0.6, top_p 0.9, num_predict 768; seeds matched per (task,trial,attempt) across arms; arm order alternated per trial |
| ledger seed | phi4-mini run bare on 3 TRAIN tasks × 2 runs → 6 behavioral records |
| runtime | 106 s (well under the 40-min cap) |

**Substrate choice (a real calibration finding, not a free parameter).** The requested default
`qwen2.5-coder:7b` is **above the ceiling** for this whole task class: bare pass@1 was ≈ 6/6 on
almost every small function we tried (textbook *and* counter-prior; roman numerals, IPv4, merge
intervals, swapped FizzBuzz, backward Caesar, …), leaving no headroom for a ledger to help. Per
the v0 lesson ([[docs/AIOS_HIVEMIND_V0_RESULTS.md]]: "the experiment is only valid when the agent
is above the task's floor" — and here, *below its ceiling*), we dropped to **phi4-mini (3.8B)**, a
real coding-capable model whose bare pass@1 lands in the measurable band (1–5 of 6) on all 8
tasks. `AIOS_AB_MODEL` overrides the model; both findings are reported.

## Results (Arm A vs Arm B, N = 40 per arm)

```
                          Arm A (bare)   Arm B (+ledger)   Δ (B − A)
within-budget solve rate      0.825          0.675          −0.150
first-attempt pass@1          0.450          0.600          +0.150
mean attempts (all trials)    1.55           1.40           −0.15
total output tokens           4965           4848           −117
```

The direction is **stable across the pilot and the definitive run**, so it is not a single-N
fluke:

| run | N/arm | solve A | solve B | pass@1 A | pass@1 B |
|---|---|---|---|---|---|
| pilot (trials=3) | 15 | 0.867 | 0.733 | 0.467 | 0.600 |
| **definitive (trials=8)** | 40 | 0.825 | 0.675 | 0.450 | 0.600 |

### Per-task (N = 8 per arm per task)

| task (bare pass@1 calib) | solve A | solve B | pass@1 A | pass@1 B | attempts A | attempts B |
|---|---|---|---|---|---|---|
| caesar_backward (5/6) | 0.875 | 0.875 | 0.500 | **0.875** | 1.50 | **1.12** |
| ipv4_lenient (3/6)    | 0.875 | 0.750 | 0.250 | **0.625** | 1.75 | **1.38** |
| factorial_zero (3/6)  | 0.875 | 0.750 | 0.500 | 0.500 | 1.50 | 1.50 |
| count_down (1/6)      | 0.500 | **0.000** | 0.000 | 0.000 | 2.00 | 2.00 |
| lower_middle (5/6)    | 1.000 | 1.000 | 1.000 | 1.000 | 1.00 | 1.00 |

## Reading (honest)

**The result is genuinely MIXED, and the mechanism is the interesting part.** The ledger helps
one thing and hurts another, and they are the *same* underlying trade:

1. **The ledger improves first-attempt accuracy: pass@1 0.45 → 0.60 (+33% relative).** On the
   FIRST try — before the model has seen any oracle feedback — the generic behavioral prime
   ("write the function, then verify; watch the edge cases you were told about") measurably
   raised the fraction solved. It also cut mean attempts (1.55 → 1.40) and output tokens. On the
   product's own terms ("carry forward what worked"), the carried-forward behavior did help the
   agent get it right sooner and cheaper.

2. **The ledger LOWERS the within-budget solve rate: 0.825 → 0.675 (−0.15).** The cause is not
   first-attempt accuracy (which improved) — it is **retry recovery**. Among trials that failed
   attempt 1:

   ```
   Arm A (bare):    22 first-attempt failures → 15 recovered on retry  (recovery 68%)
   Arm B (+ledger): 16 first-attempt failures →  3 recovered on retry  (recovery 19%)
   ```

   The always-on guidance prefix stays in the prompt during the oracle-feedback retry, where it
   **competes with the concrete "expected X, got Y" error signal** — anchoring the model on its
   first approach and collapsing recovery from 68% to 19%. Net, B's higher pass@1 is more than
   erased by its far weaker retry. In one line: **the ledger trades retry-adaptivity for
   first-shot commitment.**

This is a concrete, actionable product finding: behavioral memory is useful *at the first shot*
(cheaper, faster, more first-time-right), but a naive always-injected guidance block **should be
dropped, or replaced by the concrete error, once oracle/tool feedback is available** — otherwise
it suppresses the error-driven correction that a bare agent does well.

## What it does NOT show

- It does **not** show the ledger is net-positive on solve rate — here it was net-**negative**
  (−0.15), driven by the retry-recovery collapse. We report that straight.
- It does **not** isolate "ledger-specific value" from "any generic advice." The injected block
  is generic behavioral guidance; a fixed hand-written "be careful, handle edge cases, verify"
  prefix might produce a similar pass@1 bump. What is ledger-derived here is the *numbers and the
  action pattern* (4/6 solved, mean 1.5 attempts, `WriteCode→RunOracle→ReadError`), not a
  bespoke per-task hint. Distinguishing the two needs a third arm (fixed-advice control) — next.
- The derived lesson is **edge-case-framed** ("unhandled edge cases…"), which is only partly
  aligned with the actual counter-prior failure mode ("used the conventional rule, not the
  specified one"). A ledger that surfaced *that* lesson might help more — untested here.
- `count_down` (the hardest task, bare 1/6) alone accounts for much of the solve-rate gap
  (A 0.5, B 0.0). But the retry-recovery collapse is **not** a count_down artifact — it also
  appears on ipv4_lenient and factorial_zero, and is what makes the aggregate move.

## Caveats

- **Small n:** N = 40 per arm, 5 TEST tasks × 8 trials. Per-task cells are N = 8. Directional,
  not definitive.
- **One model:** phi4-mini (3.8B). A different-strength substrate could move both metrics — and
  indeed qwen2.5-coder:7b was above the ceiling entirely (the ledger had nothing to add there,
  which is itself a finding: for a strong coder on small tasks, first-shot is already saturated).
- **Synthetic battery:** eight small "counter-prior" functions, chosen for measurable headroom.
  They are not a representative sample of real agent work.
- **One design, one definitive run** (plus a disclosed pilot that agreed in direction). No
  post-hoc battery/guidance tuning was done to move the A-vs-B gap; difficulty was calibrated
  only on *bare Arm-A* pass@1, before the arms were compared.

## Bottom line (earned, not laundered)

On this instrument, **behavioral memory measurably helped the agent get it right the first time
(+33% relative pass@1, fewer attempts and tokens) but measurably hurt its ability to recover from
a failed attempt (retry recovery 68% → 19%), for a net −0.15 on within-budget solve rate.** The
headline "carry forward what worked" is supported *for first-shot behavior* and falsified *as an
always-on prefix during feedback-driven retry* — a specific, testable design correction, not a
verdict that memory is useless. Directional, one 3.8B model, synthetic battery; the harness now
makes the follow-ups (fixed-advice control arm; retry that drops the prefix; stronger/other
substrates) one command each.
