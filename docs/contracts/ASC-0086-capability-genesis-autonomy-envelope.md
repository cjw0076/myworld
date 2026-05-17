---
contract_id: ASC-0086
slug: capability-genesis-autonomy-envelope
status: proposed
goal: Give CapabilityOS and GenesisOS higher freedom inside explicit non-destructive autonomy envelopes so AIOS can discover routes, generate alternatives, and challenge assumptions without waiting for narrow operator prompts.
created: 2026-05-13 KST
accepted:
closed:
origin: founder observed that strict agent role limits hid easy causes like PIN-gated Codex CLI and argued CapabilityOS/GenesisOS need much higher freedom.
---

# ASC-0086 Capability + Genesis Autonomy Envelope

## Why Now

The previous loop over-constrained agents. A simple provider cause,
`pin_required_noninteractive`, was discoverable by probing Codex with a TTY,
but the system treated provider failure as a generic blocked output and let
work accumulate. CapabilityOS and GenesisOS should be allowed to explore,
classify, and propose more aggressively while still staying non-destructive.

## Scope

repos:

- `myworld`
- `CapabilityOS`
- `GenesisOS`

allowed_files:

- `docs/contracts/ASC-0086-capability-genesis-autonomy-envelope.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `CapabilityOS/docs/AUTONOMY_ENVELOPE.md`
- `CapabilityOS/capabilityos/autonomy.py`
- `CapabilityOS/tests/test_autonomy.py`
- `GenesisOS/docs/AUTONOMY_ENVELOPE.md`
- `GenesisOS/genesisos/autonomy.py`
- `GenesisOS/tests/test_autonomy.py`

forbidden_files:

- `.env`
- `.env.*`
- raw export paths
- provider credential files
- direct writes to `hivemind/**`, `memoryOS/**`, or product repo source
- network execution or install/bind actions without a separate accepted
  BindingPlan

## Autonomy Levels

### CapabilityOS.high_freedom

Allowed without operator pre-approval:

- probe local command availability with harmless help/version/status commands
- classify provider failures with locale-aware patterns
- search local registries, docs, and observed result packets
- draft route/fallback plans
- emit capability gaps and observations
- recommend an operator unlock, alternate provider, or local LLM fallback

Still forbidden:

- executing implementation work
- installing tools
- writing credentials
- calling paid/network APIs unless an accepted contract explicitly allows it
- accepting memory

### GenesisOS.high_freedom

Allowed without operator pre-approval:

- generate divergent branches
- mutate assumptions
- challenge contract scope
- propose semantic translations
- create non-language reasoning artifacts such as diagrams, tables, and
  constraint graphs
- produce pre-close challenge reports

Still forbidden:

- selecting the final branch alone
- closing contracts
- editing child repo implementation files
- overriding Hive verification
- turning speculative seeds into accepted memory

## Required Outputs

- CapabilityOS autonomy envelope doc and classifier tests.
- GenesisOS autonomy envelope doc and challenge/autonomy tests.
- MyWorld update that explains the freedom boundary in plain terms.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_autonomy.py -v
cd /home/user/workspaces/jaewon/myworld/GenesisOS
python -m pytest tests/test_autonomy.py -v
cd /home/user/workspaces/jaewon/myworld
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- CapabilityOS can classify `pin_required_noninteractive` from Korean Codex
  output and recommend unlock/fallback without executing implementation.
- GenesisOS can generate at least three alternative interpretations of a
  provider failure and mark each as speculative until verified.
- Both envelopes explicitly forbid credentials, installs, child repo source
  edits, and memory acceptance.

## Stop Conditions

- `capabilityos_executes_work`
- `genesisos_closes_contract`
- `credential_or_pin_persisted`
- `network_binding_without_contract`
- `child_repo_source_edit`
- `verification_gate_failed`
