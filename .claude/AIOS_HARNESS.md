# AIOS Operator Harness (myworld)

Packaged operator rituals so neither human nor agent re-derives them or repeats
known mistakes. Each skill below encodes a ritual + its gotchas. Invoke with
`/<name>`. (Source of the repeated-mistake list: `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`.)

| skill | fires when | kills which repeated mistake |
|---|---|---|
| **`/aios-decide`** | before any non-trivial decision (contract, pivot, dispatch) | the 4-OS query getting silently skipped ("이번도 skip — 반복 gap") |
| **`/aios-memory-propose`** | a durable fact worth remembering (recall returned null) | raw `.memlang` → 0 blocks; silent/bulk auto-accept (DNA inv. 2) |
| **`/absorption-probe`** | "does this OS/organ actually help?" | claiming AIOS helps without measuring; faith over evidence |

## Standing checks (run, don't trust prose)

- **Commit guard:** `python scripts/aios_commit_guard.py` (run with staged
  changes) — catches an embedded git repo staged as a gitlink with no
  `.gitmodules` entry (broken submodule on clone) and 0-byte junk files like
  `0`. Both bit us this session. Non-blocking by default; wireable as a git
  pre-commit hook (`git config core.hooksPath`) once the operator opts in.
- **Inward-growth alarm:** `python scripts/aios_memory_retrieval_audit.py` —
  product-domain memory coverage + `inward_growth_alarm`. Accepted memory that
  is 100% AIOS-internal = retrieve returns null on real work.
- **CLI-surface vs filesystem:** when a status CLI looks stale for ≥2 cycles,
  `ls` the artifact path before assuming failure (self-obs: desynced 19 cycles).
- **Edit race with codex:** on "modified since read", re-Read fresh tail then
  re-Edit (recurring concurrency mistake).
- **ID collision:** claude/codex can mint the same ASC/URI-NNN; first-commit-wins,
  renumber loser (memory feedback_id_collision_pattern).

## Operator discipline (carried, not re-derived)

- 5 modes per turn: observe / verify / decide / intervene / escalate — surface on change.
- Persistent state-delta Monitor + ScheduleWakeup heartbeat when actively operating.
- Append a self-observation entry at session end (ASC-0066 corpus).
- Carry reversible risk decisively; escalate only irreversible + privacy.

## Growing this harness

New repeated task or mistake → add a skill here (match `.claude/skills/devil-advocate`
format), list it in the table, and link the self-obs entry that motivated it.
Forms: skill (ritual) · slash command · hook (enforce, can't be skipped) · MCP (tool surface).
