---
name: aios-memory-propose
description: >-
  Propose and (after explicit review) accept a MemoryOS memory object the
  correct way — turning a recall/decision into durable accepted memory so
  future aios_retrieve stops returning null. Bakes in the two mistakes agents
  repeat: (1) raw .memlang files import 0 blocks — MemLang MUST be a fenced
  ```memlang block inside a .md file; (2) no silent/bulk auto-accept (DNA
  invariant 2) — every acceptance is one object with a documented review.
---

# AIOS Memory Propose → Review → Accept

The 2026-06-05 absorption probe found accepted memory was 100% AIOS-internal
(0 product-domain), so retrieve returned null on product tasks. The fix is
flowing real memories through draft → reviewed → accepted. This skill encodes
the working pipeline + the gotchas discovered the hard way.

## When to use

- A `aios-decide` recall returned null and you now have a durable fact worth
  remembering for the next agent/session.
- A closed contract / probe / decision produced a reusable rule.
- You want to raise product-domain coverage (see the inward-growth alarm in
  `scripts/aios_memory_retrieval_audit.py`).

**Do NOT use** for ephemeral session state (the AIOS ledger / receipts hold that).

## Workflow

1. **Write MemLang inside a fenced block in a `.md` file** (NOT a raw
   `.memlang` file — that imports 0 blocks):

   ````markdown
   ```memlang
   @project URI

   !decision [draft]
     "<the durable fact, one claim>"
     confidence=0.8
     refs=[<repo evidence paths>]
   ```
   ````
   Set `@project` to the real domain (URI / hivemind / …), NOT "AIOS" unless
   it truly is AIOS-internal — product coverage is what we're short on.

2. **Dry-run, then import** (run inside `memoryOS/`):
   ```bash
   python -m memoryos.cli --root . import --memlang --dry-run path.md   # expect "1 MemoryObject drafts"
   python -m memoryos.cli --root . import --memlang path.md
   ```
3. **Find the draft id:** `drafts list --project <P> --status draft --json`.
4. **Explicit review (the invariant).** Read it (`drafts show <id>`), judge
   evidence, then:
   ```bash
   python -m memoryos.cli --root . drafts approve <id> \
     --reviewer "claude@myworld" --note "<why: grounding + risk + reversible>"
   ```
5. **Verify the loop closed:** `context build --task "<query>" --json` (or
   `aios_retrieve`) now returns the object. Then `aios_observe` the decision.

## Hard rules

- **No silent or bulk auto-accept.** DNA invariant 2 / CLAUDE.md "Do not
  auto-accept MemoryOS records." `approve-batch` on unread drafts is the
  anti-pattern — that is silent-accept wearing an operator hat. One object,
  one documented review note, each time.
- **Acceptance is reversible** (`drafts reject` / `supersede`) — so a single
  well-reasoned accept is an operator decision, not a founder escalation.
- **Keep the import `.md` as the source artifact** — its path is recorded as
  provenance; renaming/deleting it dangles the source ref.
- Drafting is always fine; only acceptance needs the review gate.

## Related

- `scripts/aios_memory_retrieval_audit.py` (domain coverage + inward_growth_alarm)
- memory project_memoryos_inward_growth_finding · feedback_no_auto_accept
- [[aios-decide]] (recall step that feeds this) · `reference_memoryos_review_request_packet`
