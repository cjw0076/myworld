---
contract_id: ASC-0255
slug: end-user-serving-runtime-session-boundary
status: accepted
goal: Add the non-UI runtime/session boundary for end_user_serving so AIOS can represent user-scoped service work before the apps/serving UI is built.
created: 2026-06-13T15:48:00+09:00
accepted: 2026-06-13T15:48:00+09:00
human_approved: true
origin: ASC-0252 readiness says service readiness is partial because `end_user_serving` runtime and user-scoped serving session proof do not exist. ASC-0253 UI remains blocked by Product Design visual target, so this contract closes the non-UI runtime/session prerequisite first.
---

# ASC-0255 End-User Serving Runtime Session Boundary

## Why Now

World readiness is currently false for one correct reason:

```text
end_user_serving_readiness=partial
```

ASC-0253 cannot build UI yet because Product Design requires a confirmed visual
target. But `end_user_serving` itself is not a visual design problem. It is a
runtime/session boundary:

- user-scoped workspace;
- session id and user id on all serving packets;
- approval-before-sensitive-action semantics;
- memory draft-only writes;
- readiness evidence that does not depend on a browser UI.

This contract deliberates; it does not deploy. It produces only local runtime,
test, and documentation artifacts. No deployment code, hosting manifest,
network route, provider account, or user data path is created here.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_round_controller.py`
- `scripts/aios_serving_session.py`
- `scripts/aios_world_readiness.py`
- `tests/test_aios_dispatch.py`
- `tests/test_aios_round_controller.py`
- `tests/test_aios_serving_session.py`
- `tests/test_aios_world_readiness.py`
- `docs/contracts/ASC-0255-end-user-serving-runtime-session-boundary.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

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

## Required Work For Claude

Implement a non-UI serving runtime/session primitive.

Minimum requirements:

1. Add `end_user_serving` to runtime profiles without weakening
   `build_control`.
2. Define conservative semantics:
   - `build_control`: live child execution blocked by default.
   - `live_agent_runtime`: full live AIOS agent runtime.
   - `end_user_serving`: user-delegated runtime; live child execution is not
     generally open unless an explicit serving session/workspace boundary is
     present or an explicit allow flag is set.
3. Add `scripts/aios_serving_session.py` with JSON CLI behavior that can create
   a deterministic `aios.serving_session.v1` record containing:
   - `user_id`;
   - `session_id`;
   - user-scoped workspace path under `.aios/serving/workspaces/<user>/<session>`;
   - approval policy fields;
   - memory policy fields;
   - artifact path;
   - no raw provider logs or credential values.
4. Add focused tests proving:
   - runtime profile accepts `end_user_serving`;
   - default remains `build_control`;
   - malformed/unknown runtime profiles fall back safely;
   - serving session creation writes only under `.aios/serving/**`;
   - path traversal in `user_id` or `session_id` is rejected or sanitized;
   - serving session JSON includes approval and draft-memory policy.
5. Update world readiness markers only if the new evidence is real. It is
   acceptable for `end_user_serving_readiness` to remain partial until the UI
   and browser proof exist.
6. Write a result packet for ASC-0255 with changed files, tests, and remaining
   gaps.
7. Update ledger/worklog closeout.

Do not implement `apps/serving/` in this contract.

## AIOS Role Evidence

### MemoryOS

- context_pack: ASC-0251 product spec, ASC-0252 readiness correction, ASC-0253
  proposed prototype scope.
- retrieval_trace: local repo inspection.
- accepted_memory_ids: pending_or_not_required.
- draft_memory_policy: serving sessions must create memory drafts only.

### CapabilityOS

- route: myworld runtime/session primitive.
- recommended_tools: focused unit tests, py_compile, world-readiness JSON,
  dispatch watcher result packet.
- fallback_plan: if Claude provider fails, Codex verifies the degraded result
  and opens a narrower follow-up.
- authority: execute_with_receipt inside allowed files.

### GenesisOS

- branch_set: "UI first" versus "runtime/session boundary first".
- assumption_mutations: UI remains gated by Product Design visual target; runtime
  can progress independently.
- semantic_alignment_notes: real service users require a scoped runtime before
  a polished screen is trustworthy.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude edits bounded myworld runtime/session files.
- provider_route: `claude@myworld` via `scripts/aios_child_watcher.sh`.
- verification_receipt: unit tests, py_compile, readiness JSON, diff check.
- degraded_or_fallback_receipt: required on provider timeout/access denial.

## Verification Gate

```bash
python3 -m unittest tests.test_aios_dispatch tests.test_aios_round_controller tests.test_aios_serving_session tests.test_aios_world_readiness -v
python3 -m py_compile scripts/aios_dispatch.py scripts/aios_round_controller.py scripts/aios_serving_session.py scripts/aios_world_readiness.py
python3 scripts/aios_world_readiness.py --json
git diff --check
```

## Work Packets

### WP-0255-A — Claude serving runtime/session primitive

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Implement the non-UI `end_user_serving` runtime/session boundary
  only. Do not build `apps/serving/`. Keep all serving workspace artifacts under
  `.aios/serving/**` and keep credentials/raw provider logs out of receipts.
- result: pending

## Stop Conditions

- `apps_serving_implemented_before_visual_target`
- `runtime_profile_weakens_build_control`
- `serving_workspace_path_traversal`
- `serving_session_without_user_id`
- `memory_auto_accepts_under_end_user_serving`
- `credential_value_in_prompt_or_doc`
- `raw_provider_history_leak`
