---
contract_id: ASC-0090
slug: agent-identity-registry
status: closed
goal: Replace ad-hoc `<agent>@<host>` social-convention strings with a stable per-agent identity registry so observations, contracts, packets, and ledger entries cite a real id with capabilities + substrate + public-key seed (swarm-ready).
created: 2026-05-13 KST
proposed_by: claude@myworld (operator)
accepted: 2026-05-13 KST by codex acting founder-delegated operator as prerequisite for accepted ASC-0107
closed: 2026-05-13 21:25 KST by codex acting founder-delegated operator
acceptance_authority: codex@myworld under founder-delegated AIOS operator loop.
origin: founder verification 2026-05-13 KST that AIOS has no formal agent identity registry — only social conventions like `claude@myworld`, `codex@hivemind`. Confirmed by claude scan: no `agent_registry` file exists. Cited as Q4 in founder turn alongside the 5-layer Claude Code session reverse-engineering.
---

# ASC-0090 Agent Identity Registry

## Why Now

Right now agents are identified by ad-hoc strings in commit author
fields, contract `acceptance_authority` lines, ledger entries, and
self-observation logs. Strings like `claude@myworld`, `codex@hivemind`,
`codex@CapabilityOS`. There is no:

- Canonical list of valid agent ids
- Capabilities-per-agent record
- Substrate metadata (Claude Code / Codex CLI / Ollama Qwen / etc.)
- Public-key seed (foundation for sovereign-swarm signing later)
- Way to detect "wait, who is this `claude@somewhere-else`?"

ASC-0090 introduces `~/.aios/agents.json` (per machine) + a
`docs/AIOS_AGENTS_REGISTRY.md` (per workspace) that lists every
known agent. New agents register via CLI; observations + contracts
validate against the registry.

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_agent_registry.py`
- `tests/test_aios_agent_registry.py`
- `docs/AIOS_AGENTS_REGISTRY.md`
- `docs/contracts/ASC-0090-agent-identity-registry.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `aios_agent_registry.py` CLI:
  - `register --id <slug> --substrate <claude_code|codex_cli|ollama|...>
    --capabilities <list>` → writes registry entry
  - `list --json`
  - `verify <agent_id>` → returns valid/unknown
  - `current` → infers identity of running session from environment (best
    effort)
- Registry entry schema:
  ```yaml
  agent_id: <slug>
  substrate: claude_code | codex_cli | ollama_qwen25_7b | gemini | ...
  capabilities: [operator, reviewer, drafter, critic, child_agent, ...]
  public_key_seed: null  # placeholder for sovereign swarm later
  registered_at: <iso>
  registered_by: <prior agent or self-bootstrap>
  ```
- Validation hook: any contract `acceptance_authority` line citing an
  agent_id should pass `verify`. (Optional warning, not error, in V1.)
- Tests: register/list/verify/current paths.

### child repos: no source change.

## Verification Gate

```bash
python -m unittest tests/test_aios_agent_registry.py
python scripts/aios_agent_registry.py register --id claude_at_myworld_dev --substrate claude_code --capabilities operator,reviewer
python scripts/aios_agent_registry.py list --json
python scripts/aios_agent_registry.py verify claude_at_myworld_dev
python -m unittest discover -s tests -p 'test_aios_*.py'
```

## Stop Conditions

- `registry_blocks_existing_agents`: existing string ids must not
  invalidate retroactively (V1 is opt-in)
- `registry_writes_outside_aios`: only writes to `~/.aios/` and
  `docs/AIOS_AGENTS_REGISTRY.md`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- dispatch: `.aios/inbox/myworld/asc-0090.myworld.json`
- result: `.aios/outbox/myworld/asc-0090.myworld.result.json`
- log: `.aios/logs/asc-0090.myworld.log`
- registry: `~/.aios/agents.json`
- doc_mirror: `docs/AIOS_AGENTS_REGISTRY.md`
- memory_writeback: release wrote MemoryOS draft `mem_7e99392705adcae1`.
