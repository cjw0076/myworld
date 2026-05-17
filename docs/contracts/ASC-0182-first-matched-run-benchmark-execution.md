---
contract_id: ASC-0182
slug: first-matched-run-benchmark-execution
status: closed
goal: Execute the first synthetic matched-run benchmark fixture per ASC-0162's protocol — validate the measurement protocol on real task pairs and feed executed numbers into the AIOS utility paper.
created: 2026-05-17 03:35 KST
accepted: 2026-05-17 03:35 KST
closed: 2026-05-17 03:55 KST
close_evidence: docs/papers/AIOS_BENCHMARK_RESULTS.md (4 protocol tables filled with executed N=3 numbers); benchmark/fixtures + benchmark/runs (fixtures and run artifacts); paper draft §6.4 + abstract + conclusion cite the executed results; tests/test_aios_paper.py 9 passed.
acceptance_authority: founder Task-3 directive ("다양한 task에 AIOS가 실제로 효용이 있는지를 논문으로 쓸거야") — delegated continuation.
origin: ASC-0162 defined the benchmark protocol but its "Next Implementation Contract" (first synthetic matched-run fixture) was never executed; the 2026-05-17 internal-state audit named this gap #7. The utility paper cannot make measured claims without it.
---

# ASC-0182 First Matched-Run Benchmark Execution

DNA references: Invariant 1 (decide before acting), Invariant 4 (named exit),
Invariant 5 (provenance chain), Invariant 8 (no unearned claim).

## Scope

repos:

- `myworld`

allowed_files:

- `benchmark/**` (new — synthetic fixtures + run artifacts)
- `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- `docs/papers/AIOS_BENCHMARK_RESULTS.md` (new)
- `docs/contracts/ASC-0182-first-matched-run-benchmark-execution.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`
- `.env`, `.env.*`, provider credentials, raw private exports

## Method

Run matched pairs per `docs/papers/AIOS_BENCHMARK_PROTOCOL.md`. The same
LLM provider performs each task twice on the same fixture snapshot:

- **Baseline**: bare edit + test, no AIOS artifact.
- **AIOS**: same task as a contract → dispatch → fix → verify → ledger.

The independent variable is the operating layer, never the model.

## Task Families Covered (first fixture)

1. Single-repo bug fix (family 1) — discriminates AIOS overhead on clean work.
2. Restart/resume after a session boundary (family 5) — discriminates AIOS
   continuity gain.
3. Prior-decision-dependent work (family 7) — discriminates MemoryOS value.

## Honesty Constraints (binding)

- This is a **protocol-validation run, not a superiority claim**. N is small;
  the paper must label it so.
- If AIOS is pure overhead on a task, report it as overhead. Do not hide it.
- No claim beyond what the executed artifacts support (ASC-0162 Claim Rules).

## Named Exit

Closed when: the four protocol tables (Pair Summary, Artifact Trace, Overhead,
Negative Evidence) are filled with executed numbers in
`docs/papers/AIOS_BENCHMARK_RESULTS.md`, and the paper draft cites them.

## Stop Conditions

- A fixture requires private data → stop, redesign fixture.
- A matched pair cannot hold provider/model/snapshot constant → exclude the
  pair per the protocol's Exclusions, do not fabricate a substitute.
