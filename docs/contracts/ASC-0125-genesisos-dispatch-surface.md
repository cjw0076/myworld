---
contract_id: ASC-0125
slug: genesisos-dispatch-surface
status: closed
goal: Add GenesisOS to the AIOS dispatch surface so contracts whose scope includes GenesisOS can actually be `aios_dispatch.py create + send --repo GenesisOS`-routed. Closes the prereq gap that has blocked ASC-0069 (Prompt-Prison Critic) from dispatching despite being `accepted` since 2026-05-13.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by claude@myworld (operator) per founder explicit GO "계약 우선순위대로 전달해" 2026-05-14 KST after C→D→B priority decision.
closed: 2026-05-14 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder explicit GO.
origin: verifier discovery 2026-05-14 KST that `scripts/aios_dispatch.py` `REPOS = ("myworld","hivemind","memoryOS","CapabilityOS")` excludes GenesisOS, blocking codex@GenesisOS pickup of ASC-0069 WIP (critic.py / test_critic.py / PROMPT_PRISON.md / cli.py mods already produced by founder, untracked). Memory had flagged this gap (project_aios_recurring_gaps.md) — finally hitting the binding case.
---

# ASC-0125 GenesisOS Dispatch Surface

## Why Now

ASC-0069 (Genesis Prompt-Prison Critic) is `accepted` and has untracked WIP
(`GenesisOS/genesisos/critic.py`, `tests/test_critic.py`,
`docs/PROMPT_PRISON.md`, and `cli.py` mods) produced directly by the founder
on 2026-05-14 KST. The founder then stopped and handed back to the operator
pair. Normal flow: `aios_dispatch.py create + send --repo GenesisOS` so
codex@GenesisOS picks up. Current blocker:

```python
# scripts/aios_dispatch.py:27
REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS")
```

GenesisOS is absent. `--repo GenesisOS` errors out. `.aios/inbox/GenesisOS/`
does not exist. This is a structural gap, not a policy gap — fix the surface.

Per founder reframe 2026-05-14 KST: GenesisOS = `Agent(Philosophy)`, the
creativity / discomfort / world-line engine. If its dispatch surface is
absent, the Philosophy persona literally has no inbox — AIOS can never
invoke it.

DNA references: Invariant 1 (decide before acting — surface change is a
contract, not a silent edit), Invariant 6 (operator override — soft-fail
not hard-fail if surface incomplete), Invariant 8 (classify before
committing — repo enum is a classification).

## Required Reading

- `scripts/aios_dispatch.py` (REPOS tuple, nickname maps, packet writers)
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0069-genesis-prompt-prison-critic.md` (the unblocked target)
- `~/.claude/projects/.../memory/project_aios_recurring_gaps.md`

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_action_policy.py` (if it reads REPOS)
- `tests/test_aios_dispatch.py`
- `.aios/inbox/GenesisOS/.gitkeep`
- `.aios/outbox/GenesisOS/.gitkeep`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/contracts/ASC-0125-genesisos-dispatch-surface.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `GenesisOS/**` (source change is downstream — this contract only opens the door)
- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

1. Extend `REPOS` in `scripts/aios_dispatch.py` to include `"GenesisOS"`.
2. Add nickname map entry: `"GenesisOS": {"genesisos", "genesis os", "genesis_os", "genesis"}`.
3. Verify all `--repo` choices flow through (send/collect/release/hold/retry/escalate/watch).
4. Create `.aios/inbox/GenesisOS/.gitkeep` and `.aios/outbox/GenesisOS/.gitkeep`.
5. Verify `aios_action_policy.py` (if it consumes REPOS) accepts GenesisOS.
6. Update tests covering each new code path: send, collect, status enumeration.
7. Update `docs/AIOS_WORK_DISPATCH.md` to list GenesisOS as a target repo.

### GenesisOS / others: no source change.

## Verification Gate

```bash
python -m py_compile scripts/aios_dispatch.py
python -m unittest tests/test_aios_dispatch.py
# dry-run dispatch
python scripts/aios_dispatch.py create docs/contracts/ASC-0069-genesis-prompt-prison-critic.md --dispatch-id asc-0069 --force
python scripts/aios_dispatch.py send --repo GenesisOS --dispatch-id asc-0069 --agent codex --force
python -c "assert __import__('pathlib').Path('.aios/inbox/GenesisOS/asc-0069.GenesisOS.json').is_file()"
python scripts/aios_dispatch.py status --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- REPOS includes GenesisOS
- GenesisOS repo argument accepted by create/send/status/collect/transition/watch flows
- Test suite green (no regression on existing 4 repos)
- ASC-0069 dispatch packet writes successfully to `.aios/inbox/GenesisOS/`

## Stop Conditions

- `genesisos_source_modified`: this contract is surface-only; GenesisOS code is downstream
- `dispatch_regression`: any of the 4 existing repos breaks
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- `.aios/outbox/myworld/asc-0125-closeout.myworld.result.json`
- `python -m unittest tests/test_aios_dispatch.py` passed 21/21 before
  adding GenesisOS target coverage and 23/23 with ASC-0069 wrapper tests.
- `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 304/304.
- `python scripts/aios_dispatch.py send --repo GenesisOS --dispatch-id asc-0069
  --agent codex` wrote `.aios/inbox/GenesisOS/asc-0069.GenesisOS.json`.

## Work Packets

### WP-0125-A — codex@myworld extends dispatch surface

- target_agent: codex
- target_repo: myworld
- brief: REPOS tuple + nickname map + inbox/outbox dirs + tests + docs.
  Minimum diff. No GenesisOS source change. Verify ASC-0069 packet writes.
