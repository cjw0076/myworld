---
name: absorption-probe
description: >-
  Measure whether AIOS actually changes a model's behavior (absorption) vs is
  theater, by running the same real task in two isolated agent arms — bare vs
  +AIOS organ loop — with IDENTICAL repo/web access, then scoring the
  behavior-delta on fixed axes. Use to test the founder's "어떻게 흡수하는지
  보자" thesis on any organ/task, or before claiming an OS adds value.
---

# AIOS Absorption-Delta Probe

The honest metric for "is AIOS real?" is behavior-delta: give a fresh frontier
model the same task with and without AIOS and measure how much its behavior
changes. Null delta on an organ = that organ is theater for that task class.
First run (2026-06-05) found delta concentrated in GenesisOS challenge while
MemoryOS retrieve added ~0 (empty graph) — see project_memoryos_inward_growth_finding.

## When to use

- Deciding whether an OS / organ is worth hardening or is decorative.
- Validating a claim that "AIOS helps" before acting on it.
- Periodic dogfood check that absorption is rising as the graph fills.

## Workflow

1. **Pick ONE real task** with a clear deliverable, ideally where prior context
   exists (so recall can matter) and a known failure is predictable.
2. **Spawn two isolated agents in parallel** (Agent tool), IDENTICAL task +
   IDENTICAL repo/web access. The ONLY variable is the organ loop:
   - **Arm-bare:** "Do NOT use any `aios_*` tools; repo files + web only."
   - **Arm-AIOS:** "First `aios_retrieve`, then `aios_challenge` your draft,
     then do the work, then `aios_observe`."
3. **Score behavior-delta on 5 axes:** ① prior-decision recall ② known-failure
   avoidance ③ provenance/guardrail compliance ④ artifact correctness/usefulness
   ⑤ continuity if the model were swapped. Attribute each delta to the organ
   that produced it.
4. **Verdict:** delta≈0 → that organ is theater (redesign / fill the gap it
   exposed). delta>0 → the mechanism that produced it IS the spec; harden it.
5. Feed the finding via `aios_observe`; if durable, [[aios-memory-propose]] it.

## Output template

```markdown
| axis | bare | +AIOS | delta | organ |
|---|---|---|---|---|
| recall | … | … | ≈0/+/− | MemoryOS/Genesis/Cap |
…
verdict: delta=<small/large>, concentrated in <organ>; <implication>.
```

## Hard rules

- **Hold repo access constant across arms.** If only Arm-AIOS can read the
  repo, you measure repo-reading, not absorption. Both arms read the repo;
  only the organ loop differs.
- **Use fresh isolated agents** — the current session is already organ-primed,
  so "bare me" is contaminated; spawn clean subagents.
- **Report honestly even if delta≈0.** A refuted "AIOS helps" hypothesis is the
  most valuable output — it names what to fix. Do not force the flattering story.

## Related

- `scripts/aios_memory_retrieval_audit.py` (the standing metric this probe seeds)
- memory project_memoryos_inward_growth_finding · feedback_observation_vs_verification
