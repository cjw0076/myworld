---
contract_id: ASC-0245
slug: kernel-authority-correctness
status: closed
goal: Close the first AIOS product-kernel authority holes before service packaging by hardening filesystem scope enforcement and checkpoint continuation.
created: 2026-06-13T14:22:00+09:00
accepted: 2026-06-13T14:22:00+09:00
human_approved: true
closed: 2026-06-13T14:40:00+09:00
origin: external architecture review in `1.md` identified PR-1 kernel authority correctness as the shortest next productization slice.
---

# ASC-0245 Kernel Authority Correctness

## Why Now

`1.md` argues that AIOS is pointed at the right north star but still needs the
kernel pieces to become one safe, product-grade local device head. The shortest
next development slice is not another architecture document. It is authority
correctness in the current ContractObject / runner / head path.

This contract delegates implementation to Claude. Codex must not patch the
implementation in this slice.

## Scope

repos:

- `myworld`

allowed_files:

- `scripts/aios_contract_object.py`
- `scripts/aios_contract_runner.py`
- `scripts/aios_head.py`
- `tests/test_aios_contract_object.py`
- `tests/test_aios_contract_runner.py`
- `tests/test_aios_head.py`
- `docs/contracts/ASC-0245-kernel-authority-correctness.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- provider auth files
- sensitive vault contents
- raw provider logs
- private history stores
- child repo implementation files
- `uri/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`

## Substrate / Surface / Knowledge Gate

- schema_version: `aios.boundary_classifier.v1`
- layer: `runtime_kernel_authority`
- owner_repo: `myworld`
- substrate_level: `runtime`
- surface_type: `contract`
- knowledge_scope: `local_only`
- authority: `execute_with_receipt`
- required_receipts:
  - `authority_regression_tests`
  - `filesystem_scope_receipt`
  - `checkpoint_continuation_receipt`
  - `focused_test_report`

## Required Work For Claude

Implement the first product-kernel authority slice:

1. Add `fs.list` authorization to the same scope model that protects
   filesystem reads/writes. A planner must not be able to list arbitrary
   outside paths just because `fs.list` is an allowed tool name.
2. Add canonical path enforcement for filesystem scope checks. Use resolved
   paths and deny symlink/path traversal escape from allowed roots.
3. Add a `user.checkpoint` approved-continuation handler or equivalent receipt
   path. If a checkpoint step has already been approved, resume must not fail
   as an unknown syscall.
4. Add focused regression tests:
   - outside-scope `fs.list` is rejected;
   - symlink escape is rejected;
   - approved `user.checkpoint` records a successful receipt and continues;
   - the personal-files specimen reaches the next mutation/checkpoint gate
     without unknown-syscall failure.

## Plain-Language Framing

AIOS is supposed to act only inside the user-granted boundary. If the head can
list or traverse outside that boundary, it is not a governed device head. If
the user approves a checkpoint and resume then crashes as an unknown action,
the loop is not service-ready.

## Assumptions

- Assumption 1: `fs.list` is a filesystem read-like action and must be scoped.
- Assumption 2: path strings are not enough; resolved canonical paths must be
  used to prevent symlink/path traversal escape.
- Assumption 3: `user.checkpoint` is not a substrate action; after approval it
  should create a receipt and let the runner continue.

Negated checks:

- A path outside allowed roots remains forbidden even if a symlink under an
  allowed root points to it.
- A denied path wins over an allowed root.
- Unknown filesystem actions remain fail-closed.

## Counter-Branch

An alternative is to jump directly to turn-loop integration. Reject that for
this slice. A turn-loop that can escape filesystem scope or fail after approval
would only make the unsafe path faster. Kernel authority correctness comes
first.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_contract_object tests.test_aios_contract_runner tests.test_aios_head -v
python3 -m py_compile scripts/aios_contract_object.py scripts/aios_contract_runner.py scripts/aios_head.py
git diff --check
```

Pass criteria:

- All new and existing focused tests pass.
- The implementation does not broaden allowed paths.
- No child repo files or sensitive local material are touched.
- Result packet names the exact before/after authority behavior.

## AIOS Role Evidence

### MemoryOS

- source_context: `1.md` external architecture review, summarized here rather
  than copied into dispatch.
- draft_policy: no accepted memory mutation in this slice.

### CapabilityOS

- route: local MyWorld runtime/kernel files only.
- authority: no tool binding or provider route changes.

### GenesisOS

- challenge: do not build a faster turn-loop on top of an unsafe scope gate.
- authority: advisory only.

### Hive Mind

- execution_plan: Claude implements in MyWorld; focused tests and result packet
  prove the slice.

## Work Packets

### WP-0245-A — Claude kernel authority correctness

- target_repo: `myworld`
- target_agent: `claude`
- status: issued
- instruction: Implement the Required Work For Claude section. Keep the slice
  tight. Do not implement planner receipts, unified provider adapters, or
  turn-loop defaulting in this contract. Return a result packet with changed
  files, tests run, before/after behavior, and remaining kernel gaps.
- result: pending

## Stop Conditions

- `scope_violation`
- `privacy_violation`
- `filesystem_scope_broadened`
- `symlink_escape_still_possible`
- `checkpoint_resume_unknown_syscall`
- `verification_gate_failed`
- `child_repo_source_edit`
