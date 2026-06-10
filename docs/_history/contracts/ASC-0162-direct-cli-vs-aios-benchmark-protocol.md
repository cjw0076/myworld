---
contract_id: ASC-0162
slug: direct-cli-vs-aios-benchmark-protocol
status: closed
goal: Define the matched-run benchmark protocol for direct provider CLI versus AIOS-wrapped provider CLI.
created: 2026-05-14 12:15 KST
accepted: 2026-05-14 12:15 KST
closed: 2026-05-14 12:17 KST
acceptance_authority: founder delegated continuation under active AIOS paper goal.
origin: ASC-0161 grounded related work; the paper now needs a reproducible evaluation protocol before making measured performance claims.
---

# ASC-0162 Direct CLI Vs AIOS Benchmark Protocol

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain).

## Scope

repos:

- `myworld`

allowed_files:

- `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- `docs/papers/AIOS_BENCHMARK_PROTOCOL.md`
- `docs/papers/AIOS_MYWORLD_CLAIM_LEDGER.md`
- `tests/test_aios_paper.py`
- `docs/contracts/ASC-0162-direct-cli-vs-aios-benchmark-protocol.md`
- `docs/contracts/README.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## AIOS Role Evidence

### MemoryOS

- context_pack: `protocol will define when context is allowed`
- retrieval_trace: `future benchmark run artifact`
- accepted_memory_ids: `not_required_for_protocol`
- draft_memory_policy: `no empirical claim without run evidence`

### CapabilityOS

- route: `benchmark design`
- recommended_tools: `task fixture snapshots, result receipts, artifact scoring`
- fallback_plan: `manual scoring rubric if automated metrics are incomplete`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `reviewer attack: unfair comparison, provider confound, overhead hidden`
- assumption_mutations: `hold provider constant; measure overhead explicitly`
- semantic_alignment_notes: `AIOS layer effect only`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `codex@myworld writes benchmark protocol`
- provider_route: `codex_cli`
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `not_required`

## myworld.must_produce

- Benchmark protocol defining matched snapshots, task families, baseline/system
  conditions, metrics, scoring, exclusions, and artifacts.
- Paper draft update linking evaluation design to the protocol.
- Tests proving the protocol preserves provider-control and overhead metrics.

## Verification Gate

```bash
python -m unittest tests/test_aios_paper.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Protocol says the provider must be held constant.
- Protocol includes overhead metrics.
- Protocol defines artifacts required from both baseline and AIOS conditions.
- Paper points to the protocol without claiming results already exist.

## Stop Conditions

- `provider_not_controlled`
- `overhead_metrics_missing`
- `paper_claims_results_before_runs`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0162.myworld.result.json`
- benchmark protocol: `docs/papers/AIOS_BENCHMARK_PROTOCOL.md`
- monitor closeout: collected result cleared blocking alerts; remaining
  monitor findings are advisory Genesis/persona signals.

## Work Packets

### WP-0162-A — codex@myworld writes benchmark protocol

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0161
- brief: |
    Define a reproducible benchmark protocol comparing direct provider CLI
    workflow with the same provider wrapped by AIOS. Include overhead and
    artifact-trace metrics, and avoid claiming results before runs exist.
- result: `.aios/outbox/myworld/asc-0162.myworld.result.json`
