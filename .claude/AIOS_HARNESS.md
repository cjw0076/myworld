# AIOS Operator Harness (myworld)

Packaged operator rituals so neither human nor agent re-derives them or repeats
known mistakes. Each skill below encodes a ritual + its gotchas. Invoke with
`/<name>`. (Source of the repeated-mistake list: `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`.)

| skill | fires when | kills which repeated mistake |
|---|---|---|
| **`/aios-decide`** | before any non-trivial decision (contract, pivot, dispatch) | the 4-OS query getting silently skipped ("이번도 skip — 반복 gap") |
| **`/aios-memory-propose`** | a durable fact worth remembering (recall returned null) | raw `.memlang` → 0 blocks; silent/bulk auto-accept (DNA inv. 2) |
| **`/absorption-probe`** | "does this OS/organ actually help?" | claiming AIOS helps without measuring; faith over evidence |
| **`/local-llm-agent`** | offload gen/bulk/private work to a local model | ignoring the dual-5090 box; reinstalling already-present ollama |
| **`/multi-substrate-review`** | review own work / consequential decision | solving from one frozen model; acting on unverified substrate output |

## Outside-value capabilities (the override's goal — AIOS produces external value)

The first end-to-end outside-domain value loop, built 2026-06-05 (panel #1–#3):
- `scripts/aios_deadline_copilot.py` — student assignments → failover-routed local
  gen → deterministic date-verify → GenesisOS critique → provenance receipt.
- `scripts/aios_substrate_router.py` — provider-failover gate: ordered substrate
  chain (local-first), falls back on failure, records served substrate + trail
  (the moat: survive provider churn, no hard dependency).
- `scripts/aios_value_ledger.py` — aggregates receipts into a value signal
  (verify-pass rate, genesis rate, substrate mix, churn fallbacks).
Pattern = produce → resilient → verify → measure, all on local substrate. The
production flow belongs in uri/hivemind; these are the control-plane proofs.

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

## Known gaps (external review, gemini 2026-06-05 — codex was rate-limited)

Cross-substrate review of this harness (per feedback_use_all_substrates_not_own_head)
surfaced gaps Claude missed. Done: hook made active (live state injected via
`scripts/aios_session_brief.sh`); commit-guard junk detection broadened.

**ENFORCEMENT (done — founder: "진짜 AIOS를 위해서 모든 리스크 감수"):** the
harness is no longer advisory prose. `scripts/aios_guard_hook.py` is a
PreToolUse hook (matcher `Bash|Write`) that BLOCKS:
- a `git commit` when `aios_commit_guard` finds an ERROR (gitlink-without-submodule);
- creating a contract (`Write` to `docs/contracts/ASC-*.md`) until a fresh 4-OS
  ritual token exists (`aios_ritual_gate.py record`, done by `/aios-decide`).
It FAILS OPEN on any internal error (a hook bug never freezes work). Edits to
existing contracts (status flips) are not gated — only `Write` creation is.

Done (codex review, 2026-06-05): raw-diff parser handles rename/copy + full
status token; `.gitmodules` quote-stripping (was a false-block bug); contract
gate also covers Bash shell-writes. Done (memory audit): `provenance_integrity`
check flags accepted memory whose DURABLE evidence file is gone (ephemeral run
artifacts skipped; resolves against ROOT + parent + sibling repos).

**Hook-authoring hazards (learned the hard way, 2026-06-05 — a live hook blocked
the session twice):**
- Hook `command` MUST use an absolute path (`$CLAUDE_PROJECT_DIR/...`) and end
  with `|| true` — a relative path breaks when the shell cwd drifts, and a
  launch failure (exit≠0) BLOCKS the tool (the script's internal fail-open does
  not help if the script never launches).
- Keep deny heuristics TIGHT. A broad `>` match false-blocked any command that
  merely mentioned a contract path while using `2>/dev/null`. Match the write
  TARGET, not any write char.

Open: no binary/large-blob accidental-commit check in commit_guard.

## Growing this harness

New repeated task or mistake → add a skill here (match `.claude/skills/devil-advocate`
format), list it in the table, and link the self-obs entry that motivated it.
Forms: skill (ritual) · slash command · hook (enforce, can't be skipped) · MCP (tool surface).
