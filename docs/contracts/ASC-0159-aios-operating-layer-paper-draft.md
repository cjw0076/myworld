---
contract_id: ASC-0159
slug: aios-operating-layer-paper-draft
status: closed
goal: Draft the AIOS paper around provider CLI wrapped by a contract-bound operating layer, including evaluation axes and refinement loop.
created: 2026-05-14 11:51 KST
accepted: 2026-05-14 11:51 KST
closed: 2026-05-14 11:57 KST
acceptance_authority: founder delegated continuation under active AIOS paper goal.
origin: Founder selected the safer paper claim that AIOS improves long-running work operation over direct provider CLI workflows, rather than claiming model intelligence superiority.
---

# ASC-0159 AIOS Operating Layer Paper Draft

DNA references: Invariant 1 (decide before acting), Invariant 2
(draft-first), Invariant 4 (named exit), Invariant 5 (provenance chain),
Invariant 6 (operator override remains possible).

## Scope

repos:

- `myworld`

allowed_files:

- `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- `docs/papers/AIOS_MYWORLD_PAPER_CHARTER.md`
- `docs/papers/AIOS_MYWORLD_CLAIM_LEDGER.md`
- `tests/test_aios_paper.py`
- `docs/contracts/ASC-0159-aios-operating-layer-paper-draft.md`
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

- context_pack: `deferred_to_next_revision`
- retrieval_trace: `deferred_to_next_revision`
- accepted_memory_ids: `not_required_for_draft`
- draft_memory_policy: `paper draft only; no memory auto-accept`

### CapabilityOS

- route: `paper-writing/documentation`
- recommended_tools: `repo docs, contract ledger, monitor receipts`
- fallback_plan: `manual evidence ledger if automated citation extraction is incomplete`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `claim safety, reviewer attack, overhead honesty`
- assumption_mutations: `AIOS is not smarter; AIOS is more operable`
- semantic_alignment_notes: `pipeline -> stateful operating loop`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `codex@myworld writes first paper draft and evidence loop`
- provider_route: `codex_cli`
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `not_required`

## myworld.must_produce

- A manuscript-ready first draft with title, abstract, introduction, system
  model, architecture, evaluation plan, overhead metrics, limitations, and
  future work.
- A refinement loop that turns the draft into evidence-bound claims rather
  than unsupported AIOS marketing.
- Claim ledger updates reflecting the new main claim and overhead risk.

## Verification Gate

```bash
python -m unittest tests/test_aios_paper.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Draft centers the comparison on direct provider CLI vs AIOS-wrapped provider
  CLI, not AIOS vs a model.
- Draft includes overhead as an evaluation axis.
- Draft describes AIOS as a stateful operating loop, not a rigid pipeline.
- Claim ledger records new claims as evidence-needed or hypothesis.

## Stop Conditions

- `paper_claims_model_superiority`
- `overhead_omitted`
- `evaluation_conflates_provider_with_operating_layer`
- `unsupported_autonomy_claim`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0159.myworld.result.json`
- paper draft: `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- monitor closeout: collected result cleared blocking alerts; remaining
  monitor findings are advisory Genesis/persona signals.

## Work Packets

### WP-0159-A — codex@myworld drafts operating-layer paper

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0098
- brief: |
    Write the first paper draft around AIOS as a contract-bound operating
    layer for reliable long-running AI work. Use the founder-provided claim,
    include an evaluation design against direct provider CLI workflow, and add
    a loop for later evidence tightening.
- result: `.aios/outbox/myworld/asc-0159.myworld.result.json`
