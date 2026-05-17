---
contract_id: ASC-0160
slug: paper-refinement-loop
status: closed
goal: Refine the AIOS operating-layer paper through AIOS role artifacts, reviewer attacks, and evidence tightening.
created: 2026-05-14 12:01 KST
accepted: 2026-05-14 12:01 KST
closed: 2026-05-14 12:06 KST
acceptance_authority: founder delegated continuation under active AIOS paper goal.
origin: ASC-0159 produced the first paper draft; the next loop must dogfood AIOS by collecting MemoryOS, CapabilityOS, and GenesisOS signals and reflecting them back into the paper.
---

# ASC-0160 Paper Refinement Loop

DNA references: Invariant 1 (decide before acting), Invariant 2
(draft-first), Invariant 4 (named exit), Invariant 5 (provenance chain).

## Scope

repos:

- `myworld`

allowed_files:

- `.aios/invocations/asc-0160-paper-refinement/**`
- `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- `docs/papers/AIOS_AGENT_OPERATING_LAYER_REFINEMENT.md`
- `docs/papers/AIOS_MYWORLD_CLAIM_LEDGER.md`
- `tests/test_aios_paper.py`
- `docs/contracts/ASC-0160-paper-refinement-loop.md`
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

- context_pack: `.aios/invocations/asc-0160-paper-refinement/memory/context_pack.md`
- retrieval_trace: `artifact or degraded receipt from invocation`
- accepted_memory_ids: `not_required_for_draft`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `.aios/invocations/asc-0160-paper-refinement/capability/route.json`
- recommended_tools: `paper evidence, search, evaluation planning`
- fallback_plan: `manual related-work checklist if route is degraded`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `.aios/invocations/asc-0160-paper-refinement/genesis/branches.json`
- assumption_mutations: `reviewer attacks and claim downgrades`
- semantic_alignment_notes: `paper claim must remain operating-layer claim`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `codex@myworld turns role artifacts into refinement notes`
- provider_route: `codex_cli`
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `pending_if_any_role_degraded`

## myworld.must_produce

- AIOS invocation artifacts for the paper-refinement goal.
- A refinement note that summarizes MemoryOS, CapabilityOS, and GenesisOS
  signals and converts them into paper edits or future evidence tasks.
- Draft updates that add an evidence-tightening loop and preserve the safe
  core claim.
- Tests proving the paper references the refinement loop and claim ledger.

## Verification Gate

```bash
python -m unittest tests/test_aios_paper.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Invocation artifacts exist for MemoryOS, CapabilityOS, and GenesisOS roles.
- Refinement note records useful signals and any degraded roles.
- Paper draft includes a concrete evidence-tightening loop.
- Claim ledger includes refinement/evidence benchmark claims.

## Stop Conditions

- `missing_invocation_artifacts`
- `role_degraded_without_note`
- `paper_claims_model_superiority`
- `unsupported_autonomy_claim`
- `verification_gate_failed`

## Receipts

- invocation receipt:
  `.aios/invocations/asc-0160-paper-refinement/receipt.json`
- watcher result: `.aios/outbox/myworld/asc-0160.myworld.result.json`
- refinement note: `docs/papers/AIOS_AGENT_OPERATING_LAYER_REFINEMENT.md`
- monitor closeout: collected result cleared blocking alerts; remaining
  monitor findings are advisory Genesis/persona signals.

## Work Packets

### WP-0160-A — codex@myworld refines the paper through AIOS artifacts

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0159
- brief: |
    Run a plan-only AIOS invocation for the paper refinement goal. Summarize
    MemoryOS, CapabilityOS, and GenesisOS outputs into a paper refinement note,
    update the draft with an evidence-tightening loop, and verify with paper
    tests.
- result: `.aios/outbox/myworld/asc-0160.myworld.result.json`
