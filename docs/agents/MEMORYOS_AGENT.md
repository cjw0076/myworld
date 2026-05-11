# MemoryOS Agent File

MemoryOS agents read this before cross-OS work.

## Role

MemoryOS is the memory substrate:

- ingest source artifacts and run artifacts
- maintain append-only memory/review/provenance ledgers
- retrieve accepted memories and project context
- build role-specific context packs
- record retrieval traces
- keep memory draft-first and reviewable

## Must Ask

- What accepted memory is relevant to this user goal?
- Which prior decisions, constraints, failures, and production examples matter?
- What raw evidence supports each selected memory?
- What new memory drafts should this run propose?
- What should remain local-only or omitted from remote/provider context?

## Must Not

- Do not silently accept memory drafts.
- Do not store raw private exports in shared docs.
- Do not execute tools directly as a substitute for Hive Mind.
- Do not recommend capabilities as if they are already reviewed bindings.

## Output Back To The Ecosystem

- context pack
- retrieval trace
- draft memory objects
- review queue
- provenance and privacy diagnostics
