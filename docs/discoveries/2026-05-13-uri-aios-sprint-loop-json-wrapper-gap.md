# Uri AIOS Sprint-Loop JSON Wrapper Gap

- date: 2026-05-13 KST
- observed by: codex@uri as AIOS Executor
- source repo: `/home/user/workspaces/jaewon/myworld/uri`
- related sprint: Uri `URI-030` Sprint 016

## Observation

During Uri Sprint 016, the direct AIOS sprint-loop script worked as the durable
receipt primitive, but the launcher wrapper path returned a JSON parse failure:

```bash
/home/user/workspaces/jaewon/myworld/bin/aios --root /home/user/workspaces/jaewon/myworld sprint-loop tick \
  --sprint-file /home/user/workspaces/jaewon/myworld/uri/.aios/sprints/URI-030-sprint-016-school-calendar-season-chip.md \
  --execute --mark-complete-on-success --provider-command true --json
```

The wrapper emitted:

```text
parse_error: Expecting value: line 1 column 1 (char 0)
```

The underlying sprint-loop primitive still wrote receipts and marked the sprint
file. Running the script directly also succeeded:

```bash
python /home/user/workspaces/jaewon/myworld/scripts/aios_sprint_loop.py \
  --root /home/user/workspaces/jaewon/myworld tick \
  --sprint-file /home/user/workspaces/jaewon/myworld/uri/.aios/sprints/URI-030-sprint-016-school-calendar-season-chip.md \
  --execute --mark-complete-on-success --provider-command true
```

## Why It Matters

For the AIOS Executor pattern, `bin/aios` should be the stable primitive surface.
If the wrapper cannot reliably pass `--json` through subcommands with
`--provider-command nargs=REMAINDER`, agents will either bypass the wrapper or
write duplicate/early receipts. That weakens AIOS as the authoritative runtime.

## Suggested Fix

- Add a regression test for `bin/aios sprint-loop tick --json` with
  `--provider-command true`.
- Ensure wrapper-level `--json` is consumed by the sprint-loop command, not
  swallowed into the provider command remainder.
- Consider a separate `--provider-command-json` or `--` delimiter convention so
  provider command args cannot capture AIOS control flags.

## Workaround Used

Uri Sprint 016 continued using the direct sprint-loop script and then recorded
actual implementation evidence in Uri Hive/Memory/Capability artifacts.
