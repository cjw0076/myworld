---
contract_id: ASC-0095
slug: provider-output-projection
status: closed
goal: Add a redacted Hive provider-output projection receipt so future semantic quality checks can reason over provider results without copying raw output bodies.
created: 2026-05-13T11:56:17+09:00
accepted: 2026-05-13T11:56:17+09:00
closed: 2026-05-13T12:00:08+09:00
origin: ASC-0094 closed with artifact-level fallback promotion but deferred semantic/provider-output quality checks until redaction boundaries exist.
---

# ASC-0095 Provider Output Projection

## Why Now

ASC-0094 can promote a fallback provider attempt using artifact-level receipts.
The next semantic quality layer needs evidence about provider output, but raw
stdout/stderr/provider bodies cannot be copied into shared control-plane or
review artifacts. This contract adds the missing redacted projection layer.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0095-provider-output-projection.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`
- `hivemind/hivemind/provider_projection.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_provider_projection.py`
- `hivemind/docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- raw provider stdout/stderr bodies in shared docs or result packets
- provider credentials, PINs, tokens, keychains, auth stores, and shell history
- MemoryOS accepted memory files
- CapabilityOS route scoring files

## Responsibilities

### hivemind.must_produce

- `hive.provider_output_projection.v1` JSON artifact.
- CLI surface that writes the projection for a run.
- Projection rows for provider result receipts containing:
  - provider, role, status, provider_mode, permission_mode, returncode
  - relative receipt ref
  - output/stdout/stderr path refs only when explicitly requested
  - byte/line counts and presence flags
  - policy violation count
  - privacy flags proving raw bodies were not copied
- Tests proving raw provider body strings are excluded.

### myworld.must_produce

- Contract record, dispatch result collection, ledger closeout, and monitor
  evidence.

### capabilityos

- No role in this contract.

### memoryos

- No accepted memory change in this contract. Later writeback may import the
  projection summary as a draft.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_provider_projection.py -v
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Projection artifact exists and has schema `hive.provider_output_projection.v1`.
- Raw provider stdout/stderr/output body strings do not appear in projection
  JSON.
- Projection includes size/count metadata sufficient for later quality checks.
- Final monitor is clear or has only unrelated pre-existing control-plane
  source dirtiness.

## Stop Conditions

- `raw_provider_body_in_projection`
- `provider_secret_leak`
- `projection_missing_receipt_ref`
- `projection_missing_privacy_flags`
- `verification_gate_failed`

## Work Packets

### WP-0095-A — Hive redacted provider-output projection

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-13
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: ASC-0094
- brief: |
    Implement a Hive CLI surface that writes
    `hive.provider_output_projection.v1` for one run. The projection must never
    include raw stdout/stderr/output provider bodies. It may include relative
    refs, sizes, counts, statuses, and policy metadata.

    Required reading:
    - `/home/user/workspaces/jaewon/myworld/AGENTS.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0094-provider-fallback-verifier.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0095-provider-output-projection.md`
    - `/home/user/workspaces/jaewon/myworld/hivemind/AGENTS.md`

    Allowed files:
    - `hivemind/hivemind/provider_projection.py`
    - `hivemind/hivemind/hive.py`
    - `hivemind/tests/test_provider_projection.py`
    - `hivemind/docs/AGENT_WORKLOG.md`

    Verification:
    `cd /home/user/workspaces/jaewon/myworld/hivemind && python -m pytest tests/test_provider_projection.py -v`
- result: `.aios/outbox/hivemind/asc-0095.hivemind.result.json`; repo
  commit `9779595`.

## Receipts

- Hive result: `.aios/outbox/hivemind/asc-0095.hivemind.result.json`
- MyWorld result: `.aios/outbox/myworld/asc-0095.myworld.result.json`
- Hive repo durability commit: `9779595`
- Verification:
  - `python -m py_compile hivemind/provider_projection.py hivemind/hive.py`
  - `python -m pytest tests/test_provider_projection.py -v`
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
