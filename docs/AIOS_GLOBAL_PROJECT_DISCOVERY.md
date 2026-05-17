# AIOS Global Project Discovery

ASC-0068 lets a global AIOS runtime discover project-local agent
specifications without taking broad filesystem control.

Commands:

```bash
python scripts/aios_project_discovery.py scan --root /home/user/workspaces/jaewon --json
python scripts/aios_project_discovery.py invoke --project /path/to/project --goal "ship a local feature through AIOS" --plan-only --json
bin/aios discover --root /home/user/workspaces/jaewon --json
```

Discovery writes runtime state under `.aios/discovery/`:

- `projects.json`
- `<project_id>/agent_profile.json`
- `<project_id>/authority.json`
- `<project_id>/semantic_handshake.json`
- `<project_id>/invocation_envelope.json` after `invoke`

The default authority is conservative:

- discovery may read local instruction files and declared work surfaces;
- discovery must not read hard-banned paths, secret-like paths, raw exports, or
  symlink escapes;
- discovery does not execute providers, network calls, Hive runs, MemoryOS
  imports, or CapabilityOS tools;
- invocation is `plan_only` unless a later accepted contract grants execution.

Project status meanings:

- `usable`: an `AGENTS.md` exists and no authority ambiguity or hard-ban stop
  condition was detected.
- `degraded`: some local AIOS/provider instructions exist, but `AGENTS.md` is
  missing.
- `checkpoint_required`: local specs conflict on authority semantics.
- `blocked`: discovery found hard-ban or symlink escape conditions.
