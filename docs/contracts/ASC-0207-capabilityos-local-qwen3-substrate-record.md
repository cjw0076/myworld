---
contract_id: ASC-0207
slug: capabilityos-local-qwen3-substrate-record
status: closed
created: 2026-05-20T16:36:00+09:00
accepted: 2026-05-20T16:36:00+09:00
closed: 2026-05-20T16:41:00+09:00
accepted_by: codex_delegated_operator
origin: ASC-0205 CC5 requires a non-Claude/Codex substrate record; ASC-0206 proved local Ollama qwen3:8b generated advisory GenesisOS critic/analogy payloads.
goal: Record the local Ollama qwen3:8b substrate in the CapabilityOS recommendation matrix with ASC-0206 evidence, without granting CapabilityOS execution authority.
---

# ASC-0207 CapabilityOS Local Qwen3 Substrate Record

## Why Now

ASC-0205 CC5 requires provider diversification: a local or alternate provider
must do substantive work, CapabilityOS must record the substrate, and AIOS must
have a result packet. ASC-0206 produced a passed GenesisOS result packet where
local `ollama` model `qwen3:8b` generated advisory critic and analogy payloads
over ASC-0205.

CapabilityOS currently has an older recommendation-only Ollama Qwen 2.5 card,
but not the actual qwen3:8b substrate used in ASC-0206. This contract records
that observed substrate while preserving CapabilityOS's recommendation-only
boundary.

## Scope

repos:

- `CapabilityOS`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0207-capabilityos-local-qwen3-substrate-record.md`
- `docs/contracts/ASC-0205-aios-completion-north-star.md`
- `docs/AGENT_WORKLOG.md`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/tests/fixtures/capabilities.json`
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- provider auth files
- raw exports
- Hive, MemoryOS, GenesisOS implementation files
- any code that launches Ollama, downloads models, or executes providers

## Requirements

must_produce:

- A recommendation-only CapabilityOS card for local Ollama `qwen3:8b`.
- The card must have:
  - `executes_tools=false`
  - `requires_network=false`
  - `privacy=local`
  - evidence refs to ASC-0206 and `.aios/outbox/GenesisOS/asc-0206.GenesisOS.result.json`
- Default catalog and test fixture must remain in sync.
- A test must prove the qwen3 card exists and remains non-executing.
- CapabilityOS worklog must record the boundary: recommend only, no provider
  launch.

must_not:

- Start Ollama.
- Store provider credentials.
- Claim qwen3 is always available.
- Move execution authority into CapabilityOS.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py scripts/aios_monitor.py scripts/aios_local_app.py
python scripts/aios_local_app.py status --json --assert-live
cd CapabilityOS
python -m py_compile capabilityos/catalog.py capabilityos/schema.py capabilityos/cli.py
python -m unittest tests.test_cli -v
python -m capabilityos.cli show cap_ollama_qwen3_8b_local --json
python -m capabilityos.cli recommend --task "local ollama qwen3 genesis critique" --limit 5 --json
```

## Stop Conditions

- `capabilityos_executes_provider`
- `qwen3_card_missing`
- `catalog_fixture_drift`
- `provider_credentials_touched`
- `recommendation_boundary_broken`

## Receipts

- dispatch result: `.aios/outbox/CapabilityOS/asc-0207.CapabilityOS.result.json`
- myworld dispatch result: `.aios/outbox/myworld/asc-0207.myworld.result.json`
- dispatch status: `asc-0207` sent to `CapabilityOS`, child watcher passed,
  collected 2026-05-20T16:39:14+09:00; myworld watcher passed and collected
  after root-level gate replay.

## CapabilityOS Result Notes

- 2026-05-20 16:35 KST — codex@CapabilityOS:
  - semantic_handshake completed with `ambiguous_terms=[]`.
  - added recommendation-only `cap_ollama_qwen3_8b_local` to
    `CapabilityOS/capabilityos/catalog.py` and
    `CapabilityOS/tests/fixtures/capabilities.json`.
  - added a regression test proving `privacy=local`,
    `requires_network=false`, `executes_tools=false`, and ASC-0206 evidence
    refs.
  - verification passed:
    `python -m py_compile capabilityos/catalog.py capabilityos/schema.py capabilityos/cli.py`;
    `python -m unittest tests.test_cli -v`;
    `python -m capabilityos.cli show cap_ollama_qwen3_8b_local --json`;
    `python -m capabilityos.cli recommend --task "local ollama qwen3 genesis critique" --limit 5 --json`.
  - boundary: CapabilityOS did not start Ollama, download models, execute
    providers, open network connections, or touch credentials.
  - watcher result packet:
    `.aios/outbox/CapabilityOS/asc-0207.CapabilityOS.result.json`.
