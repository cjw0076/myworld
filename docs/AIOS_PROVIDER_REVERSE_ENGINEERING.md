# AIOS Provider & Peer Reverse-Engineering Asset

**Built**: 2026-06-08 (claude@myworld) by a 7-stream parallel research fan-out.
**Purpose**: turn the best provider agent CLIs and peer OSS into an AIOS
absorption corpus — *what design pattern, which AIOS OS owns it, what to build*.
Feeds ASC-0066 (provider-role distillation). Complements
`AIOS_PROVIDER_ABSORPTION.md` (the 6-stage absorption *process*); this is the
*source map* of what to absorb.

**Clean-room discipline**: every claim is summarized in our own words with a
cited source (official docs URL, repo@commit, or arXiv id). No verbatim copying.
Uncertainty is flagged. Sources read first-hand by the research agents:

| stream | source studied | as-of |
|---|---|---|
| Claude Code | docs.claude.com / platform.claude.com | 2026-06-08 |
| Codex CLI | `openai/codex@e648ec77` (codex-rs crates) + developers.openai.com/codex | 2026-06-08 |
| Gemini CLI | `google-gemini/gemini-cli@main` (packages/core) + docs | 2026-06-08 |
| oh-my-openagent | `code-yeongyu/oh-my-openagent@2f610b26` (61k★, omo) | 2026-06-07 |
| hermes | `NousResearch/hermes-agent@e3b8b6d` (186k★) | 2026-06-07 |
| capability routing | Anthropic tool-search docs, RAG-MCP (2505.03275), MCP-Zero (2506.01056), MCP Registry | 2026-06-08 |
| GenesisOS analogues | ToT (2305.10601), GoT, Gentner SME, Self-Refine (2303.17651), CreativityPrism (2510.20091) | 2026-06-08 |

---

## Part A — Convergent gaps (HIGHEST confidence: ≥2 independent sources agree)

When multiple independent provider CLIs all implement X and AIOS lacks it, X is a
real gap, not a preference. Ranked by source-convergence × leverage.

### A1. OS-level execution isolation (sandbox) — **hivemind** — 🔴 biggest gap
- **Sources**: Codex (`codex-rs/linux-sandbox`: bubblewrap+user-ns on Linux,
  Seatbelt `.sbpl` on macOS; network-off by default in workspace-write); Gemini
  (docker/podman or macOS Seatbelt, `GEMINI_SANDBOX`, per-tool isolation).
- **AIOS today**: `aios_adapters.py` runs providers via bare `subprocess.run` —
  **no namespace/seccomp/landlock isolation**. The named "missing real execution
  isolation". ironclaw (peer) also flagged this (WASM sandbox).
- **Absorb**: wrap every adapter subprocess in `bwrap --ro-bind / --bind
  <workspace> --unshare-net`, writable-roots = contract workspace only, bundled
  fallback + **fail-closed refusal** when namespaces unavailable. Network = explicit
  contract grant.

### A2. Capability × consent policy engine — **myworld kernel** authority gate
- **Sources**: Codex (orthogonal `sandbox_mode` × `approval_policy`; execpolicy
  Starlark `prefix_rule(allow/prompt/forbidden)` with load-time self-tests +
  justification surfaced); Gemini (`.toml` policy: toolName/commandPrefix →
  allow/deny/ask_user, priority-ranked); Claude Code (permission-mode spectrum
  plan/acceptEdits/auto/bypass).
- **AIOS today**: `aios_guard_hook.py` + `aios_boundary_classifier.py` are ad-hoc;
  no declarative, testable, priority-ranked rule file; no capability-vs-consent split.
