---
contract_id: ASC-0242
slug: packaging-smoke-and-credential-broker-adoption
status: closed
goal: Prove AIOS can run an isolated fresh-copy install smoke and route missing provider credentials through the credential broker instead of chat-secret prompts.
created: 2026-06-13T00:09:00+09:00
closed: 2026-06-13T00:09:00+09:00
origin: ASC-0241 closed live hosted-run proof; remaining deployment evidence included fresh-checkout install smoke and credential broker adoption.
---

# ASC-0242 Packaging Smoke And Credential Broker Adoption

## Why Now

AIOS has world-readiness markers and a deterministic live proof path, but a
service-grade AIOS cannot rely on one operator workstation. The next step is a
privacy-safe packaging smoke that proves installer behavior from a fresh copy
without touching the operator's real home/profile, and a provider credential
path that creates broker receipts instead of asking users to paste secrets.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_install.sh`
- `scripts/aios_packaging_proof.py`
- `scripts/aios_provider.py`
- `tests/test_aios_packaging_proof.py`
- `tests/test_aios_provider_credentials.py`
- `docs/contracts/ASC-0242-packaging-smoke-and-credential-broker-adoption.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `.aios/outbox/**`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- credential vault contents
- raw provider logs
- private history stores

## Result

`scripts/aios_install.sh` now supports dry-run and isolated smoke controls:

- `AIOS_INSTALL_DRY_RUN=1`
- `AIOS_SKIP_PIP=1`
- `AIOS_SHELL_RC=<temp path>`
- isolated `HOME`, `XDG_CONFIG_HOME`, and `AIOS_VAULT_DIR`

`scripts/aios_packaging_proof.py` copies the current source tree into a
temporary checkout-like directory while excluding runtime/private/heavy state
such as `.git`, `.aios`, `.runs`, `.local`, `node_modules`, `uri`, `gemini`,
`gemini-cli`, `artifacts`, and cache directories. It then runs the installer
in dry-run mode and verifies provider status from the copied root.

`scripts/aios_provider.py` now routes missing Claude API credentials through
`scripts/aios_credential_broker.py request --write --json`. The provider status
surface reports a broker receipt path and never prints credential values.

## Evidence

- `python3 -m unittest tests.test_aios_packaging_proof tests.test_aios_provider_credentials -v`
  passed 2/2.
- `python3 scripts/aios_packaging_proof.py --json` passed with
  `install_returncode=0`, `provider_status_returncode=0`, `copied_git_dir=false`,
  `copied_aios_runtime_state=false`, and `wrote_operator_shell_rc=false`.
- `python3 -m py_compile scripts/aios_packaging_proof.py scripts/aios_provider.py`
  passed.
- `bash -n scripts/aios_install.sh` passed.

## Boundaries

This closes privacy-safe install smoke and missing-credential broker adoption.
It does not claim a real package release, remote hosted worker backend, or
successful provider API execution with live credentials.

## Next

Continue with hosted backend selection and release packaging:

- choose first hosted worker backend or explicit local-only deployment tier;
- run install smoke from a clean committed tree or release archive;
- route provider credentials through broker refs for every hosted provider;
- produce a deployment/readiness report suitable for an operator checkpoint.
