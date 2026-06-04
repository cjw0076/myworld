---
contract_id: ASC-0216
slug: github-reddit-alignment-mining
status: closed
created: 2026-05-20T22:51:00+09:00
accepted: 2026-05-20T22:51:00+09:00
closed: 2026-05-20T22:54:00+09:00
accepted_by: codex_delegated_operator
human_approved: true
goal: Mine GitHub projects and Reddit practitioner discussions for alignment, evaluation, observability, guardrail, and preference-learning ideas, then decide what AIOS should attach next.
origin: founder request — "작업 만들자. 그리고 이번엔 github, reddit 돌면서 좋은 프로젝트, 아이디어들 mining 후 적용 방안 생각"
---

# ASC-0216 GitHub / Reddit Alignment Mining

DNA references: Invariant 1 (decide before acting), Invariant 5
(provenance chain), Invariant 7 (private-gated data stays out of dispatch and
prompt artifacts).

This contract deliberates; it does not deploy. It produces only research,
evidence, and next-contract recommendations. It does not install third-party
packages, import third-party code, call hosted observability services, or train
models.

## Decision

AIOS should create an **alignment eval spine** before any DPO/RLHF pilot.

The mined projects and practitioner threads converge on:

```text
trace multi-step behavior
  -> evaluate workflow quality
  -> red-team boundaries
  -> promote user/failure feedback into regression cases
  -> update policy/routes/templates
  -> train models only later
```

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0216-github-reddit-alignment-mining.md`
- `docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json`
- `docs/research/AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20.md`
- `docs/AGENT_WORKLOG.md`
- `.aios/inbox/myworld/asc-0216.myworld.json`
- `.aios/outbox/myworld/asc-0216.myworld.result.json`

forbidden_files:

- `.env`
- provider auth files
- raw exports
- private history stores
- child repo implementation files
- third-party source imports
- package lockfiles from dependency installation

## Research Targets

must_mine:

- GitHub projects for evals, tracing, guardrails, red-team, preference
  optimization, and RLHF/DPO tooling.
- Reddit practitioner threads for production pain points and workflow-level
  failure modes.

must_produce:

- A validated web evidence receipt.
- A research note ranking projects and extracting AIOS application patterns.
- A next-contract sequence that starts with local eval/trace/preference
  substrate before neural fine-tuning.

must_not:

- Install any mined tool.
- Send AIOS traces or private data to external services.
- Treat Reddit comments as authoritative without labeling them practitioner
  signals.
- Start model fine-tuning.

## Findings

See:

- `docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json`
- `docs/research/AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20.md`

Short synthesis:

- Promptfoo, OpenAI Evals, DeepEval, and Ragas point toward local eval cases,
  matrix comparisons, private datasets, and test-like developer ergonomics.
- Langfuse, Phoenix, and Helicone point toward traces, spans, prompt/version
  management, and cost/latency observability.
- Garak, LLM Guard, and Guardrails point toward adversarial probes and
  input/output boundary checks.
- TRL, Alignment Handbook, and OpenRLHF are later training backends, not the
  first AIOS attachment.
- Reddit practitioners repeatedly warn that prompt-level evals miss
  multi-step agent drift, stale context, schema mismatch, execution failures,
  and the feedback loop from production miss to regression case.

## Next Contracts

Recommended sequence:

1. `ASC-0217-aios-eval-spine`
2. `ASC-0218-aios-trace-span-schema`
3. `ASC-0219-red-team-boundary-probes`
4. `ASC-0220-preference-to-regression`
5. `ASC-0221-control-center-alignment-matrix`
6. `ASC-0222-local-dpo-readiness-check`

Named next exit:

```text
One AIOS contract/result pair can be evaluated locally against a rubric,
linked to its trace, and promoted into a regression case after user rejection.
```

## Verification Gate

```bash
python scripts/aios_web_research_receipt.py validate docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `uncited_claim`: mined project or Reddit-derived claim lacks a URL in the
  receipt.
- `private_data_leak`: research artifact includes secrets, raw exports, or
  private provider logs.
- `dependency_installed`: this mining task installs or vendors third-party
  packages.
- `training_overreach`: the task starts model fine-tuning before preference
  ledger and eval gates exist.
- `reddit_overclaim`: Reddit practitioner signals are presented as canonical
  truth rather than field signals.

## Work Packets

### WP-0216-A — Codex@myworld GitHub/Reddit mining

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-20
- accepted: 2026-05-20
- closed: 2026-05-20
- depends_on: ASC-0209
- brief: |
    Mine GitHub and Reddit for alignment/eval/observability/guardrail
    projects and practitioner signals. Produce a web evidence receipt, a
    research note, and a next-contract sequence. Do not install third-party
    packages or edit child repo implementation.
- result: `.aios/outbox/myworld/asc-0216.myworld.result.json`

## Receipts

- web evidence receipt:
  `docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json`
- research note:
  `docs/research/AIOS_GITHUB_REDDIT_ALIGNMENT_MINING_2026-05-20.md`
- dispatch packet:
  `.aios/inbox/myworld/asc-0216.myworld.json`
- result packet:
  `.aios/outbox/myworld/asc-0216.myworld.result.json`
- verification:
  `python scripts/aios_web_research_receipt.py validate docs/evidence/ASC-0216-github-reddit-alignment-mining-web-evidence.json --json`
  passed; `python scripts/aios_monitor.py assess --json` returned
  `health=watch` with info-only advisory findings unrelated to ASC-0216
  blocking; watcher result passed and was collected.
