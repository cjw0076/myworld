# AIOS SECI Pipeline — Next Steps

_Source: `scripts/aios_seci_pipeline.py` · Reviewed: 2026-06-21_

---

## Top 3 improvement areas

### 1. No deduplication guard in phase_e (critical correctness gap)

**Problem:** `phase_e` unconditionally calls `write_draft` for the top-N patterns every
cycle. Running the SECI cycle twice on the same session data floods MemoryOS with
duplicate drafts. The `raw_refs` field carries the pattern ID, but `write_draft` does
not reject duplicates.

**Fix:** Before calling `write_draft`, query MemoryOS for existing drafts whose
`source_run_id` matches the pattern ID.

```python
# in phase_e, before write_draft call:
existing = _query_drafts_by_source_id(MEMORYOS_ROOT, pat.get("id"))
if existing:
    print(f"  [E] skip duplicate: {pat.get('id')}", file=sys.stderr)
    continue
```

Alternatively, add a local seen-set backed by a small JSON manifest at
`MEMORYOS_ROOT/.seci_submitted.json` keyed on pattern ID. Either approach
eliminates re-submission without touching the MemoryOS schema.

---

### 2. Pattern selection quality criterion is too shallow (phase_e ranking)

**Problem:** `phase_e` sorts candidates by `len(set(tool_freq.keys()))` — raw tool
breadth. A one-off session that happened to touch many tools ranks above a high-frequency
pattern that consistently uses 2–3 key tools. This inverts the value order for
internalization.

**Fix:** Replace the single-key sort with a composite score:

```python
def _pattern_score(m: dict) -> float:
    freq = m.get("tool_freq") or {}
    diversity = len(set(freq.keys()))
    frequency = sum(freq.values())          # total invocations
    confidence = m.get("confidence", 0.5)
    return diversity * 0.3 + frequency * 0.5 + confidence * 0.2

top = sorted(clean, key=_pattern_score, reverse=True)[:max_drafts]
```

Weights are illustrative; tune after running `--phase e --dry-run` and inspecting
which patterns surface. The key change is that `frequency` (total invocations across
sessions) becomes the dominant signal.

---

### 3. Phase I verification is disconnected from the actual cycle (I phase feedback gap)

**Problem:** `phase_i` in `run_cycle` verifies internalization with a hardcoded
context (`"just read a file, need to make a change"`) and hardcoded candidates
(`["Edit", "Read", "Write", "Bash", "WebSearch"]`). This does not test whether
the memories promoted in phase C actually influence future predictions — it tests
a static probe that was already there before the cycle ran.

**Fix:** Derive the I-phase input from cycle output:

```python
# After phase_c, build context from accepted draft content
if review["accepted"]:
    # retrieve accepted memory content for verify context
    verify_ctx = f"acting on memory: {review['accepted'][0]}"
else:
    verify_ctx = verify_context  # fallback to default

# Derive candidates from tools observed in S phase
observed_tools = set()
for m in memories:
    observed_tools.update((m.get("tool_freq") or {}).keys())
candidates = list(observed_tools)[:8] or ["Edit", "Read", "Bash"]

prediction = phase_i(context=verify_ctx, candidates=candidates)
```

This closes the actual feedback loop: S observes → E externalizes → C promotes →
I verifies that promoted memories change predictions for the same tool context.

---

## Minor cleanup (non-blocking)

- `_load_behavior()` uses `importlib.util.spec_from_file_location` unnecessarily
  since `scripts/` is already on `sys.path`. Replace with `import aios_agent_behavior as b`.
- `_pattern_to_draft` truncates `content_lines` at 200 chars. Raise to 500 and strip
  newlines to preserve more signal without hitting MemoryOS field limits.
- `phase_c` accesses result fields via `getattr(result, "accepted", [])` — this is
  correct only if `auto_review` returns an object, not a dict. Add a dict/object
  branch or normalise the return type in `auto_reviewer.py`.
