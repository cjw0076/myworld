# AIOS Citizenship

ASC-0107 defines who may claim authority inside AIOS. This is not identity
proof yet; it is a V1 authority layer over the ASC-0090 agent registry.

## Classes

| Class | Meaning | Examples |
| --- | --- | --- |
| `operator` | Full delegated AIOS control-plane authority | `codex@myworld`, `claude@myworld` |
| `child_agent` | Repo-local implementation authority | `codex@hivemind`, `codex@memoryOS` |
| `reviewer` | Review and memory acceptance authority | `claude@myworld`, `codex@memoryOS` |
| `critic` | Advisory challenge authority | `codex@GenesisOS` |
| `researcher` | Evidence collection and capability discovery | `codex@CapabilityOS` |
| `outsider` | Observation and proposal only | peer or unregistered agent |

## Decision Matrix

| Action | Required citizenship | V1 behavior |
| --- | --- | --- |
| `release_dispatch` | `operator` | Soft-fail: audit denial, continue |
| `flip_status_to_accepted` | `operator` | Deny in authority result |
| `flip_status_to_held` | `operator` | Deny in authority result |
| `flip_status_to_stopped` | `operator` | Deny in authority result |
| `commit_to_child_repo` | `operator` or `child_agent` | Deny in authority result |
| `accept_memory_draft` | `operator` or `reviewer` | Deny in authority result |
| `propose_contract` | any citizenship class | Allow |
| `bind_capability` | none | Hard forbidden |

## Override

`aios_dispatch.py release` records an authority check before release. V1 does
not block an existing operator loop because that would risk deadlocking legacy
work, but it appends both dispatch-state and authority audit evidence.

```bash
python scripts/aios_dispatch.py release --dispatch-id asc-0000 --reason verified --agent codex@myworld
python scripts/aios_dispatch.py release --dispatch-id asc-0000 --reason founder_override --agent outsider_peer --override-authority
```

Audit log:

- `.aios/state/authority.jsonl`
- `.aios/state/dispatches.jsonl` event `authority_check`

## Registry Dependency

The authority layer reads ASC-0090 registry data from `~/.aios/agents.json` or
`$AIOS_AGENT_HOME/agents.json`. If the registry is unreadable, V1 allows with a
warning. If the registry is readable but an agent is unknown, that agent is
treated as `outsider`.
