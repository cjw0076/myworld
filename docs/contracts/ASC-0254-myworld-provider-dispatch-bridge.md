---
contract_id: ASC-0254
slug: myworld-provider-dispatch-bridge
status: closed
goal: Let AIOS execute myworld-targeted provider dispatch packets through the watcher bridge so Claude/Codex/Gemini/local agents can perform bounded control-plane work without manual side channels.
created: 2026-06-13T15:42:00+09:00
accepted: 2026-06-13T15:42:00+09:00
closed: 2026-06-13T15:46:00+09:00
human_approved: true
origin: ASC-0252 showed that `aios_dispatch.py` can send `myworld` packets, but `scripts/aios_child_watcher.sh once --repo myworld` returns `unsupported repo: myworld`, forcing myworld-targeted Claude work into manual or external loops.
---

# ASC-0254 MyWorld Provider Dispatch Bridge

## Why Now

AIOS is supposed to operate like an agent company: MyWorld dispatches, provider
agents execute bounded work, result packets come back, and MemoryOS/ledger can
replay what happened. ASC-0252 proved a gap in that loop:

```text
scripts/aios_child_watcher.sh once --repo myworld
unsupported repo: myworld
```

That means a control-plane packet addressed to `claude@myworld` can be sent by
`aios_dispatch.py`, but the watcher bridge cannot execute it. For the founder's
goal, this is a real infrastructure blocker: service-readiness work must be
delegable to Claude without relying on untracked manual sessions.

This contract is not an end-user UI build. It is a narrow execution bridge
fix so future contracts such as ASC-0253 can be delegated and collected through
AIOS artifacts.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `tests/test_aios_child_watcher.py`
- `docs/contracts/ASC-0254-myworld-provider-dispatch-bridge.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/control/**`
- `apps/serving/**`
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work

1. Add `myworld` as a supported watcher target.
2. Resolve `repo_path myworld` to the workspace root.
3. Include `myworld` in watcher usage/status/all loops.
4. Add tests proving:
   - `scripts/aios_child_watcher.sh once --repo myworld` accepts a myworld
     packet and writes `.aios/outbox/myworld/<id>.myworld.result.json`;
   - the provider process runs from the myworld root;
   - `status` lists `myworld`;
   - existing child repo watcher behavior remains green.
5. Preserve current dirty submodules/untracked files and do not execute live
   provider credentials in tests.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_child_watcher -v
bash -n scripts/aios_child_watcher.sh
git diff --check
```

## Result

Closed.

`scripts/aios_child_watcher.sh` now supports `myworld`:

- `repo_path myworld` resolves to the workspace root;
- usage/status/start/stop `all` include `myworld`;
- myworld packets execute through the same provider-attempt and result-packet
  path as child repo packets.

Verification:

```bash
python3 -m unittest tests.test_aios_child_watcher -v
bash -n scripts/aios_child_watcher.sh
git diff --check
```

Focused tests passed 19/19, including
`test_myworld_packet_runs_from_workspace_root`.

## Stop Conditions

- `myworld_packet_executes_without_contract`
- `provider_auth_file_touched`
- `raw_provider_log_committed`
- `child_repo_scope_broadened`
- `apps_serving_implemented_before_visual_target`
