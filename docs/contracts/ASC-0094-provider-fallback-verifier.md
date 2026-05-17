---
contract_id: ASC-0094
slug: provider-fallback-verifier
status: closed
goal: Add a Hive-owned verifier that decides whether fallback provider output can be promoted from draft/attempt to completed work.
created: 2026-05-13T11:32:05+09:00
accepted: 2026-05-13T11:32:05+09:00
closed: 2026-05-13T11:35:11+09:00
origin: ASC-0081 closed with local/Gemini fallback substrates but no promotion verifier.
---

# ASC-0094 Provider Fallback Verifier

## Why Now

ASC-0081 made `codex`, `claude`, `gemini`, and `local` visible as fallback
substrates. It intentionally did not claim those substrates are equivalent. The
remaining gap is a Hive-owned verifier receipt that decides whether a fallback
attempt may be promoted to completed work.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0094-provider-fallback-verifier.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`
- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_provider_loop.py`
- `hivemind/docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials, PINs, tokens, keychains, auth stores, and shell history
- raw provider stdout/stderr bodies in shared docs or result packets
- MemoryOS accepted memory files
- CapabilityOS route scoring files

## Responsibilities

### hivemind.must_produce

- `hive.provider_fallback_verification.v1` receipt.
- CLI surface under `hive provider-loop verify-fallback`.
- Deterministic checks:
  - original worker is degraded
  - original worker has a role capsule
  - fallback worker is not the same provider
  - fallback provider appears in `fallback_candidates`
  - fallback worker has a completed/passed/done status before promotion
  - `local` fallback cannot promote without an independent verifier provider
- Tests for promotion, local verifier hold, and CLI JSON output.

### myworld.must_produce

- Contract record, dispatch result collection, ledger closeout, and monitor
  evidence.

### capabilityos

- No role in this contract. ASC-0081 already expanded route candidates.

### memoryos

- No accepted memory change in this contract. Later contracts may write memory
  drafts from fallback verification observations.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_provider_loop.py -v
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- The verifier can promote a non-local fallback only when the original degraded
  worker has a role capsule and the fallback worker completed.
- The verifier holds local fallback without an independent verifier provider.
- The verifier writes a receipt path and JSON CLI output.
- Final monitor is clear or has only unrelated pre-existing control-plane
  source dirtiness.

## Stop Conditions

- `missing_role_capsule`
- `original_worker_not_degraded`
- `fallback_provider_not_recommended`
- `fallback_worker_not_completed`
- `local_fallback_without_independent_verifier`
- `same_provider_fallback`
- `provider_secret_leak`
- `verification_gate_failed`

## Work Packets

### WP-0094-A — Hive fallback promotion verifier

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-13
- accepted: 2026-05-13
- closed: 2026-05-13
- depends_on: ASC-0081
- brief: |
    Implement `hive provider-loop verify-fallback` and a
    `hive.provider_fallback_verification.v1` receipt in Hive. The verifier is
    deterministic and artifact-based; it does not execute provider CLIs or read
    raw provider output bodies.

    Required reading:
    - `/home/user/workspaces/jaewon/myworld/AGENTS.md`
    - `/home/user/workspaces/jaewon/myworld/docs/AIOS_AGENT_INTERFACE.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0081-provider-fallback-execution-binding.md`
    - `/home/user/workspaces/jaewon/myworld/docs/contracts/ASC-0094-provider-fallback-verifier.md`
    - `/home/user/workspaces/jaewon/myworld/hivemind/AGENTS.md`

    Allowed files:
    - `hivemind/hivemind/provider_loop.py`
    - `hivemind/hivemind/hive.py`
    - `hivemind/tests/test_provider_loop.py`
    - `hivemind/docs/AGENT_WORKLOG.md`

    Verification:
    `cd /home/user/workspaces/jaewon/myworld/hivemind && python -m pytest tests/test_provider_loop.py -v`
- result: `.aios/outbox/hivemind/asc-0094.hivemind.result.json`; repo
  commit `6e0bde1`.

## Receipts

- Hive result: `.aios/outbox/hivemind/asc-0094.hivemind.result.json`
- MyWorld result: `.aios/outbox/myworld/asc-0094.myworld.result.json`
- Hive repo durability commit: `6e0bde1`
- Verification:
  - `python -m py_compile hivemind/provider_loop.py hivemind/hive.py`
  - `python -m pytest tests/test_provider_loop.py -v`
  - `python scripts/aios_monitor.py assess --json` returned `health=clear`.
