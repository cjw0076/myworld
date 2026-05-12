---
contract_id: ASC-0044
slug: desktop-control-application
status: closed
goal: Provide a non-web native desktop AIOS control app for local monitor, contract, dispatch, repo, and route state.
created: 2026-05-12 19:20 KST
accepted: 2026-05-12 19:20 KST by codex acting operator
closed: 2026-05-12 19:31 KST
---

# ASC-0044 Desktop Control Application

## Why Now

The operator asked for a desktop application instead of the web/static control
surface. ASC-0039 and ASC-0040 remain useful as snapshot and local app
infrastructure, but AIOS needs a non-web native desktop entry point that does
not require a browser or HTTP server.

## AIOS Inputs Used

- MemoryOS context build:
  `trace_id=rtrace_47a2a93628dec7f2`, selected accepted memory
  `mem_90b5cfe6570e6ee2`.
- CapabilityOS route:
  `cap_capabilityos_recommendation`, `cap_web_research_route`,
  `cap_hivemind_execution_harness`, `cap_memoryos_import_run`, and
  `cap_memoryos_context_build`.
- Hive Mind dry-run:
  `run_20260512_192045_2b20d1`, `route_source=heuristic_fast`, prepared
  planner/executor/reviewer artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_desktop_app.py`
- `tests/test_aios_desktop_app.py`
- `docs/AIOS_CONTROL_APP.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0044-desktop-control-application.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.aios/logs/**`
- `.aios/state/**`
- `.aios/inbox/**`
- `.aios/outbox/**`
- `.env`
- raw export paths

## Responsibilities

### myworld.must_produce

- `scripts/aios_desktop_app.py` with:
  - `status --json`: report native desktop capability, display availability,
    snapshot path, and non-web mode.
  - `snapshot --json`: produce a headless view-model from the current control
    snapshot.
  - `launch`: start a native `tkinter` desktop window when a graphical display
    is available.
- Tests that work headless and prove the app does not require a browser or
  HTTP server.
- Docs showing the desktop command path next to the existing static/local app.

### child repos

- No source role in this contract.

## Verification Gate

```bash
python -m py_compile scripts/aios_desktop_app.py scripts/aios_control_snapshot.py
python -m unittest tests/test_aios_desktop_app.py
python scripts/aios_desktop_app.py status --json
python scripts/aios_desktop_app.py snapshot --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Desktop status reports `mode=native_desktop`.
- Desktop status reports `uses_http_server=false` and `uses_browser=false`.
- Headless tests pass without requiring `$DISPLAY`.
- `launch` is available for graphical sessions, but CI/headless verification
  does not require opening a window.
- Full tests pass and monitor remains clear.

## Stop Conditions

- `web_view_used`
- `http_server_required`
- `browser_required`
- `display_required_for_tests`
- `child_repo_source_edit`
- `verification_gate_failed`
- `monitor_not_clear`

## Receipts

- implementation:
  - `scripts/aios_desktop_app.py` adds native desktop `status`, `snapshot`,
    and `launch` commands.
  - `tests/test_aios_desktop_app.py` covers view-model extraction, non-web
    status, snapshot refresh, and headless CLI output.
  - `docs/AIOS_CONTROL_APP.md` documents the native desktop entry point.
- dispatch evidence:
  - `asc-0044` sent to `myworld`, watched, collected, and released with reason
    `asc_0044_desktop_control_application_verified`.
  - result packet:
    `.aios/outbox/myworld/asc-0044.myworld.result.json`.
- verification:
  - focused ASC-0044 tests passed 4/4.
  - `python scripts/aios_desktop_app.py status --json` reported tkinter
    available but no `$DISPLAY` in this shell; this is expected for headless
    verification.
  - full myworld suite passed 90/90.
  - final `python scripts/aios_monitor.py assess --write --json` returned
    `health=clear`.
