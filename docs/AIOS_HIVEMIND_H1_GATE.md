# AIOS H¹ Gate Test — Sheaf Cohomology as Composition-Gap Backbone

**Date:** 2026-06-29
**Experiment files:** `scripts/aios_h1_gate.py`, `tests/test_aios_h1_gate.py`
**Status:** COMPLETE — Verdict 2 (honest partial)

---

## Purpose

Falsification test: does H¹ sheaf cohomology provide a real backbone for detecting
AIOS composition gaps, and does it beat a naive baseline?

No laundering. An honest negative (or partial) is the deliverable.

---

## PART A — Mechanism on synthetic AIOS-shaped data

### Graph design

9 nodes (memory records each asserting a scalar benchmark score), 11 edges
(relative measurements m_ij ≈ val_j − val_i). Three triangles connected by
two bridge edges, with one failure mode isolated per triangle:

```
Triangle A (nodes 0-2):   single corrupted edge 0→1, error = +0.30
Triangle B (nodes 3-5):   coherent liar at node 4, constant offset +0.10
Triangle C (nodes 6-8):   incoherent atom at node 7, +0.10 error on both edges
Bridges (2→3, 5→6):       clean
```

### Raw numbers

| Edge                   | H¹ obstruction |
|------------------------|---------------|
| 0→1 **[CORRUPTED]**    | 0.10000000    |
| 1→2                    | 0.10000000    |
| 2→0                    | 0.10000000    |
| 2→3 [bridge AB]        | 0.00000000    |
| 3→4 [liar +0.10]       | **0.00000000**|
| 4→5 [liar −0.10]       | **0.00000000**|
| 5→3                    | **0.00000000**|
| 5→6 [bridge BC]        | 0.00000000    |
| 6→7 [atom +0.10]       | 0.06666667    |
| 7→8 [atom +0.10]       | 0.06666667    |
| 8→6                    | 0.06666667    |

### Finding (i): Does H¹ obstruction mass concentrate on the known-corrupted edge?

**No, not uniquely.** H¹ distributes the holonomy equally across all edges in the
containing cycle. Triangle A has cycle holonomy = CORRUPT\_ERROR = 0.30; each of
the 3 cycle edges gets obstruction = 0.30/3 = 0.10. The corrupted edge (0→1) is
NOT the unique argmax — all 3 Triangle-A edges tie for the maximum.

What H¹ *does* correctly localize: **which cycle** is corrupted. Triangle A edges
all show 0.10; Triangle B (liar) shows exactly 0.00; Triangle C (atom) shows 0.0667.
Prior agent claims of "bad edge is the argmax" were false. The correct statement is
"the bad cycle is the argmax cycle."

### Finding (ii): Coherent liar vs incoherent atom — ratio

| Quantity                        | Value       |
|---------------------------------|-------------|
| Liar cycle holonomy             | 0.00000000  |
| Liar avg H¹ obstruction         | 0.00000000  |
| Atom cycle holonomy             | 0.20000000  |
| Atom avg H¹ obstruction         | 0.06666667  |
| Atom / Liar ratio               | **∞**       |
| Ratio > 10 (claimed criterion)  | **True**    |

**Mechanism confirmed.** The coherent liar adds a constant offset to all its
incident edges. The errors cancel in the cycle sum (gauge shift is a coboundary),
so holonomy = 0 and H¹ obstruction = exactly 0. The incoherent atom injects
same-sign errors on both its incident edges; cycle sum = 2 × 0.10 = 0.20 ≠ 0;
H¹ obstruction = 0.0667. The discrimination is structural and exact.

This matches the ~200:1 claim in spirit; the exact ratio is ∞ because the liar
creates exactly zero holonomy (not just "much less than the atom").

### Finding (iii): Baseline comparisons

**Baseline 1 — Least-squares global solve:**

H¹ obstruction and LS edge residual are numerically identical (max absolute
difference = 0.00e+00). Both compute the same linear-algebra projection:

```
(I − BB⁺) · residual
```

where B is the incidence matrix and B⁺ is its pseudoinverse. LS "smears" the
holonomy as node-value corrections distributed across all nodes; H¹ names the
same numbers as a cohomological obstruction per edge. For gap *detection* the two
are equivalent. H¹ adds a structural interpretation (cycles vs gauge), not a
numerical advantage over LS.

**Baseline 2 — Per-edge cosine/threshold detector:**

| Scenario                    | Threshold (t=0.08) | H¹ |
|-----------------------------|-------------------|-----|
| Large single error (0.30)   | Flags ✓           | Detects ✓ |
| Liar errors (±0.10)         | Flags (false alarm) | Obstruction = 0 ✓ |
| Atom errors (+0.10)         | Flags ✓           | Detects ✓ |
| Sub-threshold holonomy (0.04/edge, cycle sum=0.12) | Misses ✗ | Detects ✓ |