- **Absorb**: ContractObject carries **both** `sandbox_mode` (what's possible) and
  `approval_policy` (when to ask), resolved to presets. A declarative `default.rules`
  (allow/prompt/forbidden + justification + `match`/`not_match` self-tests) evaluated
  pre-dispatch; justification → receipt.

### A3. Snapshot/rollback + resumable run log — **myworld kernel**
- **Sources**: Gemini (shadow-git at `~/.gemini/history/<hash>` snapshots
  files+conversation+pending-call before every mutation; `/restore`, tri-modal
  `/rewind`); Codex (rollout `.jsonl` sessions, `exec resume --last/<id>` with
  cwd/git/model metadata); omo (`boulder-state` resumable work tree: works→tasks→
  sessions w/ status/elapsed/worktree, crash-resume).
- **AIOS today**: `aios_contract_runner.py` has backup-manifest reversibility +
  append-only ledger, but the ledger is *inspectable, not replayable/resumable*, and
  there is no out-of-band shadow-git file snapshot.
- **Absorb**: before any runtime mutation, snapshot project state to `.aios/history/
  <sha>`; receipt stores the SHA → `aios rollback <receipt>`. Make per-run receipts
  append-only **resumable** JSONL (cwd/git/model) → `aios resume --last`. Tri-modal
  rewind (state / memory / both).

### A4. Headless structured-JSON agent protocol — **adapters / kernel**
- **Sources**: Codex (`exec --json` typed event stream thread/turn/item +
  `--output-schema` + exit codes 0/1/42/53); Gemini (`--output-format
  json/stream-json`, init/tool_use/tool_result/result events, exit 0/1/42/53).
- **AIOS today**: `aios_adapters.py` calls bare `gemini -p` / one-shot and scrapes
  stdout text — no structured events, no schema.
- **Absorb**: a uniform multi-substrate execution wire — adopt typed event +
  exit-code contract so receipts capture tool_use/tool_result *structurally* instead
  of scraping. Single protocol across claude/codex/gemini/ollama adapters.

### A5. Deferred/lazy tool loading + semantic tool search — **CapabilityOS**
*(the founder's ToolSearch intuition, confirmed)*
- **Sources**: Claude Code (Tool Search Tool: `defer_loading:true`, regex/BM25 over
  names, `tool_reference` expand inline, ~85% def-token cut; defers MCP tools past
  ~10k tokens); RAG-MCP (2505.03275: selection accuracy **collapses 90%→13.6%** as
  catalog grows past 30–50 tools; external vector index fixes it); MCP-Zero
  (2506.01056: active gap-declaration → hierarchical server-filter→tool-rank); Gemini
  (namespaced tools registry + `discoverMcpTools`); official MCP Registry (REST
  `GET /v0/servers?search=`).
- **AIOS today**: CapabilityOS `recommend()` returns full `card.to_json()` for every
  active card (bag-of-terms scoring); catalog **hardcoded** in `DEFAULT_CATALOG`,
  no discovery.
- **Absorb**: (1) **two-tier** `recommend()` returns lightweight refs →
  `expand(ids)` returns full cards on demand (mirrors `defer_loading`,
  recommendation-only preserved); (2) optional semantic retrieval over card text with
  **bag-of-terms kept as the deterministic offline fallback** (no-network invariant);
  (3) `discover` subcommand: MCP Registry → emit **draft `kind:"mcp"` cards**
  (`executes_tools:false`, status `planned`), never auto-bind.

### A6. Event-triggered draft-first memory consolidation — **memoryOS**
- **Sources**: Hermes (`on_session_end` `_auto_extract_facts`, `on_pre_compress`
  extract-before-summarize; never applied without review); Gemini (Auto Memory miner:
  idle transcripts → draft `.patch` + `SKILL.md` into inbox, **never auto-applied**).
- **AIOS today**: memoryOS write is manual; the graph-control dream-loop **only
  computes JSON snapshots**, never autonomously executes (the founder's stated gap).
- **Absorb**: wire session-end + pre-compress extraction hooks that emit **drafts**
  (makes the dream-loop autonomous *without* breaking draft-first — extracted facts
  are drafts, not accepted). A transcript→draft miner feeding the existing review queue.

### A7. Independent second-substrate verification before accept — **hivemind**
- **Sources**: omo (Ralph/ultrawork loop: independent **Oracle** skeptical pass before
  accepting `<promise>DONE</promise>`); convergent with AIOS's own
  `multi-substrate-review` skill.
- **AIOS today**: run receipts self-report; no *different-provider* skeptical gate at
  closeout.
- **Absorb**: a verify pass by a **different** provider before contract closeout —
  operationalize the multi-substrate-review skill as a harness stop condition.

---

## Part B — Per-OS absorption backlog (prioritized)

### myworld (kernel)
1. capability×consent declarative policy engine (A2) — **P0**
2. shadow-git snapshot + `aios rollback` + resumable JSONL (A3) — **P0**
3. uniform headless structured-JSON adapter protocol (A4) — **P1**
4. Skills-based contract registry — contracts as lazy-load runnable `/ASC-NNNN`
   runbooks with pre-blessed tools (Claude Code skills) — **P1**
5. permission-mode spectrum (observe/accept/sovereign) + safe-decision auto-classifier
   to cut founder escalations (Claude Code) — **P2**
6. context-budget dashboard + auto-digest of old ledger entries (Claude Code) — **P2**
7. OpenTelemetry spans per contract/tool (Gemini) — **P3**

### hivemind (execution)
1. OS-level bwrap/seatbelt sandbox + network-deny-by-default (A1) — **P0**
2. provider **fallback chains + category routing** (category→tier→fallback; omo,
   Gemini pro→flash) — **P1**
3. loop-detector / circuit-breaker as a named stop condition (omo; satisfies DNA #4) — **P1**
4. independent second-substrate verify before closeout (A7) — **P1**
5. `boulder-state` resumable work tree over `.runs/` (omo) — **P2**
6. preemptive compaction at context-fraction 0.78 (omo) — **P2**
7. per-provider concurrency limits + backpressure queue (omo) — **P3**

### memoryOS
1. event-triggered draft-first consolidation hooks (A6) — **P0** (autonomizes dream-loop)
2. **trust-as-feedback** loop: retrieval usefulness writes back to a confidence signal
   (Hermes `record_feedback`) — **P1**
3. **contradiction detection** dream-loop pass: MemoryObjects sharing entities but
   divergent claims → draft review (Hermes `contradict()`) — **P1**
4. temporal half-life decay `0.5^(age/half_life)` in retrieval scoring (Hermes) — **P2**
5. promote merge-candidate runs into draft "observation" MemoryObjects (Hermes
   Hindsight 3-tier) — **P2**
6. short-lived `working` memory tier with TTL eviction feeding consolidation — **P3**
7. hierarchical context-file layer (global/project/JIT) + `@`-import (Gemini GEMINI.md) — **P3**

### CapabilityOS
1. two-tier `recommend()`+`expand()` deferred loading (A5) — **P0**
2. MCP-registry `discover` → draft cards, audit-gated (A5) — **P1**
3. semantic retrieval w/ bag-of-terms offline fallback (A5) — **P1**
4. recency-weighted observation decay + "recently failing" reason code (router
   registries) — **P2**
5. live server-prefixed tool **registry** with conflict resolution, recommendation-only
   preserved (Gemini tools-registry) — **P2**
6. emit `tool_reference`-shaped recs so Claude Code/MCP can consume CapabilityOS as its
   retriever — **P3**

### GenesisOS (the "score, don't just generate" upgrade)
1. **divergence-quality verifier** (quality×novelty×diversity; CreativityPrism /
   NoveltyBench) — every ToT/GoT/Nova peer pairs generation with a scorer, GenesisOS
   has generation only — **P0**
2. replace analogy lookup with **Gentner Structure-Mapping** (relational alignment,
   not keyword) — converts detector → genuine cross-domain *transfer engine* — **P1**
3. contradiction-conditioned operator firing (TRIZ): select mutation axes by detected
   prison signature, not blanket — **P1**
4. optional local-qwen3 LLM-in-loop **branch generator**, deterministic scorer gates it
   (LLM proposes, code judges — keeps `speculative_only` DNA, avoids self-refine
   degradation) — **P2**
5. Reflexion loop over the seed `library` (bury/revive) → learns which divergences paid
   off across sessions — **P2**

---

## Part C — Cross-cutting reading

- **The pattern AIOS already does better**: draft-first review (no auto-accept) is
  rare in peers — Hermes/Gemini Auto-Memory both *converged on it independently*
  (draft inbox, human accept), validating DNA invariant 2. CapabilityOS's
  machine-enforced `audit` (block `executes_tools==True`) has no peer equivalent.
- **The patterns AIOS is behind on**: execution isolation, declarative policy,
  resumable/replayable runs, deferred tool loading, scored divergence. All are
  *mechanism* gaps, not *philosophy* gaps — AIOS's governance frame is sound; the
  kernel/harness plumbing is immature.
- **Uncertainty flags carried from sources**: Gemini Auto-Memory / local-Gemma routing
  / tool-sandbox are marked experimental (APIs churn — `--checkpointing` was removed in
  0.11.0). Multi-agent-debate gains are empirically fragile (2511.07784) — borrow the
  loop *structure*, not the objective. omo gap-claims were vs the task brief, not a
  direct `harness.py` checkout — confirm before building hivemind changes.

---

## Provenance
Research fan-out receipts: 7 background agents, 2026-06-08. This doc is the operator
synthesis; the per-source raw asset tables live in the session transcript. Absorption
of any item follows `AIOS_PROVIDER_ABSORPTION.md` (Evidence→Registry→Card→WorkerSpec→
Observation→MemoryDraft) and remains recommendation-only until an operator/contract
accepts it.
