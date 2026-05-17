# AIOS Ecosystem Borrow Plan

Synthesis of `CLAUDE_CODE_ECOSYSTEM.md` + `CODEX_CLI_ECOSYSTEM.md` into a
prioritized plan for what AIOS imitates from the two leading provider-CLI
ecosystems — so a **local-LLM-based AIOS ecosystem** can follow them and
claim the "first" title.

Founder directive (2026-05-17): dissect global Claude Code / Codex CLI;
document everything borrowable; specify how user conversation logs reach
MemoryOS and become Hive/AIOS work; embed it all into MemoryOS.

## Positioning — symbiosis, not competition

AIOS does **not compete** with Claude Code / Codex CLI. It is a symbiotic
layer (상생): the provider CLIs remain the strongest executors, and AIOS
wraps them — giving their one-shot execution continuity, memory, governance,
and recovery. AIOS already does this concretely (provider reroute across
CLIs, not avoidance — ASC-0096/0100). Borrowing from their ecosystems is
learning from peers in a shared space, not taking share from rivals.

Claude Code and Codex CLI are *agentic harnesses* — the platform value is in
the harness (the turn loop, config layering, context economy, on-disk
formats, extension standards), not the model. Both ration their best
subsystems (reviewer subagent, memory distillation, divergence) behind a
hosted, metered model.

AIOS's distinct contribution is the same harness idea extended with
**provider sovereignty** and a **trajectory toward local LLMs**: the
ecosystem keeps running on a local model with no API or account dependency.
This is additive — it does not displace the provider CLIs; it extends
coverage to where a provider is unavailable, unwanted, or too costly. The
trajectory: from [single model — many functions] toward
[many specialized models — many functions], spreading to local LLMs. What
Codex/Claude ration behind a metered model, AIOS can also run continuously
and free on a local model — that is the always-on dream cycle. Copy the
structure; the local-LLM economics make new things possible, alongside the
provider CLIs, not against them.

## Tier 1 — borrow now (closes a known AIOS gap)

| Borrow | From | Closes |
|---|---|---|
| **Hooks as deterministic enforcement** — a PreToolUse-style layer that hard-blocks actions regardless of model intent | Claude Code | ASC-0122 "policy spec without enforcement" — makes DNA invariants *binding*, not advisory |
| **Leased jobs queue** — `kind` + `job_key` + `lease_until` + `retry_remaining` + `ownership_token` | Codex | the watcher-race / ID-collision bug class ([[feedback_id_collision_pattern]], ASC-0059) |
| **JSONL = truth, SQLite = rebuildable index** — canonical append-only log, derived fast index, no truth living only in SQLite | both | makes `dispatch status` fast without risking the append-only-audit invariant |
| **Deferred / searchable tools** — tool schemas load on demand, only names resident | Claude Code | a small-context local LLM cannot hold 50 tool defs; essential for AIOS-on-local-LLM |
| **Context anti-thrash circuit breaker** — stop after N failed compactions; evict tool output before summarizing | Claude Code | local LLMs hit the context wall far sooner |

## Tier 2 — borrow next (strengthens an invariant)

- **Per-turn `turn_context` record** (model/effort/sandbox/approval/cwd
  serialized every turn) → AIOS work packets become fully replayable,
  strengthening the provenance-chain invariant.
- **Two-layer security model** — separate *sandbox* (technical capability)
  from *approval policy* (when to pause). AIOS conflates both in contract
  status; split them.
- **`rules` prefix-allowlist** — mechanize past human approvals into a
  persistent rule ledger; cuts repeated escalation noise.
- **Reviewer subagent** (`auto_review`) — Codex turned the human approver
  into a model. AIOS runs this as a local-LLM critic (GenesisOS / Hive),
  operator override preserved.
- **`thread_spawn_edges` lineage graph** — explicit parent→child spawn tree
  for GenesisOS branches and child-repo dispatch.
- **`thread_goals` with token/time budgets** + a `budget_limited` status →
  every AIOS contract gets a named loop exit backed by real accounting.
- **CLAUDE.md re-injection after compaction** — AIOS should re-inject the
  active contract the same way, so continuity survives context loss.

## Tier 3 — ecosystem / platform moves (the "first" title)

- **Skills as an open standard** — directory + YAML frontmatter (description
  = trigger) + lazy-loaded body + `!`shell-injection. AIOS contracts /
  playbooks / primitives should adopt this shape and stay cross-compatible
  with the Agent Skills standard.
- **Speak open standards at the seams** — MCP + Agent Skills. AIOS already
  ships an MCP server; staying standard-compatible is what makes it an
  *ecosystem* others can plug into.
- **Publish the harness as an SDK**; standardize extension formats with a
  documented precedence order; ship a plugin/marketplace surface.
- **Subagents** — fresh isolated context, summary-only return, no nesting,
  cheap-model routing for Explore-type work → formalize for AIOS dispatch.

## Conversation log → MemoryOS → Hive/AIOS pipeline

Founder's explicit ask. Both CLIs persist sessions as append-only JSONL:

- **Claude Code**: `~/.claude/projects/<slug>/<session>.jsonl` — a DAG of
  records (`uuid` + `parentUuid`), large tool outputs spilled to sidecar
  `tool-results/` dirs.
- **Codex CLI**: rollout JSONL + a derived `state_*.sqlite` index;
  per-turn `turn_context`.

The AIOS pipeline (extends the existing `aios_ingest_conversations.py`):

1. **Capture** — watch the provider transcript dirs; treat each session
   JSONL as a source. (Privacy boundary: never ingest `_from_desktop`,
   `dain`, `minyoung`, secrets — Invariant 7.)
2. **Import as drafts** — each session → MemoryOS draft MemoryObjects,
   provenance-stamped with the source path/uuid. Draft-first: no
   auto-accept ([[feedback_no_auto_accept]]).
3. **Distill** — staged pipeline (Codex's model): raw rollout → stage-1
   distillation → usage-weighted selection → phase-2 promotion. The
   usage-weight signal is a concrete MemoryOS auto-writeback trigger.
4. **Embed** — `memoryos embed` makes the distilled memory semantically
   retrievable (dream phase 1; coverage now 100%).
5. **Become Hive/AIOS work** — a recurring pattern surfaced from the logs
   becomes a dream open-question → contract → dispatch. Conversation logs
   thus feed the autopoietic loop, not just an archive.

`writable_roots` (Codex) is the security pattern: sandbox everything, punch
one hole for the memory directory — a safely self-writing memory.

## Routing

- Tier 1 items each warrant a contract (hooks-enforcement and the leased
  jobs queue are the highest value — they close named bug classes).
- This plan + both ecosystem docs are embedded into MemoryOS so the borrow
  decisions are retrievable in future dream cycles.
