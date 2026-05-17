# AIOS Benchmark Protocol

Status: protocol draft for ASC-0162  
Date: 2026-05-14

## Objective

Measure the operating-layer effect of AIOS by comparing direct provider CLI
workflow against the same provider CLI wrapped by AIOS.

The benchmark must not compare different models. Provider quality is a
confound. The independent variable is the operating layer.

## Conditions

### Baseline: Direct Provider CLI

- Same repository snapshot as the AIOS condition.
- Same task prompt.
- Same provider CLI and model configuration.
- No AIOS contract, dispatch packet, MemoryOS context pack, CapabilityOS route,
  GenesisOS branch, Hive packet, monitor recovery, or AIOS ledger closeout.
- The provider may inspect files, edit files, and run tests as a normal direct
  CLI workflow would permit.

Required baseline artifacts:

- initial repository snapshot id
- final diff
- command log or terminal transcript
- test output
- human reprompt count
- provider failure/backpressure notes
- elapsed time

### System: AIOS-Wrapped Provider CLI

- Same repository snapshot.
- Same task prompt, converted into an accepted AIOS contract or governed goal.
- Same provider CLI and model configuration as baseline.
- AIOS may use MemoryOS, CapabilityOS, GenesisOS, Hive, monitor, and ledger
  surfaces as the contract permits.

Required AIOS artifacts:

- contract id
- dispatch packet
- role artifacts used, if any
- result packet
- monitor assessment
- final diff
- test output
- ledger closeout
- memory draft ids
- human reprompt count
- provider failure/backpressure notes
- elapsed time

## Task Families

Use at least two tasks from each class before making broad claims:

1. Single-repo bug fix.
2. Multi-file feature implementation.
3. Multi-repo coordination.
4. Provider failure or empty-output recovery.
5. Restart/resume after a session boundary.
6. External tool/API research and integration.
7. Prior-decision-dependent work where memory should matter.

## Metrics

### Outcome Metrics

- `completion_rate`: task reaches its stated done condition.
- `verification_pass_rate`: declared tests or checks pass.
- `restart_resume_success`: resumed run can identify prior state and continue
  without re-deriving all context.
- `provider_failure_recovery`: provider failure is classified and recovered or
  checkpointed.
- `scope_violation_count`: edits or actions outside allowed scope.
- `artifact_trace_completeness`: required records exist and cross-reference
  each other.
- `memory_reuse_count`: accepted memory ids or context traces used in the
  AIOS condition.
- `tool_route_accuracy`: recommended route matches required artifact or task
  need.
- `user_visibility_score`: reviewer can answer what happened, what is blocked,
  and what artifact proves it.
- `negative_evidence_captured`: failed memories, bad routes, false holds,
  failed tools, and misleading provider habits are recorded as learnable
  signals rather than discarded.
- `genesis_recombination_count`: GenesisOS produces candidate branches that
  combine at least two unlike signals, such as a failure memory plus a distant
  domain analogy or bad route plus founder pattern.

### Overhead Metrics

- `extra_time_per_task`: AIOS elapsed time minus direct CLI elapsed time.
- `generated_artifact_count`: contracts, packets, receipts, ledgers, drafts,
  and role artifacts.
- `false_checkpoint_count`: checkpoint or hold that reviewer judges
  unnecessary.
- `false_escalation_count`: escalation that blocks harmless work.
- `contract_authoring_cost`: time and token cost spent creating or revising the
  contract.
- `user_cognitive_load`: reviewer rating of how hard the workflow was to
  understand.

## Scoring

Use paired comparisons. Each task produces one baseline run and one AIOS run.

Primary score:

```text
operating_gain =
  normalized(reliability + recovery + continuity + governance + visibility)
  - normalized(overhead)
```

Do not collapse the full result into a single number in the paper unless the
component table is also shown.

## Exclusions

Exclude or rerun a pair if:

- provider differs between conditions
- model configuration differs
- repository snapshot differs
- task prompt materially differs
- private data or secrets enter either condition
- either condition receives extra human advice not counted as a reprompt

## Required Tables

### Pair Summary

| Task | Provider | Direct CLI Result | AIOS Result | Main Gain | Main Overhead |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD |

### Artifact Trace

| Task | Condition | Required Artifacts Present | Missing Artifacts | Trace Complete |
| --- | --- | --- | --- | --- |
| TBD | Direct CLI | TBD | TBD | TBD |
| TBD | AIOS | TBD | TBD | TBD |

### Overhead

| Task | Direct Time | AIOS Time | Extra Artifacts | False Holds | Human Reprompts |
| --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD | TBD |

### Negative Evidence And Creativity Trace

| Task | Failure Memories | Bad Tool Observations | Genesis Recombination Candidates | Promoted To Contract |
| --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | TBD |

## Claim Rules

- Do not claim AIOS improves task quality until matched-run outcome evidence
  exists.
- Do not claim AIOS reduces human effort unless reprompt count or user load is
  measured.
- Do not claim MemoryOS is useful unless a run uses selected memories or
  retrieval traces.
- Do not claim CapabilityOS is useful unless route recommendations are checked
  against task needs.
- Do not claim AIOS learns from experience unless both successful and failed
  examples are retained with provenance.
- Do not claim GenesisOS improves creativity unless recombination candidates
  are preserved and at least one is rejected, revised, or promoted through a
  verification seed.
- Do not hide overhead. If AIOS is slower or heavier, report it.

## Negative Evidence Policy

Long-running agent work rarely has clean labels. AIOS therefore needs both
positive and negative examples:

- MemoryOS should store failed or misleading patterns as reviewable memory
  drafts, not only successful lessons.
- CapabilityOS should preserve bad route/tool observations so future routing
  can avoid tools that were costly, irrelevant, unsafe, or repeatedly
  unproductive.
- Hive receipts should distinguish failed execution, degraded execution,
  recovered execution, and false success.
- GenesisOS should treat discomfort and failure as branch-generation material.

Negative evidence must be provenance-bound. A "bad tool" claim without task,
route, outcome, and reviewer context is not reusable evidence.

GenesisOS should use this evidence to create recombination candidates, not just
post-hoc critiques. The required shape is defined in
`docs/AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md`: a candidate
must name its input signals, combination mode, created need, what default frame
it breaks, and the smallest verification seed.

## Next Implementation Contract

The next contract should create the first synthetic matched-run fixture with a
small, non-private repository snapshot and one bug-fix task. The initial goal
is to test the measurement protocol, not to prove AIOS superiority.
