# AIOS Design Re-validation — 2026-07-02

> Founder directive: *"AIOS에 대해 이 설계가 맞는지부터 다시 재검증하는 시간이 필요해.
> Claude, Codex, Agy, local llm, 26년 7월 기준 최신동향 consensus, github, reddit, x 등
> 방대하게 찾아보기."* This document is the result: the five core design bets, each
> triangulated across independent lanes, with disagreements surfaced (not averaged away)
> and a final synthesized verdict per bet. Everything cited is from live 2026-07-02
> sources or retrieved papers — not model priors.

## Method

| Lane | Substrate/source | Status |
|---|---|---|
| Landscape | live web + GitHub API + HF (agent sweep) | ✅ full report |
| Academic | Consensus + arXiv + HF papers (agent sweep) | ✅ full report, ~40 papers |
| Community | HN Algolia + Reddit (5 subs) + provider blogs; X unreachable (noted) | ✅ full report, ~400 comments |
| Gemini (agy/Antigravity) | adversarial Q1–Q5 review | ✅ full review |
| Local qwen3-coder:30b | adversarial Q1–Q5 review | ✅ (weight: stale-knowledge substrate) |
| Codex | adversarial Q1–Q5 review | ❌ FAILED — context overflow during its own evidence sweep; no substantive output |
| Claude (this doc) | synthesis + disagreement adjudication | this document |

Raw artifacts: scratchpad `critique_agy_full.md`, `critique_qwen.txt`, `signals/`; the two
agent reports are reproduced in the session record. Design brief with Q1–Q5:
`design_brief.md` (same scratchpad).

---

## Verdict per design bet

### Bet ① — "Local-first memory layer for AI agents" (positioning)

- **Landscape:** WEAKENS. The generic slot is commoditized: Mem0 (59.9k★, $24M, AWS
  Agent SDK exclusive), Zep/Graphiti (28k★), Cognee (26k★), plus a dozen 10k★+ 2026
  entrants — EverOS (10k★) occupies the *exact* "local-first, user-owned, portable"
  wording. Provider-native memory shipped everywhere: Claude Code auto-memory + **Anthropic
  "Dreaming"** (2026-05: managed agents review their own sessions and write playbooks —
  our thesis, executed inside the provider), Codex CLI Memories (default-on), Gemini
  Memory Bank, Cloudflare Agent Memory.
- **Community:** SUPPORT, narrowed. The pain is consensus-real ("amnesia across agent
  sessions… wastes time and tokens"). Local-first distrust of cloud memory is strong in
  the CLI-power-user segment. But "another memory layer" is a hostile, saturated market;
  the community's loudest demand is **"evals or it didn't happen"** ("memory arena",
  "no benchmarks = FOMO").
- **Gemini/qwen:** commoditized; reposition.

**SYNTHESIS: NARROW, don't abandon.** "Memory layer" alone is dead as a differentiator.
The defensible position is the *conjunction* no incumbent occupies:
**cross-CLI portable** (provider memory is locked to one CLI; multi-CLI fleets are now
normal) + **white-box, user-owned** (the #1 complaint about provider memory is black-box
non-portability) + **behavioral — what worked, not facts** (Mem0-class stores facts;
practitioners explicitly ask for pattern/correction learning: "user corrections are the
highest-signal data — I cannot understand how this hasn't been capitalized on") +
**published controlled evals** (the community's scarcest asset; we have the only
pre-registered ledger A/B with an honest negative). Each leg is evidenced; together they
are a real, unoccupied position.

### Bet ② — Behavioral-signature primitive (tool-names-only)

- **All six voices agree on one thing:** tool-names-ONLY is signal-starved. Academic: no
  paper tests this granularity (absence in both directions); every published winner
  (ReasoningBank +8.3 abs / AWM +51% rel / Memp / AFTER 73.1% cross-model) keeps semantic
  content; SkillEvolBench shows even distilled skills lose to raw trajectories when
  context is discarded. Landscape: nobody ships tool-names-only; ECC "Instincts"
  (content-rich behavioral patterns) owns the mindshare. Gemini: "zero semantic
  grounding… framework lock-in (tool names differ per harness)". Our own A/B: signal
  exists (pass@1 +15pp) but is thin and brittle under feedback.
- **But the DIRECTION is validated and demanded:** academic weight favors
  pattern/procedure/strategy-level memory over trajectory dumps for transfer
  (2604.27003: "abstract procedural memories transfer more reliably"); compactness is
  independently justified (context length alone hurts 13.9–85%); practitioners
  independently converge on "I only track decisions, actions, and outcomes — not RAG".
- **The unification (Claude synthesis):** the content-stripping existed to make the
  PUBLIC pool safe. Kill/park the public pool (bet ④) and the constraint dissolves:
  **local memory can be content-rich** (decisions, corrections, outcomes, what-worked
  notes — OKF-style markdown, draft-first) because privacy is preserved by *locality and
  user ownership*, not by stripping. Tool-sequence signatures survive as what our A/B
  showed they are: a cheap **attempt-1 routing prior**, not the memory unit.

**SYNTHESIS: ADJUST.** Keep behavioral memory as the category (right bet, early). Enrich
the local payload to decisions/corrections/outcomes with content (draft-first review,
OKF-compatible format). Demote tool-name signatures to routing-prior. Injection policy:
attempt-1-only (our own measured correction, mechanism confirmed by
sycophancy/experience-following/SteeM literature — and the exact experiment is
unpublished: **write it up**).

### Bet ③ — Integration point (wrapping provider CLIs)

- **Landscape (live data):** SUPPORTS — the sidecar/harness-wrap pattern *won* (OpenClaw
  CLI backends, ruflo 62k★ "meta-harness", ECC 224k★, and **Letta pivoting its company
  onto exactly this architecture** via claude-subconscious: 4 Claude Code hooks + stdout
  injection). The durable seams are **hooks + MCP + ACP** (Agent Client Protocol), not
  raw subprocess wrapping.
- **Gemini/qwen:** "kill CLI wrapping — brittle, MCP won." **Adjudication:** this attacks
  a strawman (PTY hijacking / stdout parsing). AIOS's actual integration is already
  hooks + MCP server + static context injection — the exact converged pattern the live
  data confirms. The criticism is right only about any residual subprocess-wrap paths.

**SYNTHESIS: KEEP, formalize.** Name the integration surface as hooks+MCP(+ACP — new
adapter needed); deprecate/retire any remaining subprocess-wrapping in the product story.
The threat here is crowding (Letta subconscious is a funded company on our architecture),
not wrongness — which makes speed and the eval asset matter more.

### Bet ④ — Cross-user shared behavioral ledger (AkashicRecord)

- **Community:** WEAKEN→KILL as product. Zero observed demand for cross-USER pooling in
  ~400 comments ("I don't even want a shared agent memory" went unrebutted); the Go
  telemetry precedent predicts exactly our cold-start (opt-in → sparse, biased data;
  1.5k/10k entries); memory-poisoning is now OWASP-ranked, so "public writable memory
  pool" reads as an attack surface. Real, repeated demand exists for **team-scoped**
  sharing — currently solved with git+markdown.
- **Academic:** MIXED-risky. Pooling works when curated (SkillClaw cross-user skill
  evolution; Fed-SE +18%; CoPS with distribution-matched selection) — but benign
  cross-user shared state contaminates 57–71% with silent failures; decentralized
  per-agent memory *beats* centralized pooling by up to +23.8%; poisoning
  (AgentPoison→MemoryGraft→Zombie Agents) is first-order. All published wins share
  content-richer artifacts than tool names.
- **Landscape:** the position is genuinely unclaimed (nobody shipped a public pool) and
  freshly evidenced as a research direction (Spark 2511.08301, MATM, FederatedSkill).

**SYNTHESIS: KILL as the product thesis; PARK as a research lane; PIVOT the sharing story
to team-scope.** The Merkle/k-anon/draft-first governance work transfers almost verbatim
to **team-scoped, git-native, verifiable shared memory** — where the demand actually is.
The GIMPS network-effect framing comes OUT of the README's value story (it may return if
the research lane earns it).

