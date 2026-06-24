# Changelog

All notable changes to AIOS (`aios-os`). Format: themed summaries per release.
Tag `vX.Y.Z` → `publish.yml` builds + publishes to PyPI.

## [0.2.0] — 2026-06-24

The "one foundation" release: a research-backed reliability core, two unifying
spines, a real brand + CLI, and the seeds of parameter-level self-improvement.
~147 commits since 0.1.0.

### Reliability — research-backed turn-loop (arXiv 2509.09677 / 2604.11978)
- Self-conditioning defense: old error traces compressed so the model doesn't
  err more after seeing its own mistakes.
- Horizon-aware routing: long/multi-step tasks → reasoning model (qwen3:30b-a3b),
  short tasks → fast model.
- Execution-time plan verify+repair: stall → forced re-plan (process-level failures
  are 72.5%).
- Long-range constraint re-surfacing from MemoryOS during a run.

### Architecture — condensation to one foundation
- One capability spine (`aios_routing`): classify_horizon / select_model_by_horizon /
  classify_domain / executable_clis — one routing brain.
- One memory spine (`aios_memory`): retrieve / memoryos_context (single MemoryOS call)
  / contribute_run (single ledger write) + sparse domain activation at runtime.
- Runner unification: the 4 pillars apply on both head and harness paths; shared
  render_directives + decondition_history in the kernel turn-loop.

### Onboarding & absorption
- `aios onboard`: one-shot absorb (device LLMs + agent CLIs) → classify usable →
  e2e verify → manifest; CLI + MCP tool. Surfaces hippocampal-capture status.
- Absorb→use closed: grok adapter; onboard derives executable providers from the
  adapter registry. Capability scan runs at install.

### Brand, marker & CLI design
- Brand identity (Cosmic Ledger) + presence sigil `✦` / marker `✦ aios`
  (`aios_sigil`), single source.
- CLI design system (`aios_cli_style`) applied to real terminal output.
- `aios cli` — interactive runtime shell (`✦ aios ›`).
- Ambient presence: every AIOS-wired session opens with `✦ AIOS active`.
- Tightened CLI surface (grouped help), graceful `serve` port-in-use, `discover`
  default root, silent-no-op fix (provider fallback).

### Self-improving (CLS) — foundations
- CLS architecture plan (`docs/AIOS_SELF_IMPROVING.md`): hippocampus + dream +
  (frontier) neocortical fine-tune.
- Sub-agent / sidechain recognition + provider-feature capture in session ingest.
- Domain tools (FinanceMind/HRMind/LogisticsMind/…) wired into routing.

### Fixed
- Numerous robustness fixes surfaced by per-command verification (env-artifact vs
  code-regression isolation). Full suite green: 1258 passed.

## [0.1.0]
- Initial AIOS: kernel head, 5-OS organs, AkashicRecord ledger, behavior predict,
  install.sh, Docker, PyPI packaging.
