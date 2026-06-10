---
contract_id: ASC-0210
slug: offline-user-agent-frontier-loop
status: closed
created: 2026-05-20T18:00:00+09:00
accepted: 2026-05-20T18:00:00+09:00
closed: 2026-05-20T18:04:00+09:00
accepted_by: codex_delegated_operator
human_approved: true
goal: Turn the offline user agent idea into a repeatable AIOS primitive for frontier questions, bounded field observations, and draft-first memory routing.
---

# ASC-0210 Offline User Agent Frontier Loop

## Decision

AIOS must not collapse unknowns into confident model prose. When the missing
variable is outside the user's articulated knowledge, the active agent's
context, or model training, AIOS now has a packet primitive for:

1. naming the knowledge boundary;
2. routing possible outside evidence;
3. asking `user@offline` for one bounded observation only when needed;
4. keeping that observation draft-first for MemoryOS review;
5. recording contradictions as follow-up contract candidates.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_OFFLINE_USER_AGENT_PROTOCOL.md`
- `docs/contracts/ASC-0210-offline-user-agent-frontier-loop.md`
- `scripts/aios_offline_user_agent.py`
- `tests/test_aios_offline_user_agent.py`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- provider auth files
- raw private exports
- accepted MemoryOS records
- child repo implementation files

## Implementation

The implementation is:

```bash
python scripts/aios_offline_user_agent.py
```

It supports:

- `validate PATH`
- `new-offline-task ...`

The packet schema is `aios.offline_user_agent_packet.v1`.

Valid packet types:

- `unknown.frontier.question`
- `user.offline_task`
- `field_observation`
- `contradiction`

Default route:

```text
valid packet -> .aios/inbox/memoryOS/ -> draft-first review
```

## Acceptance Evidence

The helper enforces:

- required fields per packet type;
- `review_policy.draft_first: true`;
- `review_policy.auto_accept: false`;
- `field_observation.observed_by: user@offline`;
- `field_observation.private_data_included: false`;
- confidence range checks;
- known owner repo checks for contradictions;
- sensitive/private-term rejection outside explicit boundary fields.

## Verification Gate

Commands:

```bash
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests.test_aios_offline_user_agent -v
python scripts/aios_offline_user_agent.py new-offline-task --task "Open the Uri campus screen and note where your eye stops first." --time-budget "3 minutes" --observe "First hesitation point, confusing label, and one desired tap." --not-share "Do not paste credentials, messages, raw screenshots, or files." --return-format "Three bullets: hesitation / desired action / one fix." --privacy-boundary "Private data and raw screenshots stay offline." --contract-id ASC-0210 --dry-run --json
```

## Next

Wire the Control Center or chat UI to surface `unknown.frontier.question` and
`user.offline_task` packets so the operator sees when AIOS is using the
offline user as a governed sense organ rather than asking ad hoc questions in
chat.
