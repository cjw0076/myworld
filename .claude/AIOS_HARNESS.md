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

A reusable **capability factory** (a generic pipeline → cheap to add new student
value tools), built 2026-06-05:

Pipeline = real-input → failover-routed local-gen → **deterministic-verify**
(LLM proposes, CODE checks the exact part) → GenesisOS gate → provenance receipt
→ personalize → measure. All on local substrate (free, private, churn-resilient).

Architecture (layered):
`aios_capability_dispatch.py` (operating layer — detects input → routes) →
4 capabilities (shared `aios_capability_base.py`: generate + write_receipt) →
`aios_substrate_router.py` (failover gate, local-first, no hard provider dep) →
local LLM. Plus `aios_value_ledger.py` (unified value signal across the family)
and `aios_copilot_serve.py` (HTTP delivery surface).

Capabilities (each = one domain prompt + one **deterministic verifier**; ~5-7 tests):
- `aios_deadline_copilot.py` — deadlines (.ics/CSV) → plan; verify = date-consistency. + per-student memory.
- `aios_grade_copilot.py` — grade CSV → recovery; verify = exact weighted-grade math.
- `aios_exam_copilot.py` — exam .ics → prep blocks; verify = prep-before-exam logic.
- `aios_tuition_copilot.py` — bursar CSV → cashflow; verify = payment/overdue math.

**To add capability #5**: import `aios_capability_base`, write a domain prompt +
a pure deterministic verifier (the trust anchor — LLM proposes, code checks the
exact part), emit a receipt, add a `detect_capability` branch. ~50 lines.
Production (uri UI, hive cron, MemoryOS-per-student) is deploy-target — see
AIOS_OUTSIDE_VALUE_HANDOFF + AIOS_DEADLINE_COPILOT.

## Security enforcement (absorbed from ironclaw peer Agent OS, 2026-06-07)

The Star Radar absorption (`aios_star_radar.py`) deep-read ironclaw and found AIOS
had DNA invariants but no security-ENFORCEMENT layer. Three primitives now exist
(defense-in-depth for the permissioned-head thesis):
- **`aios_secret_scan.py`** — scans staged changes / paths for leaked secrets
  (API keys, tokens, private keys, generic secret assignments; placeholders
  skipped, matches redacted). Exit 1 on findings → pre-commit-hook-able. (DNA #7)
- **`aios_prompt_guard.py`** — `detect_injection` + `sanitize_untrusted` for
  untrusted external text before it enters an LLM prompt. Wired into star_radar
  (GitHub descriptions are untrusted) — use it anywhere user/external text is embedded.
- **`aios_endpoint_policy.py`** — `is_allowed(url)` + `guarded_urlopen` restrict
  outbound HTTP to an allowlist (GitHub, localhost ollama). Wired into star_radar's fetch.
Next (Hive-owned): sandbox/capability-permissions for tool execution, credential
injection at the host boundary.

## Star Radar — ecosystem absorption organ

`aios_star_radar.py` tracks GitHub momentum → local-LLM distills idea + AIOS angle
→ draft-first candidates (operator promotes good fits to MemoryOS). dedup skips
already-seen repos. See memory reference_star_radar_absorption. Re-run periodically.

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
