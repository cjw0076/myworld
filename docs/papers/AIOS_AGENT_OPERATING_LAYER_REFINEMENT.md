# AIOS Agent Operating Layer Paper Refinement Loop

Status: ASC-0160 role-artifact refinement note  
Date: 2026-05-14

## Source Invocation

- invocation: `.aios/invocations/asc-0160-paper-refinement/receipt.json`
- session envelope:
  `.aios/invocations/asc-0160-paper-refinement/session_envelope.json`
- goal: refine the AIOS operating-layer paper while preserving the claim that
  AIOS wraps provider CLIs rather than replacing them.
- overall_status: `passed`
- role_statuses: MemoryOS `passed`, CapabilityOS `passed`, GenesisOS
  `passed`, Hive `passed`

## MemoryOS Signal

Artifact:

- `.aios/invocations/asc-0160-paper-refinement/memory/context_pack.md`

MemoryOS returned a context pack for the Hive role with:

- trace_id: `rtrace_7124ea1c1fee8eff`
- selected_memory_ids:
  - `mem_5012d57c2c4acbf6`
  - `mem_4a44670b379ca4ea`
  - `mem_e4a9c7fe7d342598`
  - `mem_d0b64430dd5da2a8`
  - `mem_3af960f629693170`
  - `mem_001f6d5191fb8e51`
  - `mem_fdf38e3f47d1aed4`
  - `mem_940ad99fcc2ed445`
  - `mem_70c8edbf4c5c9c7b`
  - `mem_1f18cea463eed9fd`

Paper impact:

- The paper should explicitly evaluate memory usefulness as retrieval with
  provenance, not as vague personalization.
- The evaluation section should measure whether MemoryOS-selected context
  changes restart/resume success or reduces repeated prompting.
- The claim ledger must keep memory usefulness as evidence-needed until
  matched-run evidence exists.

## CapabilityOS Signal

Artifact:

- `.aios/invocations/asc-0160-paper-refinement/capability/route.json`

Top recommendation surfaces:

- `cap_memoryos_context_build`
- `cap_hivemind_execution_harness`
- `cap_memoryos_import_run`
- `cap_capabilityos_recommendation`
- `cap_ollama_qwen25_7b_local`

Paper impact:

- The paper should describe CapabilityOS as recommendation-only in this loop;
  it did not execute network tools or bind capabilities.
- Related-work and benchmark construction are now the next appropriate
  CapabilityOS route, but they need a separate current-source/web evidence
  contract if external citations are required.
- Tool route accuracy should be defined as whether the recommended route
  matches the task's required artifact, not whether the provider simply
  succeeds.

## GenesisOS Signal

Artifact:

- `.aios/invocations/asc-0160-paper-refinement/genesis/branches.json`

Useful branches:

- `failure_as_feature`: treat AIOS friction as the product's strongest signal.
- `inversion`: the useful system may be the one that refuses premature
  completion.
- `alien_domain`: treat the operating layer like city planning, where
  infrastructure, zoning, and rituals matter more than individual features.
- `anti_user_prompt`: ask whether the next valuable move is to change the
  question rather than comply with the literal prompt.

Paper impact:

- Dogfood friction should not be hidden. It is evidence for both AIOS value and
  AIOS overhead.
- The paper should include a reviewer-attack loop before submission.
- The architecture metaphor should avoid a rigid pipeline and emphasize
  operating infrastructure.

## Hive Signal

Artifact:

- `.aios/invocations/asc-0160-paper-refinement/hive/execution_plan.json`

Hive remained plan-only and selected:

- candidate_worker: `hive.provider_loop`
- candidate_provider: `capabilityos_recommended`
- execute_allowed: `false`
- verification_gate:
  - `python -m unittest discover -s tests -p 'test_aios_*.py'`
  - `python scripts/aios_monitor.py assess --json`

Paper impact:

- The current paper draft is a planning/research artifact, not an external
  empirical result.
- The next loop should create a benchmark protocol before claiming measured
  improvement.

## Concrete Edits Applied

- Add a refinement-loop section to the paper draft.
- Add evidence-tightening steps that explicitly use MemoryOS, CapabilityOS,
  GenesisOS, and Hive outputs.
- Add claim-ledger rows for MemoryOS retrieval usefulness, route accuracy, and
  reviewer-attack requirements.

## Next Contract Seeds

1. `ASC-0161-paper-related-work-web-evidence`
   - Use CapabilityOS current-source/web route to collect related-work
     citations with source receipts.
2. `ASC-0162-direct-cli-vs-aios-benchmark-design`
   - Define matched-run tasks, metrics, artifact scoring, and overhead
     measurement.
3. `ASC-0163-paper-reviewer-attack-pass`
   - Run GenesisOS/Hive-style reviewer attacks against unsupported claims and
     downgrade weak statements before submission.
