---
contract_id: ASC-0161
slug: paper-related-work-source-evidence
status: closed
goal: Add source-grounded related work evidence to the AIOS operating-layer paper.
created: 2026-05-14 12:10 KST
accepted: 2026-05-14 12:10 KST
closed: 2026-05-14 12:14 KST
acceptance_authority: founder delegated continuation under active AIOS paper goal.
origin: ASC-0160 identified related-work/source evidence as the next paper gap after the first refinement loop.
---

# ASC-0161 Paper Related Work Source Evidence

DNA references: Invariant 1 (decide before acting), Invariant 5 (provenance
chain), Invariant 7 (private-gated data stays out of dispatch and prompt
artifacts).

## Scope

repos:

- `myworld`

allowed_files:

- `docs/papers/AIOS_AGENT_OPERATING_LAYER_DRAFT.md`
- `docs/papers/AIOS_RELATED_WORK_SOURCE_RECEIPT.md`
- `docs/papers/AIOS_MYWORLD_CLAIM_LEDGER.md`
- `tests/test_aios_paper.py`
- `docs/contracts/ASC-0161-paper-related-work-source-evidence.md`
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

- context_pack: `ASC-0160 context already captured`
- retrieval_trace: `rtrace_7124ea1c1fee8eff`
- accepted_memory_ids: `not_required_for_source_receipt`
- draft_memory_policy: `source receipt may become draft memory after closeout`

### CapabilityOS

- route: `current-source/web evidence`
- recommended_tools: `web search, primary source docs, arXiv pages`
- fallback_plan: `keep related work as placeholders if source evidence is missing`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `reviewer attack: related work omission`
- assumption_mutations: `AIOS is distinct by operating-layer boundary, not by claiming to be first`
- semantic_alignment_notes: `related work narrows claim rather than inflating it`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `codex@myworld adds source receipt and paper section`
- provider_route: `codex_cli + web evidence`
- verification_receipt: `pending`
- degraded_or_fallback_receipt: `not_required`

## myworld.must_produce

- Source receipt with primary sources and source-role notes.
- Related work section that positions AIOS against agent orchestration,
  software agents, durable workflow runtimes, and long-running agent platforms.
- Tests proving source receipt and related work references exist.

## Verification Gate

```bash
python -m unittest tests/test_aios_paper.py
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Related work source receipt includes source URLs.
- Paper related work section cites the source receipt and preserves the
  operating-layer claim boundary.
- No private data or provider credentials are added.

## Stop Conditions

- `source_evidence_missing`
- `related_work_overclaims_novelty`
- `private_data_in_source_receipt`
- `verification_gate_failed`

## Receipts

- watcher result: `.aios/outbox/myworld/asc-0161.myworld.result.json`
- source receipt: `docs/papers/AIOS_RELATED_WORK_SOURCE_RECEIPT.md`
- monitor closeout: collected result cleared blocking alerts; remaining
  monitor findings are advisory Genesis/persona signals.

## Work Packets

### WP-0161-A — codex@myworld adds related-work source evidence

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14
- depends_on: ASC-0160
- brief: |
    Use web evidence from primary sources to add a related-work source receipt
    and update the paper's related work section without overclaiming AIOS
    novelty.
- result: `.aios/outbox/myworld/asc-0161.myworld.result.json`
