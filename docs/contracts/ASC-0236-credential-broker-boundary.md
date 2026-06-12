---
contract_id: ASC-0236
slug: credential-broker-boundary
status: closed
goal: Add a privacy-safe credential broker so AIOS can request provider credentials through receipts without printing values or repeatedly asking the user in chat.
created: 2026-06-13T00:08:00+09:00
closed: 2026-06-13T00:14:00+09:00
origin: ASC-0234 and ASC-0235 world-readiness gap: credential/private-data boundary is partial.
---

# ASC-0236 Credential Broker Boundary

## Why Now

AIOS has `scripts/aios_vault.py`, but the vault is a storage primitive. Agent
workflows also need a broker surface that says whether a named credential is
available, missing, or possibly in the vault without exposing the value. This
reduces the Claude-style usability failure where the agent repeatedly asks the
operator for sensitive information because it cannot distinguish "missing",
"present but private", and "route through trusted process".

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_credential_broker.py`
- `tests/test_aios_credential_broker.py`
- `docs/contracts/ASC-0236-credential-broker-boundary.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- raw provider logs
- credential vault contents
- private history stores
- child repo implementation files

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `kernel_primitive`
- owner_repo: `myworld`
- substrate_level: `primitive`
- surface_type: `contract`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `credential_request_receipt`
  - `privacy_redaction_receipt`
  - `focused_test_report`

## Result

Implemented `scripts/aios_credential_broker.py` with schema
`aios.credential_broker.v1`.

The broker:

- reports credential availability without values;
- distinguishes `available_via_env`, `vault_may_hold_value`, and `missing`;
- writes `.aios/credential_requests/<id>.json` receipts;
- marks `allowed_to_print_value=false`;
- marks `chat_secret_request_allowed=false`;
- never decrypts or prints vault contents.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_credential_broker -v
python3 -m py_compile scripts/aios_credential_broker.py
python3 scripts/aios_credential_broker.py --json status
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Stop Conditions

- `credential_value_in_prompt_or_doc`
- `raw_provider_history_leak`
- `vault_decrypts_for_status_probe`
- `chat_secret_request_allowed`
- `child_repo_implementation_without_dispatch`

## Next

Provider wrappers should consume broker receipts before falling back to raw
operator prompts. The next world-readiness bottlenecks remain MemoryOS Akashic
lineage and Hive runtime isolation.
