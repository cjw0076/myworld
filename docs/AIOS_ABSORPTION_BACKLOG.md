# AIOS Absorption Backlog — ecosystem ideas → AIOS development

Operator digest of what Star Radar (`scripts/aios_star_radar.py`) absorbed from the
GitHub ecosystem on 2026-06-07, turned into a prioritized AIOS development backlog.
Each was reviewed and accepted into MemoryOS (draft-first). "흡수" = the idea drives
AIOS development, not just a note.

## Built this session (absorption → shipped capability)

| absorbed idea | source | AIOS evolution built | tests |
|---|---|---|---|
| security enforcement (sandbox, credential isolation, prompt-injection, endpoint allowlist) | **ironclaw** (peer Agent OS) | `aios_secret_scan` (blocks high-confidence secrets at commit), `aios_prompt_guard` (sanitize untrusted LLM input), `aios_endpoint_policy` (outbound allowlist) | ✓ |
| shareable installable .claude skill collections | **mattpocock/skills, gstack, antigravity** (100k+★ trend) | `aios_skill_catalog` (unified CapabilityOS index of all 59 workspace skills) | ✓ |

## Backlog (absorbed, mapped to AIOS, not yet built — operator/founder to prioritize)

| absorbed idea | source | concrete AIOS action | size |
|---|---|---|---|
| **self-evolving skills** (eval→improve→test→keep/rollback) | darwin-skill | CORRECTION (verify-before-building): AIOS **already has** `scripts/aios_self_evolve.py` — a per-specialist organ that distills VERIFIED-GOOD invocations into a principles file, with the critical no-self-distillation safety (never evolve from a helper's own raw output). darwin-skill's contribution is the explicit propose→test→**keep/rollback A/B** (variant vs current, keep the strictly-better) — an ENHANCEMENT to the existing organ, not a missing capability. Parametric (LoRA on the verified set) is the named follow-on. | S |
| **benchmarked memory system** | MemPalace (~54k★) | benchmark MemoryOS against MemPalace; run the retrieval-research-cycle vs it; study its patterns while keeping AIOS active-graph + draft-first differentiators. | S |
| **queryable knowledge graph from code/docs** | graphify (~60k★) | adopt queryable cross-source graph patterns in MemoryOS (aligns project_lgm_memory_thesis). | M |
| **installable cross-platform skill library** | antigravity (~39k★) | make the skill catalog installable into other agent CLIs' `.claude` (next step after the catalog). | M |
| **agent-management platform / work-history** | paperclip (~69k★) | a work-history memory surface + agent orchestration view (apps/control roster). | M |
| **single-GPU agent research loop** | karpathy/autoresearch (~85k★) | run research/eval agents on the local dual-5090 via Hive. | M |

## Process note

The local-LLM distiller mis-called darwin-skill "low fit"; **Claude-verify overrode
it** (the absorption pipeline's mandatory verify step — never act on unverified
substrate output). Re-run the radar periodically (dedup surfaces only new repos);
promote genuine fits via /aios-memory-propose.
