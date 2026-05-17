---
contract_id: ASC-0085
slug: codex-cli-aios-absorption
status: closed
goal: Record Codex CLI self-observation and install global Codex guidance so AIOS can absorb Codex as a provider substrate instead of relying on it as the final operator interface.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder direct instruction
closed: 2026-05-13 KST by codex@myworld
origin: founder asked whether blocked Claude caused inbox buildup, then directed Codex to continuously self-observe and leave reverse-engineering artifacts for AIOS and global Codex instructions.
---

# ASC-0085 Codex CLI AIOS Absorption

## Scope

repos:

- `myworld`
- user-level Codex configuration

allowed_files:

- `docs/AIOS_CODEX_CLI_ABSORPTION.md`
- `docs/discoveries/2026-05-13-operator-cli-role-distillation-dialogue.md`
- `docs/contracts/ASC-0085-codex-cli-aios-absorption.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `/home/user/.codex/AGENTS.md`

forbidden_files:

- `.env`
- `.env.*`
- raw export paths
- `/home/user/.codex/auth.json`
- `/home/user/.codex/history.jsonl`
- `/home/user/.codex/state_*.sqlite*`
- child repo source files

## Responsibilities

### myworld.must_produce

- Codex CLI absorption document.
- Completed TURN 2 in the Claude/Codex role-distillation dialogue.
- Global Codex AGENTS guidance that tells future Codex sessions to cooperate
  with AIOS and record provider observations.

### Hive Mind.must_use_later

- Treat the absorption map as input to ASC-0081 provider fallback binding.
- Treat empty provider output without a structured result as failure.

### CapabilityOS.must_use_later

- Record localized Codex auth-denied behavior as a capability observation.

### MemoryOS.must_use_later

- Preserve reviewed summaries, not raw provider stdout/stderr.

## Verification Gate

```bash
test -f /home/user/.codex/AGENTS.md
rg -n "AIOS|Codex CLI|접근 거부|pin_required_noninteractive|role_capsule" docs/AIOS_CODEX_CLI_ABSORPTION.md docs/discoveries/2026-05-13-operator-cli-role-distillation-dialogue.md /home/user/.codex/AGENTS.md
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Global Codex guidance exists.
- Codex TURN 2 is no longer pending.
- Absorption doc records the non-interactive Codex PIN/auth-denied behavior.
- Monitor has no new ASC-0085-specific alert.

## Stop Conditions

- `codex_secret_leak`
- `raw_history_ingested`
- `global_auth_file_modified`
- `child_repo_source_edit`
- `verification_gate_failed`

## Receipts

- `docs/AIOS_CODEX_CLI_ABSORPTION.md`
- `docs/discoveries/2026-05-13-operator-cli-role-distillation-dialogue.md`
- `/home/user/.codex/AGENTS.md`
- Verification summarized in `docs/AIOS_AGENT_LEDGER.md`.