H¹ has a real advantage over per-edge threshold for **sub-threshold distributed
holonomy**: when each edge error is below the detection threshold but the cycle
sum is non-zero, threshold misses all edges while H¹ reports the holonomy. In the
sub-threshold demo: error = 0.04 per edge < threshold 0.08; H¹ obstruction = 0.04
per edge (non-zero); threshold flags 0 edges. This scenario (many small consistent
drift errors forming a non-trivial cycle sum) is a realistic composition gap that
H¹ uniquely catches.

H¹ also correctly suppresses false alarms on the liar (obstruction = 0) while the
threshold fires on liar edges (±0.10 > 0.08).

---

## PART B — Does real AIOS memory carry relative-measurement structure?

Probed 1,438 records across:
- `memoryOS/memory/objects.jsonl` (373 records)
- `~/.aios/memory/objects.jsonl` (1,065 records)

| Category                                     | Count |
|----------------------------------------------|-------|
| Scalar claim + relative comparison language  | 0     |
| Scalar claim only                            | 1     |
| Relative comparison only                     | 219   |
| Prose only (no scalar or relative)           | 1,218 |
| **Candidate fraction for rel-meas edges**    | **0.0%** |

Record types: 193 decisions, 172 observations, 6 unknown, 2 artifacts (memoryOS);
behavioral stats, prose notes, contract decisions (aios memory).

**Plain finding:** Real AIOS memory records do not carry typed relative-measurement
edges. There is no m_ij = val_j − val_i schema. Records are prose decisions,
observations about AIOS operations, and behavioral statistics — not comparable
scalar claims about shared quantities.

The "relative comparison" language present in 219 records (e.g., "better than",
"higher") is qualitative prose, not typed scalar measurements that could form a
SheafCover edge.

---

## VERDICT

**VERDICT (2): MECHANISM SOUND — but real AIOS memory lacks relative-measurement
structure. H¹ backbone requires an architectural addition to memory representation.**

### Precise claims (all verified by 15/15 passing tests):

| Claim | Status | Number |
|-------|--------|--------|
| H¹ obstruction concentrates on bad CYCLE | TRUE | Triangle A obs = 0.10, others 0–0.067 |
| Bad edge uniquely identified within cycle | **FALSE** | All 3 cycle-A edges tie at 0.10 |
| Coherent liar obstruction ≈ 0 | **TRUE** | Exactly 0.00000000 |
| Incoherent atom obstruction >> liar | **TRUE** | Ratio = ∞ (liar = 0) |
| H¹ beats LS for gap detection | **FALSE** — same projection | Max diff = 0.00e+00 |
| H¹ beats per-edge threshold (sub-threshold holonomy) | **TRUE** | 0.04 error, threshold misses, H¹ sees 0.04 |
| H¹ suppresses liar false alarms vs threshold | **TRUE** | Threshold fires on ±0.10; H¹ = 0 |
| Real AIOS memory has rel-meas structure | **FALSE** | 0.0% coverage |

### Architecture implication

The sheaf/H¹ backbone does NOT apply to current AIOS memory as-is. Applying it
requires:

1. Defining a typed **quantity cover** (e.g., "benchmark score on task T") over
   which memory records make comparable scalar claims.
2. Representing each cross-memory comparison as an explicit relative measurement
   edge m_ij with a quantity label, not as prose.
3. Building the SheafCover from those edges.

This is a real architectural gap, not a minor addition. Until memory records carry
typed scalar comparisons over shared quantities, running project\_edge\_field on
AIOS memory produces no signal.

### What H¹ genuinely offers (if the architecture is extended)

- **Holonomy detection**: catches cyclic inconsistency (composition gap) even when
  individual edge errors are sub-threshold. Threshold misses distributed drift;
  H¹ catches the cycle sum.
- **Gauge vs real inconsistency**: liar (constant offset = gauge) gets obstruction = 0;
  atom (contradictory reports = true inconsistency) gets obstruction >> 0. No
  threshold baseline can distinguish these without cycle-level reasoning.
- **Cycle-level fault isolation**: identifies *which cycle* in the memory graph is
  inconsistent, not which individual edge. Useful for routing review/repair to the
  right memory cluster.

### What H¹ does NOT offer

- Per-edge localization to a single bad record within a cycle (holonomy distributes uniformly).
- A detection advantage over least-squares edge residual (they are the same computation).
- Any signal on current AIOS memory without re-architecture.

---

## Reproduction

```bash
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_h1_gate.py        # full experiment + JSON output
python -m pytest tests/test_aios_h1_gate.py -v   # 15 assertions
```

JSON output: `docs/aios_h1_gate_results.json`
