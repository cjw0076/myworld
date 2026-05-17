# AIOS Memory Review

MemoryOS drafts are not accepted automatically. AIOS may propose review actions,
but an operator or explicitly authorized reviewer applies them through
MemoryOS.

## Propose

```bash
python scripts/aios_memory_review_proposer.py --limit 20 --json
```

The proposal batch is written under `.aios/memory_review_proposals/` and uses
`schema_version: aios.memory_review_proposals.v1`.

Rules:

- `recommendation_only: true`
- `auto_apply: false`
- rationale length is capped at 200 characters
- no remote LLM call is required or allowed by this proposer

## Apply

Inspect the proposal first, then apply individual accepted recommendations:

```bash
python -m memoryos.cli --root memoryOS drafts approve <memory_id> \
  --reviewer aios-operator \
  --note "reviewed proposal <batch_id>"
```

Batch approval is available in MemoryOS, but should only be used for a clearly
bounded class of records with shared provenance and risk.

## Verify

After approval, prove the memory is actually retrievable:

```bash
python -m memoryos.cli --root memoryOS context build \
  --task "<query>" \
  --for hive \
  --project AIOS \
  --json
```

The returned context pack must include at least one accepted memory in a
section such as `decisions`, `constraints`, `recent_actions`, or `other`.

## Stop Conditions

- `proposer_auto_accept`
- `proposer_uses_remote_llm`
- `accepted_memory_not_retrievable`
- `batch_approval_without_shared_policy`
