---
name: multi-substrate-review
description: >-
  Fan a review/decision/draft out to multiple heterogeneous LLM substrates
  (codex, gemini, local qwen3-coder) in parallel, then Claude-verify and
  synthesize — never solve from one frozen model. Packages the cross-substrate
  pattern proven repeatedly on 2026-06-05 (gemini + codex found real bugs Claude
  missed; routing by measured accuracy). Implements feedback_use_all_substrates_not_own_head.
---

# Multi-Substrate Review / Fanout

The most-repeated high-value move this operator makes: get ≥1 NON-Claude
substrate to independently review/attempt something, then verify and synthesize.
A single frozen model can't surprise itself; heterogeneous substrates catch each
other's blind spots. This skill is that pattern, packaged.

## When to use

- Reviewing your OWN work (code, design, contract) before it lands — you are the
  worst reviewer of your own output.
- Any consequential decision/claim where one model's confidence is a risk.
- Generating N independent attempts to synthesize the best.

## The substrates (verified available 2026-06-05)

| substrate | invoke (read-only / non-interactive) | strength | accuracy on code-AUDIT |
|---|---|---|---|
| **codex** (gpt-5.5) | `codex exec -s read-only --skip-git-repo-check "PROMPT"` | reasoning, audit | HIGH (found 3 real bugs Claude missed) |
| **gemini** | `gemini -p "PROMPT" --approval-mode plan` | audit, breadth | HIGH (found the enforcement gap) |
| **qwen3-coder:30b** (local) | `hivemind/.local/ollama/bin/ollama run qwen3-coder:30b "PROMPT"` or `:11434/v1` | gen, tool-use, bulk, private | LOW (4/5 false positives — see [[local-llm-agent]]) |

Routing rule (measured): **audits/reviews → codex &/or gemini; generation/draft/
bulk/private → local qwen3-coder.** Always Claude-verifies every substrate's
output — substrates propose, Claude disposes.

## Workflow

1. **Frame one sharp prompt** — concrete target, "find what I missed", bounded
   output (e.g. "max 5 findings, one line each, cite file:line, real issues only").
2. **Fan out in parallel** (independent Bash calls in one message; codex/gemini may
   rate-limit — that's fine, use whoever returns):
   - codex: `codex exec -s read-only --skip-git-repo-check "<prompt + file contents>"`
   - gemini: `gemini -p "<prompt>" --approval-mode plan`
   - (optional) local: `ollama run qwen3-coder:30b "<prompt>"` for a cheap third take.
3. **Claude-verify each finding against the actual source** — reject false
   positives (substrates hallucinate; on 2026-06-05 codex was ~3/4 right, qwen ~1/5).
   Verifying is mandatory; do not act on unverified substrate output.
4. **Synthesize**: act on the confirmed findings; record rejected ones + why.
5. Feed the substrate-accuracy data point via `aios_observe` so routing improves.

## Hard rules

- **Never skip the Claude-verify step** — a substrate's finding is a hypothesis,
  not a fact. Most damage comes from acting on a confident-but-wrong claim.
- **Read-only postures** (`-s read-only`, `--approval-mode plan`) — reviewers
  must not edit.
- **Don't block on one substrate** — codex/gemini rate-limit; proceed with what
  returns, note who was unavailable (no silent coverage gaps).
- Route by measured strength, not faith: audits to codex/gemini, gen to local.

## Related

- memory feedback_use_all_substrates_not_own_head · reference_local_llm_assets
- [[local-llm-agent]] (the local substrate) · [[absorption-probe]] (measure if a
  substrate adds value) · [[aios-decide]] (the 4-OS organ ritual is the AIOS
  analog of this)
