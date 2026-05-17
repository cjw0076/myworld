---
contract_id: ASC-0166
slug: provider-pin-required-classification
status: closed
goal: Classify provider PIN/auth unlock failures without storing secrets, so AIOS watchers can route or checkpoint instead of treating PIN-gated providers as generic access denied.
created: 2026-05-14 12:55 KST
accepted: 2026-05-14 12:55 KST
closed: 2026-05-14 12:53 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: ASC-0165 child watcher evidence showed Codex and Claude provider execution blocked on PIN/access or rate limit; founder asked whether PIN should be stored in .env or removed.
---

# ASC-0166 Provider PIN-Required Classification

DNA references: Invariant 5 (provenance chain), Invariant 6 (operator
override remains possible), Invariant 7 (private-gated data stays out of
dispatch and prompt artifacts).

## Plain Language

Do not put provider PINs in repo `.env`, docs, contracts, packets, logs, or
code. AIOS should first recognize that a provider is PIN-gated, then either
fallback to another provider or stop at an operator unlock checkpoint.

This contract does not solve secret storage. It prevents the current false
classification where localized PIN prompts become generic
`provider_access_denied`.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_child_watcher.sh`
- `scripts/aios_pingpong.sh`
- `tests/test_aios_child_watcher.py`
- `tests/test_aios_pingpong.py`
- `docs/contracts/ASC-0166-provider-pin-required-classification.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts
- child repo source files

## Requirements

- Classify logs containing localized PIN failure symptoms such as
  `틀렸습니다.` as `pin_required_noninteractive`.
- Keep plain `접근 거부.` without PIN-attempt evidence as
  `provider_access_denied`.
- Treat `pin_required_noninteractive` as fallback-eligible in child watcher
  and pingpong loops.
- Do not store, echo, or document any actual PIN value.
- Preserve existing provider access denied and provider backpressure behavior.

## Verification Gate

```bash
bash -n scripts/aios_child_watcher.sh
bash -n scripts/aios_pingpong.sh
python -m unittest tests/test_aios_child_watcher.py tests/test_aios_pingpong.py
```

Pass criteria:

- PIN-attempt logs classify as `pin_required_noninteractive`.
- Fallback still proceeds to the next provider.
- Generic Korean access denied continues to classify as
  `provider_access_denied`.
- No secret value is added to any tracked or generated artifact.

## Stop Conditions

- `secret_written_to_repo`
- `pin_logged_in_artifact`
- `fallback_regression`
- `provider_access_denied_regression`
- `verification_gate_failed`

## Work Packet

### WP-0166-A — myworld provider PIN failure classifier

- target_agent: codex
- target_repo: myworld
- status: closed
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14 12:53 KST
- brief: |
    Update watcher and pingpong failure classification so PIN-required
    non-interactive provider failures become a named category without storing
    any secret. Verify fallback behavior and existing access-denied behavior.
- result: passed. PIN-attempt logs are now classified as
    `pin_required_noninteractive`, fallback remains enabled for that category,
    generic Korean access-denied remains `provider_access_denied`, and no
    provider PIN or credential value was stored.

## Receipts

- action_policy: initial dispatch send escalated with
  `human_checkpoint_required:uses_credentials`; this was expected because the
  contract discusses credentials. No secret was handled.
- watcher result: `.aios/outbox/myworld/asc-0166.myworld.result.json`, status
  `passed`.
- environment change: `/home/user/bin/codex` now directly executes
  `/home/user/.nvm/versions/node/v22.22.2/bin/codex`, bypassing the prior
  local PIN-gate loader. The hidden loader config was not printed, copied, or
  stored.
- smoke: `codex --help` returned the Codex CLI help; `timeout 60 codex exec
  --dangerously-bypass-approvals-and-sandbox "Print exactly:
  AIOS_CODEX_READY"` returned `AIOS_CODEX_READY`.
- release: final release wrote MemoryOS draft `mem_9ebe54e652676ea2`.
- verification:
  - `bash -n scripts/aios_child_watcher.sh` passed.
  - `bash -n scripts/aios_pingpong.sh` passed.
  - `python -m unittest tests/test_aios_child_watcher.py tests/test_aios_pingpong.py`
    passed 15/15.
