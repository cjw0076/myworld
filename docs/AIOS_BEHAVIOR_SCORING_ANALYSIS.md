# AIOS Behavior Scoring Analysis

> Analyzed: 2026-06-21 | Source: scripts/aios_agent_behavior.py lines 435-699

---

## 1. Can doom_loop sessions contaminate transition scores?

**Partial yes — mitigation exists but has a gap.**

`_transition_scores()` (line 435) applies `weight = 0.1` for `doom_loop` sessions when
counting adjacent tool pairs. This correctly reduces (not eliminates) their influence.

**Gap**: `freq_scores = _frequency_scores(candidates, top_mems)` (line 632) is called on
`top_mems` which includes doom_loop sessions at full weight — it does NOT use `clean_mems`.
The variable `clean_mems` is computed on line 631 but only used for the `support` evidence
strings (lines 668-671), never for actual scoring.

So: transition contamination is mitigated (0.1x weight). Frequency contamination from
doom_loop sessions is NOT mitigated — they count at full 1.0x in freq_scores.

**Fix**: Pass `clean_mems` to `_frequency_scores()`:
```python
# line 632 — change from:
freq_scores = _frequency_scores(candidates, top_mems)
# to:
freq_scores = _frequency_scores(candidates, clean_mems or top_mems)
```

---

## 2. Is the 3-weight blend (40% freq + 30% descent + 30% transition) sound?

**Reasonable, with one structural concern.**

The weights (40/30/30 with prev_tool, 60/40 without) are proportionally balanced. The
fallback to uniform distribution in `_transition_scores()` when `total == 0` (line 457)
is correct — it prevents score collapse.

**Concern**: `_transition_scores()` normalizes by `max_c` (line 459), producing scores
in [0, 1] relative to the most frequent transition. But `_frequency_scores()` normalizes
by `total` (line 432), producing scores in [0, 1] as a probability. These are
differently-scaled quantities being combined with equal precision (30/30). This is not
wrong but makes the 30% weight for `trans` structurally different from the 30% for
`descent` — descent is a cosine similarity [−1, 1] clipped by DescentNet's behavior,
frequency is a probability, transition is a max-normalized count ratio.

The blend works in practice because all three happen to produce values in ~[0, 1], but
a more rigorous implementation would standardize all three to the same scale (e.g.,
softmax normalization before blending).

---

## 3. Concrete improvement recommendation

**Apply doom_loop exclusion to freq_scores, not just support strings.**

One-line fix on line 632:

```python
# Before:
freq_scores = _frequency_scores(candidates, top_mems)

# After:
_scoring_mems = clean_mems if clean_mems else top_mems
freq_scores = _frequency_scores(candidates, _scoring_mems)
```

This closes the contamination gap identified in §1. The `transition_scores` already
applies 0.1x weighting; this fix makes freq scoring consistent.

Expected impact: in domains where doom_loop sessions dominate the memory corpus (e.g.,
early training data with repetitive Bash→Bash→Bash sequences), this prevents the
frequency score from over-recommending the repeated tool.

---

## Summary

| Issue | Severity | Status |
|-------|----------|--------|
| doom_loop contaminates freq_scores | Medium | Not fixed — clean_mems not used for scoring |
| Transition score contamination | Low | Mitigated (0.1x weight) |
| Weight scale heterogeneity | Low | Acceptable, document if publishing externally |

**Recommended action**: Apply the one-line fix above. Add a regression test verifying
that a corpus of 3 doom_loop sessions + 1 clean session doesn't rank a repeated tool
above a clean-session signal.
