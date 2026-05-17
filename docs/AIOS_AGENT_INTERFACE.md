# AIOS Agent Interface v0.1

This is the minimal protocol any AI agent can read to know how to report useful
observations back to AIOS. It is a definition only: no daemon, sync service, or
library is required by this spec.

## Discovery

1. If `AIOS_ROOT` is set, use it.
2. Otherwise walk up from the current directory looking for `myworld/AGENTS.md`.
3. Otherwise AIOS is offline for this session.

## Observation Path

- Online: `$AIOS_ROOT/.aios/observation_buffer/<agent_id>/`
- Offline: `~/.aios/observation_buffer/<agent_id>/`

Write one JSON file per observation. File names should be timestamped and
unique. Do not write secrets, raw private exports, credentials, or PINs.

## Observation Schema

```yaml
spec_version: "aios.agent_interface.v0.1"
agent_id: "codex_at_myworld"
substrate: "codex_cli | claude_code | gemini | ollama | other"
observed_at: "ISO-8601 timestamp"
context: "repo, task, or contract where this was observed"
event_type: "capability_gap | failure_mode | workflow_pattern | decision | handoff"
summary: "short human-readable observation"
evidence_refs:
  - kind: "contract | dispatch_result | run_artifact | source_file | external_source | operator_turn"
    ref: "stable path, id, or citation"
privacy_class: "public | workspace_internal | private_gated"
recommended_route: "myworld | hivemind | memoryOS | CapabilityOS | GenesisOS | none"
```

## Field Semantics

- `spec_version`: version of this protocol, copied exactly.
- `agent_id`: stable local agent identity if known; otherwise descriptive slug.
- `substrate`: provider or runtime that produced the observation.
- `context`: enough location detail for AIOS to route the observation.
- `event_type`: why this record matters.
- `summary`: concise claim, not raw logs.
- `evidence_refs`: references proving where the claim came from.
- `privacy_class`: strongest privacy level touched by the observation.
- `recommended_route`: AIOS subsystem that should receive follow-up.

## Example

```json
{
  "spec_version": "aios.agent_interface.v0.1",
  "agent_id": "codex_at_myworld",
  "substrate": "codex_cli",
  "observed_at": "2026-05-13T11:12:00+09:00",
  "context": "ASC-0093",
  "event_type": "workflow_pattern",
  "summary": "Verification gates must avoid shell heredocs because dispatch safe_argv rejects them.",
  "evidence_refs": [{"kind": "dispatch_result", "ref": ".aios/inbox/myworld/asc-0093.myworld.json"}],
  "privacy_class": "workspace_internal",
  "recommended_route": "myworld"
}
```

## Known Limitations

- No sync daemon is defined here.
- No provider prompt delivery template is defined here.
- No validator or library guarantee is defined here.
- Retention, compaction, and cross-machine merge policy remain open.
