---
contract_id: ASC-0068
slug: global-project-agent-discovery
status: closed
goal: Let a global AIOS runtime discover project-local agent specifications across a workspace, normalize their authority boundaries, and produce ASC-0067-compatible invocation envelopes without taking broad filesystem control.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder/operator directive ("Contract 수행하자")
closed: 2026-05-13 KST by codex@myworld
acceptance_authority: founder/operator approval in chat
origin: founder clarified that AIOS should exist globally while many projects with local AGENTS.md specifications coexist in one filesystem or sandbox.
depends_on:
  - ASC-0054 global-aios-launcher
  - ASC-0067 unified-os-invocation-pipeline
---

# ASC-0068 Global Project Agent Discovery

## Why Now

The intended AIOS ecosystem is closer to the web or a distributed ledger than
to a single app folder. Many projects can live in one filesystem. Each project
may contain its own `AGENTS.md`, `.aios/` state, local worklogs, and ownership
language. A global AIOS runtime must discover those local agent laws before it
routes work.

ASC-0068 does not make AIOS a superuser over every directory. It creates a
discovery and authority-normalization layer: find project-local agent specs,
classify what AIOS may read or write, and emit an invocation envelope that
ASC-0067 can route through GenesisOS, MemoryOS, CapabilityOS, Hive, and
MyWorld.

## Scope

repos:

- `myworld`

read_targets:

- project-local `AGENTS.md`
- project-local `CLAUDE.md`
- project-local `CODEX.md`
- project-local `.aios/manifest.json`
- project-local `.aios/inbox/`
- project-local `.aios/outbox/`
- project-local `docs/AGENT_WORKLOG.md`
- project-local `docs/WORKSTREAMS.md`
- project-local `docs/TODO.md`

allowed_files:

- `scripts/aios_project_discovery.py`
- `tests/test_aios_project_discovery.py`
- `tests/fixtures/project_discovery/`
- `docs/AIOS_GLOBAL_PROJECT_DISCOVERY.md`
- `docs/contracts/ASC-0068-global-project-agent-discovery.md`
- `docs/contracts/README.md`
- `bin/aios`
- `scripts/aios_launcher.py`
- `tests/test_aios_launcher.py`

forbidden_files:

