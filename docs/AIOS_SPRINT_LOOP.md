# AIOS Sprint Loop

The sprint loop is the file-backed way to make one-shot providers behave like a
bounded loop.

Codex does not need to stay alive. AIOS keeps a local sprint file, calls Codex
for one worker tick, records a receipt, then checks the sprint file again. If
unchecked work remains, AIOS may call another tick. If no unchecked work
remains, the loop stops.

```text
sprint file
  -> next unchecked task
  -> provider one-shot tick
  -> verification and receipt
  -> sprint file update
  -> continue or stop
```

## Sprint File Shape

```md
---
schema_version: aios.sprint_file.v1
repo: uri
repo_path: /home/user/workspaces/jaewon/myworld/uri
provider: codex
goal: Uri Sprint 008
verification: npm run typecheck && npm run build && npm test
---

# Uri Sprint 008

## Queue

- [ ] Add reflection card memory 후보 CTA
- [ ] Add self-ingest aria-disabled semantics
- [ ] Verify mobile bottom nav overlap

## Receipts
```

The only required queue syntax is GitHub-style checkboxes:

- `- [ ]` means pending
- `- [x]` means complete

## Commands

Create a sprint file:

```bash
python scripts/aios_sprint_loop.py init \
  --sprint-file .aios/sprints/uri/current.md \
  --repo uri \
  --repo-path /home/user/workspaces/jaewon/myworld/uri \
  --goal "Uri Sprint 008" \
  --task "Add reflection card memory 후보 CTA" \
  --json
```

Preview the next provider tick:

```bash
python scripts/aios_sprint_loop.py tick \
  --sprint-file .aios/sprints/uri/current.md \
  --json
```

Run one bounded provider tick:

```bash
python scripts/aios_sprint_loop.py tick \
  --sprint-file .aios/sprints/uri/current.md \
  --execute \
  --json
```

Use the AIOS runtime wrapper:

```bash
bin/aios --root . sprint-loop status --sprint-file .aios/sprints/uri/current.md --json
bin/aios --root . sprint-loop tick --sprint-file .aios/sprints/uri/current.md --json
```

## Stop Conditions

- The sprint file is missing or contains secret-like text.
- The repo path is wrong or outside the intended workspace.
- Provider execution times out.
- The provider returns non-zero.
- A task stays unchecked after execution and the provider did not write a
  blocker note.

## Boundary

This runner does not make Codex persistent. It makes AIOS persistent by keeping
state in the sprint file and receipts under `.aios/sprint_runs/`.

Provider execution remains bounded. Long-running loops belong to AIOS runtime,
round controller, Hive provider-loop, or a future contract with explicit stop
semantics.
