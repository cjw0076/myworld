---
contract_id: ASC-0246
slug: kernel-authority-correctness-fix-forward
status: closed
goal: Finish ASC-0245 after failed verification by fixing test imports and completing the missing authority regression coverage without broadening scope.
created: 2026-06-13T14:26:00+09:00
accepted: 2026-06-13T14:26:00+09:00
human_approved: true
closed: 2026-06-13T14:40:00+09:00
origin: ASC-0245 produced partial implementation but failed its verification gate.
---

# ASC-0246 Kernel Authority Correctness Fix-Forward

## Why Now

ASC-0245 was delegated to Claude and produced partial changes in the intended
kernel authority files, but the verification gate failed:

```text
python3 -m unittest tests.test_aios_contract_object tests.test_aios_contract_runner tests.test_aios_head -v
-> 34 tests run, 3 errors
```

The failing tests import `aios_contract_object` directly instead of following
the existing test module import pattern, causing:

```text
ModuleNotFoundError: No module named 'aios_contract_object'
```

This contract is a tight fix-forward. It allows Claude to continue from the
current partial dirty state and finish the missing ASC-0245 acceptance criteria.
Codex must not patch the implementation.

## Scope

repos:

- `myworld`

allowed_existing_dirty:

- `scripts/aios_contract_object.py`
- `scripts/aios_contract_runner.py`
- `tests/test_aios_contract_object.py`

allowed_files:

- `scripts/aios_contract_object.py`
- `scripts/aios_contract_runner.py`
- `scripts/aios_head.py`
- `tests/test_aios_contract_object.py`
- `tests/test_aios_contract_runner.py`
- `tests/test_aios_head.py`
- `docs/contracts/ASC-0246-kernel-authority-correctness-fix-forward.md`
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
- `CapabilityOS/**`
- `artifacts/**`
- `gemini/**`
- `gemini-cli/**`
- `1.md`
- `scripts/aios_frontier_question.py`

## Required Work For Claude

1. Fix the new `tests/test_aios_contract_object.py` imports to match the
   existing test module pattern.
2. Complete the missing ASC-0245 coverage:
   - symlink escape is rejected;
   - approved `user.checkpoint` records a successful receipt and continues;
   - the personal-files specimen reaches the next mutation/checkpoint gate
     without unknown-syscall failure.
3. Reassess the partial canonical path implementation. It must preserve deny
   precedence and must not broaden allowed roots.
4. Write or update the ASC-0246 closeout ledger entry only after tests pass.

## Verification Gate

Claude must run:

```bash
python3 -m unittest tests.test_aios_contract_object tests.test_aios_contract_runner tests.test_aios_head -v
python3 -m py_compile scripts/aios_contract_object.py scripts/aios_contract_runner.py scripts/aios_head.py
git diff --check
```

Pass criteria:

- Focused tests pass.
- `fs.list` is read-scope gated.
- symlink/path traversal escape is blocked.
- approved checkpoint continuation is a successful receipt, not an unknown
  syscall.
- No unrelated dirty paths are modified.

## Stop Conditions

- `test_gate_failed`
- `scope_violation`
- `privacy_violation`
- `filesystem_scope_broadened`
- `symlink_escape_still_possible`
- `checkpoint_resume_unknown_syscall`