- child project source edits
- raw exports
- private transcripts
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.env`
- `.env.*`
- `**/*secret*`
- `**/*credential*`
- `**/*token*`
- `.aios/logs/**` in committed output
- symlink traversal outside the requested scan root
- network access
- provider execution
- MemoryOS import or acceptance
- CapabilityOS tool execution
- Hive provider run execution

## Discovery V1

Commands:

```bash
python scripts/aios_project_discovery.py scan --root /home/user/workspaces/jaewon --json
python scripts/aios_project_discovery.py invoke --project <project_root> --goal "<goal>" --plan-only --json
bin/aios discover --root /home/user/workspaces/jaewon --json
```

Runtime output directory:

```text
.aios/discovery/
  projects.json
  <project_id>/
    agent_profile.json
    authority.json
    semantic_handshake.json
    invocation_envelope.json
```

The runtime output is local state and must not be committed.

## Project Profile Schema

`agent_profile.json` must use schema `aios.project_profile.v1` and include:

- `project_id`: stable hash derived from canonical project root.
- `project_root`: absolute canonical path.
- `control_plane_root`: resolved MyWorld root.
- `agent_specs`: discovered local instruction files with hashes.
- `local_aios_state`: whether `.aios/inbox` and `.aios/outbox` exist.
- `declared_roles`: project-local role names and ownership notes.
- `verification_surfaces`: discovered test/check commands when declared.
- `forbidden_paths`: merged hard-ban paths from AIOS plus local specs.
- `write_authority`: default `none` unless a contract or local spec grants it.
- `status`: `usable|degraded|checkpoint_required|blocked`.
- `reasons`: why the profile received that status.

`authority.json` must use schema `aios.project_authority.v1` and include:

- `may_read`
- `may_write`
- `must_not_read`
- `must_not_write`
- `requires_contract`
- `requires_operator_checkpoint`
- `stop_conditions`

`semantic_handshake.json` must use schema `aios.semantic_handshake.v1` and
include:

- `project_terms`: local names for agents, roles, repos, and verification.
- `aios_terms`: normalized AIOS terms.
- `ambiguities`: terms whose meaning differs from AIOS defaults.
- `checkpoint_required`: true when ambiguity affects ownership or authority.

`invocation_envelope.json` must be ASC-0067-compatible and include:

- `goal`
- `project_profile_ref`
- `authority_ref`
- `semantic_handshake_ref`
- `requested_mode: plan_only`
- `required_os_roles: [GenesisOS, memoryOS, CapabilityOS, hivemind, myworld]`
- `stop_conditions`
- `next_command`: proposed `scripts/aios_invoke.py` command

## Per-OS Responsibility

### MyWorld.must_produce

- `scripts/aios_project_discovery.py`
- `tests/test_aios_project_discovery.py`
- `docs/AIOS_GLOBAL_PROJECT_DISCOVERY.md`
- project profile, authority, semantic handshake, and invocation envelope
  artifacts.

MyWorld may discover, normalize, and issue plan-only envelopes. It must not
edit discovered project source files.

### GenesisOS.must_receive

- The normalized goal and semantic ambiguities.
- It may later generate divergent branches through ASC-0067.
- It receives no filesystem authority from discovery alone.

### MemoryOS.must_receive

- The project profile and source hashes as context request input.
- It may later retrieve accepted context or write draft candidates through a
  separate accepted contract.
- It must not import project data during discovery.

### CapabilityOS.must_receive

- The authority profile and requested goal.
- It may recommend tools, providers, MCPs, skills, and fallback routes.
- It must remain recommendation-only.

### Hive.must_receive

- The invocation envelope and authority boundaries.
- It may plan execution only after ASC-0067 produces a bounded Hive plan.
- It must not run providers from discovery alone.

## Verification Gate

```bash
python -m py_compile scripts/aios_project_discovery.py scripts/aios_launcher.py
python -m unittest tests/test_aios_project_discovery.py
python -m unittest tests/test_aios_launcher.py
python scripts/aios_project_discovery.py scan --root tests/fixtures/project_discovery/workspace --json
python scripts/aios_project_discovery.py invoke --project tests/fixtures/project_discovery/workspace/project_alpha --goal "ship a local feature through AIOS" --plan-only --json
bash bin/aios discover --root tests/fixtures/project_discovery/workspace --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- The scan discovers only fixture projects that contain recognized agent specs
  or `.aios` manifests.
- `project_id` is deterministic across repeated scans.
- Hard-ban paths and secret patterns are excluded and reported as blocked
  rather than silently scanned.
- Symlinks that escape the scan root are blocked.
- A project without `AGENTS.md` can be listed only as `degraded`; it cannot
  receive write authority.
- Conflicting local instructions produce `checkpoint_required`.
- `authority.json` defaults to `may_write=[]`.
- `invocation_envelope.json` is valid input for ASC-0067 plan-only mode.
- No discovered project source file is modified by scan or invoke.
- `bin/aios discover` and direct script output agree on project ids and
  statuses.
- Full AIOS tests pass and monitor health is not worsened by discovery
  artifacts.

Required unit-test fixtures:

- `project_alpha`: valid `AGENTS.md` and `.aios` inbox/outbox.
- `project_beta`: `CLAUDE.md`/`CODEX.md` only, degraded until `AGENTS.md`
  exists.
- `project_conflict`: two local specs with conflicting write authority.
- `project_secret`: contains `.env` and secret-like paths that must be blocked.
- `project_symlink_escape`: symlink outside scan root that must be blocked.
- `project_no_aios`: ordinary project that may be observed but not invoked.

Required negative tests:

- discovery cannot read hard-ban files.
- discovery cannot write outside `.aios/discovery/`.
- invoke cannot set `requested_mode` to execution by default.
- invoke cannot omit ASC-0067 required OS roles.
- launcher cannot resolve an unrelated directory as MyWorld without `AIOS_HOME`
  or explicit `--root`.

## Stop Conditions

- `hard_ban_path_read`
- `secret_pattern_scanned`
- `symlink_escape`
- `write_authority_without_contract`
- `project_source_modified`
- `ambiguous_agent_spec`
- `missing_project_profile`
- `missing_authority_profile`
- `missing_invocation_envelope`
- `asc_0067_incompatible_envelope`
- `network_access_attempted`
- `provider_execution_attempted`
- `verification_gate_failed`

## Receipts

- implementation: `scripts/aios_project_discovery.py`,
  `scripts/aios_launcher.py`, `bin/aios`,
  `tests/test_aios_project_discovery.py`, `tests/test_aios_launcher.py`,
  `tests/fixtures/project_discovery/`, and
  `docs/AIOS_GLOBAL_PROJECT_DISCOVERY.md`
- local verification:
  - `python -m py_compile scripts/aios_project_discovery.py scripts/aios_launcher.py`
  - `python -m unittest tests/test_aios_project_discovery.py tests/test_aios_launcher.py`
  - `python scripts/aios_project_discovery.py scan --root tests/fixtures/project_discovery/workspace --json`
  - `python scripts/aios_project_discovery.py invoke --project tests/fixtures/project_discovery/workspace/project_alpha --goal "ship a local feature through AIOS" --plan-only --json`
  - `bash bin/aios discover --root tests/fixtures/project_discovery/workspace --json`
- dispatch receipt: `.aios/outbox/myworld/asc-0068.myworld.result.json`
  with `status=passed`.

## Work Packets

### WP-0068-A — codex@myworld implements project discovery

- target_agent: codex
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- depends_on: ASC-0067 accepted or explicitly allowed as parallel
- brief: |
    Implement the global project discovery CLI, fixtures, tests, and docs.
    Discovery is read-only across projects and may write only local runtime
    artifacts under `.aios/discovery/`. It must produce an ASC-0067-compatible
    invocation envelope but must not execute child repo agents or providers.
- return_to: `.aios/outbox/myworld/asc-0068.myworld.result.json`
- result: `.aios/outbox/myworld/asc-0068.myworld.result.json`

### WP-0068-B — claude@myworld reviews ecosystem and authority wording

- target_agent: claude
- target_repo: myworld
- status: superseded
- depends_on: WP-0068-A
- brief: |
    Review whether the discovery layer preserves the distinction between AIOS
    global presence and local authority. Check privacy wording, semantic
    handshake fields, ecosystem framing, and stop conditions.
- return_to: `.aios/outbox/myworld/asc-0068.claude-review.result.json`
- result: not executed in this contract closeout; wording review can be
  reopened as a separate review packet if operator wants a policy pass.

### WP-0068-C — codex@myworld wires launcher discover command

- target_agent: codex
- target_repo: myworld
- status: done
- closed: 2026-05-13 KST
- depends_on: WP-0068-A
- brief: |
    Add `bin/aios discover --root ... --json` through the existing launcher
    path. The launcher must not bypass MyWorld root resolution or grant write
    authority. Verify parity with direct `aios_project_discovery.py scan`.
- return_to: `.aios/outbox/myworld/asc-0068.launcher.result.json`
- result: covered by `.aios/outbox/myworld/asc-0068.myworld.result.json`
