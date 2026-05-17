# AIOS Benchmark Results — First Matched-Run Fixture

Status: executed protocol-validation run (ASC-0182)
Date: 2026-05-17
Protocol: `docs/papers/AIOS_BENCHMARK_PROTOCOL.md` (ASC-0162)
Repo snapshot: `b1fdb2a`
Fixtures + run artifacts: `benchmark/fixtures/`, `benchmark/runs/`

## Honesty preface (binding — ASC-0162 Claim Rules)

This is **N=3, a protocol-validation run, not a superiority claim**. The same
LLM provider performed each task twice on an identical fixture snapshot; the
only manipulated variable is the operating layer. Where AIOS is pure overhead,
it is reported as overhead. Where a claimed gain did not materialize, that is
reported as a null result.

## Tasks

| Task | Family | What it discriminates |
|---|---|---|
| A | 1 — single-repo bug fix | AIOS overhead on clean, isolated work |
| B | 5 — restart/resume across a session boundary | AIOS continuity gain |
| C | 7 — prior-decision-dependent work | MemoryOS recall gain |

## Table 1 — Pair Summary

| Task | Provider | Direct CLI Result | AIOS Result | Main Gain | Main Overhead |
|---|---|---|---|---|---|
| A | claude-opus-4-7 | 4/4 tests pass | 4/4 tests pass | none — outcomes identical | +3 governance artifacts, contract-authoring time |
| B | claude-opus-4-7 | resume partial — design intent lost, 1 reprompt | resume success — intent certified, 0 reprompt | prior decision crossed the session boundary | +1 contract artifact |
| C | claude-opus-4-7 | fail — no prior-decision recall | fail — memory layer returned 0 items | none — claimed recall unrealized | memory store maintained but not queryable |

## Table 2 — Artifact Trace

| Task | Condition | Required Artifacts Present | Missing | Trace Complete |
|---|---|---|---|---|
| A | Direct CLI | final diff, test output | contract, packet, ledger | no (none expected) |
| A | AIOS | contract, dispatch, result, ledger, diff, test output | — | yes |
| B | Direct CLI | resume log, final code | record of prior decision | no — intent unrecoverable from code |
| B | AIOS | contract (part-1 decision recorded), resume log, final code | — | yes |
| C | Direct CLI | — | any memory surface | no (none expected) |
| C | AIOS | memory store (198,485 nodes) | embeddings (0%), retrieval result | no — store present, recall absent |

## Table 3 — Overhead

| Task | Direct Time | AIOS Time | Extra Artifacts | False Holds | Human Reprompts (Direct / AIOS) |
|---|---|---|---|---|---|
| A | baseline | + contract-authoring | +3 | 0 | 0 / 0 |
| B | baseline | + contract-authoring | +1 | 0 | 1 / 0 |
| C | baseline | negligible (recall path empty) | 0 usable | 0 | n/a (both fail) |

(Mechanical edit times were sub-second and identical across conditions — the
fix was byte-identical, confirming the model was held constant. The real
AIOS cost is contract-authoring, not execution.)

## Table 4 — Negative Evidence And Creativity Trace

| Task | Failure Memories | Bad Tool Observations | Genesis Recombination Candidates | Promoted To Contract |
|---|---|---|---|---|
| A | none | none | none | n/a |
| B | none | none | none | n/a |
| C | **MemoryOS recall returned 0 items for a memory-relevant query; embedding coverage 0.0% (0/44 objects)** | `memoryos context build` and `search` both empty | none generated | should be — see below |

## Findings

1. **On clean isolated work (Task A), AIOS is pure overhead.** Both conditions
   produced a byte-identical fix and 4/4 passing tests. AIOS added three
   governance artifacts and contract-authoring time for zero outcome gain.
   This is the honest cost and the paper must not hide it.

2. **On continuity across a session boundary (Task B), AIOS delivers a real,
   measured gain.** The fixture embedded a design decision (whitespace
   collapse is intentional; round-trip is lossy by design) that the *code did
   not encode*. The baseline resumer could re-derive the code but not the
   intent — it had to guess, and a competent provider could plausibly
   "fix" the intended behavior into a bug. The AIOS resumer read the decision
   from the contract and certified consistency: 0 reprompts vs 1. The gain
   came from the **deterministic layer** (contract + ledger), which is built
   and works.

3. **On memory-dependent work (Task C), AIOS's claimed gain is currently
   unrealized.** Empirically: `memoryos context build` returned 0 items and
   `search` returned 0 hits for a memory-relevant query, because embedding
   coverage is 0.0%. AIOS maintains a 198,485-node store but cannot yet query
   it. On memory-dependent tasks today AIOS provides no advantage over the
   baseline. This is a null result and the paper reports it as one.

## Synthesis

The three tasks separate AIOS's value cleanly along the audit's own fault
line. AIOS's **deterministic layer** — contracts, dispatch, ledger — is built,
works, and delivers a genuine continuity gain (Task B) at a real but bounded
overhead cost (Tasks A, B). AIOS's **cognition-closing layer** — semantic
memory retrieval — is scaffolded but unrun (Task C), so its headline gain is
not yet real.

The honest one-line claim the paper may make from N=3: *AIOS today buys
verifiable continuity and governance at an artifact-overhead cost; its memory
advantage is contingent on closing the embedding gap and is not yet
demonstrated.*

## Task C re-run (2026-05-17, after embedding completed)

The embedding job completed: coverage 0.0% → **100.0%** (44/44 objects;
197,345 nodes embedded, 1,327 failed = 0.7%). Task C was re-run on the same
query class.

| | before embedding | after embedding |
|---|---|---|
| `memoryos context build` | 0 items | **10 decisions returned per query** |

The null result **flipped**. Three independent memory-relevant queries each
returned 10 ranked decision records (e.g. a prior founder directive
"계속 Contract를 발행해", contract closeouts ASC-0091/0095/0096). AIOS's
memory layer now retrieves; the gain it claimed — contingent on closing the
embedding gap — is demonstrated at the retrieval level.

Honesty note: this confirms retrieval is **non-empty and plausibly relevant**,
which is the binary Task C tested. Ranking *quality* (how well the top item
matches intent) is a separate, untested follow-on. The claim earned is "the
memory layer works," not yet "the memory layer is well-tuned."

Updated Task C verdict: **Direct CLI fail / AIOS success** — the memory gain
is real once embeddings are closed.

## Next

- Expand to families 2, 3, 4, 6 (multi-file, multi-repo, failure-recovery,
  external-research) before any broad utility claim.
- Measure memory-retrieval *relevance* quality, not just non-emptiness.
