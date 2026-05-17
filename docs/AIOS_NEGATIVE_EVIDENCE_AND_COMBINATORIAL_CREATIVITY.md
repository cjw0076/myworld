# AIOS Negative Evidence And Combinatorial Creativity

Status: V1 specification for ASC-0163  
Date: 2026-05-14

## Purpose

AIOS must learn from more than completed work. Long-running agent work contains
weak labels: failed routes, misleading memories, false confidence, provider
habits, bad tools, and user discomfort. These are not cleanup noise. They are
training signal for future routing, retrieval, verification, and creative
branching.

GenesisOS is therefore not only a critic. It is the layer that recombines
negative evidence, distant domains, tool affordances, founder intent, and
semantic alignment into new candidate worlds before AIOS converges on one
execution path.

## Required Evidence Classes

### Failure Memory

MemoryOS should support reviewable drafts for failure patterns:

- `kind`: `failure_memory`
- `source_artifact`: contract, dispatch result, invocation receipt, trace, or
  worklog that proves the failure happened
- `task_context`: what AIOS was trying to do
- `failed_pattern`: the mistaken assumption, bad prompt habit, stale memory, or
  false-success shape
- `negative_label`: `misleading_context`, `false_success`,
  `provider_backpressure`, `scope_violation`, `bad_retrieval`,
  `unproductive_loop`, or `privacy_hold`
- `reuse_rule`: when this failure should change future behavior
- `review_status`: draft-first; never auto-accepted

Failure memories are useful only when they carry provenance. A naked statement
like "this method failed" is not reusable memory.

### Bad Tool Observation

CapabilityOS should preserve low-value or harmful route evidence:

- `kind`: `bad_tool_observation`
- `capability_id`: the routed tool, provider, API, skill, or MCP surface
- `task_context`: what the route was expected to solve
- `route_reason`: why it was selected
- `outcome`: `irrelevant`, `costly`, `unsafe`, `blocked`, `low_signal`,
  `wrong_modality`, `auth_blocked`, or `overkill`
- `replacement_hint`: better route or checkpoint condition
- `evidence_ref`: route artifact, result packet, monitor alert, or reviewer
  note

Bad tool evidence should reduce future route confidence only in matching
contexts. The same tool can be bad for one task and good for another.

### Genesis Recombination Candidate

GenesisOS should produce more than warnings. A useful Genesis artifact can be a
new candidate formed by combining unlike evidence:

- `kind`: `genesis_recombination_candidate`
- `inputs`: two or more source signals, such as a failure memory, bad tool
  observation, accepted founder pattern, external analogy, and current goal
- `combination_mode`: `inversion`, `alien_domain`, `constraint_removal`,
  `failure_as_feature`, `anti_user_prompt`, `semantic_bridge`, or
  `worldline_merge`
- `candidate`: the new direction, interface, contract, or experiment
- `what_it_breaks`: the default frame this branch refuses
- `need_created`: the concrete discomfort or gap that makes the branch worth
  testing
- `verification_seed`: the smallest future check that can turn the idea into a
  contract or reject it
- `authority`: advisory only; MyWorld or the operator chooses

This is the AIOS form of human combination ability. Humans create by moving a
pattern from one domain into another, noticing discomfort, then turning it into
a need. GenesisOS must make that motion explicit and auditable.

## OS Responsibilities

### MemoryOS

- Store success and failure as separate reviewable drafts.
- Preserve provenance for failed memories and misleading context.
- Allow future context builds to include relevant negative evidence when the
  retrieval intent asks for risk, prior failure, or route avoidance.
- Do not auto-accept failure memories merely because a contract closed.

### CapabilityOS

- Record positive and negative capability observations.
- Distinguish "tool unavailable", "tool unsafe", "tool irrelevant", and "tool
  too expensive" from generic failure.
- Let negative observations affect route confidence by task context.
- Keep execution authority out of recommendation-only surfaces.

### GenesisOS

- Generate recombination candidates from negative evidence, accepted patterns,
  distant analogies, and current goals.
- Treat discomfort as a signal that can create a new need.
- Preserve multiple candidate worlds without choosing final truth.
- Surface semantic bridges when two agents use the same word differently.

### Hive Mind

- Mark execution receipts as `failed`, `degraded`, `recovered`, or
  `false_success` instead of flattening them into pass/fail.
- Attach enough task and artifact context for MemoryOS and CapabilityOS to
  create negative evidence drafts.
- Verify any recombination candidate before implementation.

### MyWorld

- Keep negative evidence and Genesis recombination in contracts, dispatch
  packets, paper claims, and benchmark scoring.
- Prevent success-only ledgers from making AIOS look healthier than it is.
- Choose which Genesis candidate becomes the next contract.

## Invocation Evidence

ASC-0163 used a plan-only AIOS invocation before this spec was written:

- invocation: `.aios/invocations/asc-0163-negative-evidence-creativity/`
- MemoryOS trace: `rtrace_0fa028fc49623cad`
- CapabilityOS route: recommendation-only local routes including
  `cap_ollama_qwen25_7b_local`, `cap_hivemind_execution_harness`, and
  `cap_memoryos_context_build`
- GenesisOS branches: `inversion`, `alien_domain`, `constraint_removal`,
  `failure_as_feature`, and `anti_user_prompt`
- Hive: `execute_allowed=false`, preserving control-plane boundaries

The invocation itself is evidence that the next implementation should not be
hidden in chat. It should become child repo work packets.

## Stop Conditions

- `negative_evidence_without_provenance`
- `failure_memory_auto_accepted`
- `bad_tool_label_without_context`
- `genesis_candidate_selected_without_verification_seed`
- `privacy_sensitive_failure_copied_into_shared_artifact`
- `success_only_closeout_masks_failed_substeps`

## Next Child-Repo Work

1. MemoryOS: add a failure-memory draft schema or metadata profile and a
   retrieval path for negative evidence.
2. CapabilityOS: add negative observation labels and route-confidence effects.
3. GenesisOS: add recombination candidate output beside critique branches.
4. Hive Mind: emit richer failure/degraded/false-success receipt labels.

These are implementation tasks. ASC-0163 only fixes the shared AIOS language
and paper/benchmark contract so each child repo can implement the same idea.
