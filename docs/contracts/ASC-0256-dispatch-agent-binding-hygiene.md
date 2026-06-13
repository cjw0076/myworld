---
contract_id: ASC-0256
slug: dispatch-agent-binding-hygiene
status: closed
goal: Prevent AIOS dispatch packets from executing under a stale/default agent when the operator later assigns a different provider.
created: 2026-06-13T16:05:00+09:00
accepted: 2026-06-13T16:05:00+09:00
closed: 2026-06-13T16:12:00+09:00
human_approved: true
origin: ASC-0255 was intended for `claude@myworld`, but the pending packet executed as `codex@myworld` because the dispatch id already had a default-agent packet.
---

# ASC-0256 Dispatch Agent Binding Hygiene

## Why Now

AIOS is becoming a serving system, not a single local chat. In a real service,
the operator's provider assignment must be a binding control-plane fact:

| State | Existing packet agent | Requested agent | Required behavior |
| --- | --- | --- | --- |
| no packet | none | any | write packet normally |
| pending packet | same | same | keep existing overwrite semantics |
| pending packet | different | different | refuse; packet agent is immutable |
| result exists | any | different | refuse; do not rewrite executed evidence |

This contract fixes the packet-level hygiene only. It does not build
`apps/serving/`, change provider credentials, or execute live child work.

## Assumptions

- A pending inbox packet may already be visible to a watcher, so its `agent`
  cannot be safely rewritten to another provider.
- An outbox result or collected event means execution evidence exists and the
  packet must not be rewritten to imply another provider did the work.
- A mismatch must be auditable, not just a generic "packet already exists"
  error.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0256-dispatch-agent-binding-hygiene.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- private vault contents
- raw provider logs
- private history stores
- `apps/control/**`
- `apps/serving/**`
- child repo implementation files
- `uri/**`
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Required Work

1. Teach `send` to inspect an existing inbox packet before overwrite.
2. If the existing packet's `agent` differs from the requested `--agent`, fail
   without `--force` and record an `agent_binding_mismatch` event.
3. If `--force` is present and the requested agent still differs, refuse the
   rewrite and record an `agent_reassign_blocked` event.
4. If result evidence exists, include that evidence in the blocked event and
   error text.
5. Add focused tests for mismatch refusal, forced pending reassignment, and
   result-protected refusal.

## AIOS Role Evidence

### MemoryOS

- context_pack: ASC-0255 route-mismatch closeout and provider reroute history.
- retrieval_trace: `rtrace_c3bca53907ac5dfe`.
- accepted_memory_ids: pending_or_not_required.
- draft_memory_policy: no memory acceptance in this contract.

### CapabilityOS

- route: `cap_myworld_operator_control_plane`,
  `cap_aios_child_watcher`.
- recommended_tools: focused dispatch unit tests, py_compile, diff check.
- fallback_plan: if provider-specific dispatch remains ambiguous, hold future
  Claude work until packet assignment is explicit in the inbox artifact.
- authority: execute_with_receipt inside allowed files.

### GenesisOS

- branch_set: "rewrite freely" versus "evidence-protected reassignment".
- assumption_mutations: forced rewrite is only safe before result evidence.
- semantic_alignment_notes: serving users need provider accountability, not
  generic worker pickup.
- authority: advisory only.

### Hive Mind

- execution_plan: Codex implements the control-plane primitive and verifies it.
- provider_route: `codex@myworld` for dispatch CLI correctness.
- verification_receipt: unit tests, py_compile, diff check.
- degraded_or_fallback_receipt: required if tests cannot run.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_dispatch -v
python3 -m py_compile scripts/aios_dispatch.py
git diff --check
```

## Stop Conditions

- `executed_evidence_rewritten`
- `provider_auth_touched`
- `apps_serving_modified`
- `child_repo_modified`

next: after this contract closes, future Claude-owned serving work can be
dispatched only after confirming packet `agent` matches the intended provider.

## Result Packet

schema_version: `aios.result_packet.v1`
contract_id: `ASC-0256`
dispatch_id: `asc-0256`
repo: `myworld`
agent: `codex@myworld`
status: `passed`

changed:

- `scripts/aios_dispatch.py`
- `tests/test_aios_dispatch.py`
- `docs/contracts/ASC-0256-dispatch-agent-binding-hygiene.md`
- `docs/AGENT_WORKLOG.md`
- `docs/AIOS_AGENT_LEDGER.md`

evidence:

- `python3 -m unittest tests.test_aios_dispatch -v` passed 52 tests.
- `python3 -m py_compile scripts/aios_dispatch.py` passed.
- `git diff --check` passed.
- AIOS route recommended `cap_myworld_operator_control_plane` and
  `cap_aios_child_watcher`.
- GenesisOS critique forced explicit assumptions and machine-checkable rules.
- Explorer review recommended immutable existing packet assignment.

decision:

- Existing inbox packet `agent` is immutable across provider names.
- `send --force` may still overwrite same-agent packets, but it cannot convert
  a packet from `codex` to `claude`, `gemini`, or any other provider.
- If outbox/collected result evidence exists, that evidence is reported in the
  blocked event.

remaining_gaps:

- There is still no dedicated `archive/cancel/reissue` command for replacing a
  stale wrong-agent dispatch id. Future work should add that as an explicit
  operator action instead of overloading `send --force`.
