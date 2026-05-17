# AIOS Hooks — Deterministic Enforcement

`scripts/aios_hooks.py` (`aios hooks`). Contract: ASC-0184.

AIOS's DNA invariants and per-contract scope were honored by convention. A
hook is deterministic code that inspects a proposed action and returns a
verdict; a `block` is final regardless of model intent. This is the mechanism
that turns the invariants from documented into enforced (the ASC-0122 gap).

## The action shape

A hook evaluates an *action* dict:

```json
{
  "kind": "write | overwrite | delete | dispatch_apply",
  "paths": ["docs/x.md", "scripts/y.py"],
  "contract_id": "ASC-NNNN",
  "operator_override": {"decision": "allow", "reason": "..."}
}
```

## Verdicts

- `allow` — no hook objected.
- `block` — at least one hook blocked; the action must not happen.
- `escalate` — a hook could not decide safely; surface to the operator.
- `allow_overridden` — a hook blocked, but an explicit `operator_override`
  converted it (Invariant 6). The override is logged.

Precedence: block > escalate > allow.

## Built-in hooks

| Hook | Invariant | Fail mode | Blocks |
|---|---|---|---|
| privacy-boundary | 7 | **fail-closed** (error → block) | a path with a gated segment (`dain`, `minyoung`, `_from_desktop`) or substring (`.env`, `secret`, `credentials`, `auth.json`, `raw_export`) |
| contract-scope | — | fail-open → escalate | a path outside the contract's `allowed_files` or matching `forbidden_files` |
| append-only-audit | 3 | fail-open → escalate | a `delete`/`overwrite` of a ledger file or a closed contract |

Privacy is the one hook that fails *closed*: if it errors, the action is
blocked. The others fail *open to escalate* — a hook bug must not silently
wave an action through, nor halt the autopoietic loop on a non-privacy
matter.

## Usage

```bash
aios hooks list
aios hooks check --kind write --path scripts/x.py --contract ASC-0184
aios hooks check --kind overwrite --path docs/AIOS_AGENT_LEDGER.md   # → block
aios hooks check --kind write --path dain/x.md --override "founder ok" # → allow_overridden
```

`check` exits non-zero on `block` so a caller can gate on it. Every decision
is appended to `.aios/hooks/log.jsonl` (audit trail).

## Integration status

The engine is built, tested (`tests/test_aios_hooks.py`, 9 tests), and
callable. Wiring it into `aios_dispatch.py` so dispatch consults it before
applying a packet — the contract's remaining named-exit item — is a
deliberate follow-on done while the live round controller can be watched.

## Extending

`BUILTIN_HOOKS` is a list of `(name, fail_closed, fn)`. A hook is
`fn(root, action) -> {"verdict": ..., "reason": ...}`. Add narrow,
deterministic checks; keep model-judgment out of the enforcement layer.
