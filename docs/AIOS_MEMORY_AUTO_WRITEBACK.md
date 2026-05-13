# AIOS Memory Auto-Writeback

ASC-0091 adds a draft-first closeout memory path:

1. A contract is marked `closed`.
2. `scripts/aios_dispatch.py release` runs the closeout hook unless
   `--no-memory-write` is passed.
3. `scripts/aios_contract_to_memory.py emit --contract ASC-NNNN --json`
   emits `aios.contract_closeout_memory.v1`.
4. `memoryOS ingest-contract-closeout --json` writes one
   `MemoryObject(type=decision, status=draft, project=AIOS)`.
5. Human or AIOS review still decides whether the draft is accepted.

The hook must never auto-accept memory. Every emitted closeout payload must
carry non-empty `evidence_refs`; otherwise MemoryOS rejects it.

Manual check:

```bash
python scripts/aios_contract_to_memory.py emit --contract ASC-0095 --json
python scripts/aios_contract_to_memory.py emit --contract ASC-0095 --json > /tmp/closeout.json
python -m memoryos.cli --root memoryOS ingest-contract-closeout --json /tmp/closeout.json
python -m memoryos.cli --root memoryOS drafts list --project AIOS --json
```

Operational rule: raw provider output is not copied into the MemoryOS draft.
Only contract paths, result packet paths, commit SHAs, ledger refs, and compact
substrate observations are recorded.