### Bet ⑤ — Safety/governance DNA (draft-first, append-only, recommendation-only, white-box)

**UNANIMOUS DOUBLE-DOWN — the strongest asset.** Gemini: "excellent… double down." The
academic harm literature (error propagation, memory anchoring, tool-drift, interference,
poisoning) maps one-to-one onto the DNA's protections; the community's top fears (bloat,
wrong recalls, staleness, black-box) are exactly what draft-first + white-box +
user-owned answers; "we should be able to make our machines *unlearn* easily" is our
review lifecycle. This is also the moat provider memory does not offer (black-box).

---

## Cross-cutting findings

1. **The eval asset is the wedge.** The community's most-repeated demand ("memory arena",
   "clean-slate control", "no benchmarks = FOMO") is the thing we uniquely have: a
   pre-registered controlled A/B with an honest negative and a named injection-policy
   correction. The academic lane confirms the anchoring mechanism is known but our exact
   experiment is unpublished. **Lead the product story with measured evidence; publish
   the injection-timing result.**
2. **Distribution is the decisive gap** (landscape): every winner won via a zero-config
   channel (AWS SDK, plugin marketplace, npm, cloud onboarding). AIOS has no equivalent
   install-to-value channel. A Claude Code plugin/hooks package + MCP server listing is
   the shortest path.
3. **Convergences we already own:** OKF (markdown+frontmatter memory standard) ≈ our
   file-based memory + auto-memory format; Anthropic "Dreaming" ≈ our dream cycle
   (validation of the idea; threat to the position); SuperLocalMemory (arXiv 2603.02240)
   is the closest published peer — required reading.
4. **Substrate disagreement log** (kept, per multi-substrate discipline): Gemini/qwen
   said "kill CLI wrapping" — overruled by live landscape data + misread of our actual
   seams. qwen said "kill local-first framing" — overruled by community segment data.
   No lane defended tool-names-only or the public pool; those verdicts are unanimous.

## What this means (recommended redesign, pending founder GO)

1. **Sharpen identity** to the conjunction: *"the white-box, cross-CLI memory layer that
   learns what worked — and proves it with published evals."* (README/NORTHSTAR/banner
   already memory-led; this is a sharpening, not a rewrite.)
2. **Enrich local memory payload** (decisions/corrections/outcomes, content-rich,
   draft-first, OKF-compatible); demote tool-signatures to attempt-1 routing prior.
3. **Retire the public-pool headline**: AkashicRecord → research lane + team-scope pivot;
   update README's contribute section accordingly.
4. **Formalize integration = hooks + MCP + ACP**; ship the zero-config Claude Code
   plugin/hooks package as the distribution channel.
5. **Publish the injection-timing experiment** (arXiv-able; community-credible).
6. Keep and market the DNA (white-box, draft-first, unlearn-able) as the moat.

*Every claim above is traceable to the lane reports; disagreements were adjudicated with
live data, not averaged. Codex lane failure is recorded honestly (no substantive output).*
