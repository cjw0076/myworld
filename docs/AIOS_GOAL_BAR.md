# AIOS Goal Bar

ASC-0096 adds a deterministic natural-language Goal Bar to the local control
app. It is an end-user input layer for common AIOS questions and route
requests, not an external-LLM classifier.

## Flow

```text
user text
  -> scripts/aios_goal_bar.py classify
  -> show intent + command in apps/control
  -> operator presses Run
  -> scripts/aios_goal_bar.py --execute
  -> inline result
```

The first submit only classifies. Execution requires a second confirmed
request, so the UI does not silently run a command.

## Intents

| Intent | Example | Route |
| --- | --- | --- |
| `hive_agents_status` | `어떤 Agent가 있지?` | `hive agents status` |
| `dispatch_status` | `어떤 contract가 열려있나` | `aios_dispatch.py status` |
| `primitive_monitor_list` | `list monitor primitives` | `aios_primitives monitor list` |
| `memory_drafts_list` | `기억 draft 보여줘` | `memoryos drafts list` |
| `capability_recommend` | `도구 추천해줘` | `capabilityos recommend` |
| `aios_invoke_plan` | `AIOS로 실행 route 만들어` | `aios_invoke.py --plan-only` |
| `hive_ask` | anything else | `hive ask --fast` |

## Guardrails

- deterministic keyword/pattern classification only
- no shell execution; subprocess uses argv lists
- rejects destructive patterns such as `rm -rf`, `dd if=`, `mkfs`, `sudo`,
  `shutdown`, and raw block-device writes
- execution requires UI confirmation
- child repos are read only from this contract

## Commands

```bash
python scripts/aios_goal_bar.py "어떤 Agent가 있지?" --json
python scripts/aios_goal_bar.py "어떤 Agent가 있지?" --execute --json
python scripts/aios_local_app.py up --port 9885 --ws-port 9886 --json
python scripts/aios_local_app.py status --assert-live --json
```
