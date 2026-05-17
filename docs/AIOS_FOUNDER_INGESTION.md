# AIOS Founder Ingestion

ASC-0111 adds the first structured path for founder directives to enter
MemoryOS as draft memories.

The pipeline is deliberately narrow:

1. `scripts/aios_founder_capture.py` reads durable AIOS records, not chat
   scroll.
2. It extracts founder directives from operator session logs and contract
   `acceptance_authority` / `origin` lines.
3. It emits `aios.founder_directive_memory.v1`.
4. `memoryos ingest-founder-directive` writes
   `MemoryObject(type=decision, origin=founder_directive, status=draft)`.

Run:

```bash
python scripts/aios_founder_capture.py --write /tmp/founder_capture.json --json
cd memoryOS
python -m memoryos --root . ingest-founder-directive /tmp/founder_capture.json --json
python -m memoryos --root . drafts list --origin founder_directive --json
```

Boundaries:

- The extractor does not scrape chat scroll.
- Drafts are not auto-accepted.
- Content preserves directive text instead of replacing it with a summary.
- Raw refs point back to durable source files and lines.

## Activation Review

Founder directives become useful to Hive/Claude only after MemoryOS review
accepts selected drafts. On 2026-05-13, Codex acting as founder-delegated
operator approved 10 direct founder directives with durable contract
provenance, leaving paraphrased or low-signal directives as drafts.

Approved memory IDs:

- `mem_001f6d5191fb8e51`
- `mem_70c8edbf4c5c9c7b`
- `mem_4f390c90de100dbf`
- `mem_61910dd09950fc81`
- `mem_1f18cea463eed9fd`
- `mem_0c3b41fd22b1d801`
- `mem_4ec54ac7409828c8`
- `mem_7a13c1fc3880df9c`
- `mem_fdf38e3f47d1aed4`
- `mem_3d34968d34418b03`

Verification:

```bash
python -m memoryos.cli --root memoryOS context build \
  --task "AIOS완성 공진화 memoryOS capabilityOS hive mind founder directive" \
  --for hive --project AIOS --json --explain --include-excluded
```

The run selected founder directives in trace `rtrace_31b18b1d2fd7c0aa`.
Retrieval still needs ASC-0110 ranking/tokenization repair, but founder memory
is no longer draft-only.
