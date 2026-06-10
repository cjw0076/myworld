---
contract_id: ASC-0171
slug: hivemind-permissioned-dangerous-provider-execution
status: closed
goal: Allow Hive Mind to represent Codex dangerous full-access provider execution only as an explicit AIOS danger route with operator grant, irreversible authority, and proof receipts.
created: 2026-05-15 15:01 KST
accepted: 2026-05-15 15:01 KST
closed: 2026-05-15 15:06 KST
supersedes: ASC-0170 for dangerous/full-access behavior only
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: Hive Mind needs a complete AIOS execution surface, including a visible and auditable route for rare full-access provider execution instead of hidden manual bypass.
---

# ASC-0171 Hive Mind Permissioned Dangerous Provider Execution

## Why This Exists

ASC-0170 opened scoped Codex `workspace-write` execution but kept dangerous or
full-access modes blocked. That was correct for the first writable slice.

The next AIOS gap is different: if full automation sometimes requires a native
provider bypass, AIOS should not force the operator to leave the contract layer
and run it manually. The route must exist, but it must be more explicit than
normal writable execution.

## Scope

repos:

- `hivemind`
- `myworld`

allowed_files:

- `hivemind/hivemind/provider_passthrough.py`
- `hivemind/hivemind/provider_loop.py`
- `hivemind/hivemind/aios_packet_runner.py`
- `hivemind/hivemind/protocol.py`
- `hivemind/hivemind/harness.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_aios_packet_runner.py`
- `hivemind/tests/test_provider_passthrough.py`
- `hivemind/tests/test_protocol.py`
- `hivemind/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0171-hivemind-permissioned-dangerous-provider-execution.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `memoryOS/**`
- `CapabilityOS/**`
- `GenesisOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts

## Requirements

- Preserve read-only provider execution as the default.
- Preserve workspace-write as the normal writable route from ASC-0170.
- Keep dangerous full-access blocked unless all of these are present:
  - `--execute`
  - `--dangerous-full-access` or provider-loop `--allow-dangerous-full-access`
  - `--operator-grant <reason>`
  - grant text explicitly names `dangerous` and `full-access` or `full access`
- Support only Codex dangerous full-access in this slice.
- Reject simultaneous `--writable-provider-execution` and
  `--dangerous-full-access`.
- Record dangerous execution as:
  - `permission_mode=danger_full_access_with_policy`
  - `authority_class=provider_bypass_irreversible`
  - high risk
  - low reversibility
  - policy-gate `ask_user`
  - user/operator approval
  - execution proof and provider result receipt
- Keep approval-never and destructive shell-wrapper combinations blocked.

## Verification Gate

Run from `hivemind`:

```bash
python -m unittest tests.test_aios_packet_runner tests.test_provider_passthrough tests.test_protocol
python -m py_compile hivemind/aios_packet_runner.py hivemind/provider_passthrough.py hivemind/provider_loop.py hivemind/protocol.py hivemind/hive.py
```

Expected:

- no-grant dangerous packet is held with `operator_grant_missing`
- vague dangerous grant is held with `dangerous_operator_grant_not_explicit`
- dangerous provider passthrough without explicit grant is policy-blocked
- explicit dangerous grant produces a provider receipt and proof
- irreversible protocol intents close only when user/operator approval exists

## Stop Conditions

- `operator_grant_missing`
- `dangerous_operator_grant_not_explicit`
- `dangerous_requires_execute`
- `dangerous_provider_only_codex_supported`
- `conflicting_provider_permission_modes`
- `provider_tick_failed`
- `provider_secret_leak`
- `scope_violation`
- `verification_gate_failed`

## AIOS Role Evidence

- Hive Mind: implements the permissioned route, protocol authority, provider
  receipts, and tests.
- MemoryOS: not required for execution; may later remember accepted outcomes.
- CapabilityOS: should recommend this route only for high-freedom tasks and
  only with explicit operator permission.
- Operator: owns the high-risk grant text and may stop the route at any time.

## Work Packets

### WP-0171-A — Implement permissioned dangerous route

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-15
- accepted: 2026-05-15
- closed: 2026-05-15
- depends_on: ASC-0170
- brief: |
    Add a Codex dangerous full-access route that remains blocked by default,
    requires explicit dangerous grant language, records irreversible authority,
    and keeps proof/receipt artifacts. Update focused tests and close with the
    verification gate above.
- result: pending
- result: hivemind commit pending; verification passed 391 tests and
  `scripts/public-release-check.sh` 17/17.

## Result

Implemented a permissioned dangerous route:

```bash
python -m hivemind.hive aios-packet \
  --packet <packet.json> \
  --provider codex \
  --execute \
  --dangerous-full-access \
  --operator-grant "operator approved dangerous full-access for <scope>" \
  --json
```

Provider-loop also exposes:

```bash
python -m hivemind.hive provider-loop tick \
  --execute \
  --allow-dangerous-full-access \
  --dangerous-grant "operator approved dangerous full-access for <scope>" \
  --json
```

The route remains blocked by default. Vague grant text is held. The resulting
execution intent uses irreversible provider-bypass authority and requires
user/operator approval before execution can proceed.

Verification:

```bash
python -m unittest tests.test_aios_packet_runner tests.test_provider_passthrough tests.test_protocol
python -m unittest discover -s tests -p 'test_*.py'
bash scripts/public-release-check.sh
```

Observed result:

- focused tests passed 29/29.
- full Hive suite passed 391 tests.
- public release gate passed 17/17 with zero warnings.
