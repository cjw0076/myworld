# AIOS Action Policy

AIOS actions are evaluated before execution. The policy engine does not execute
work; it classifies proposed actions so the control plane can proceed, hold,
deny, or escalate.

## Decisions

```text
allow
  The action is local, low-risk, contracted, evidenced, and reversible enough.

hold
  The action may be valid, but required contract, evidence, owner, or budget
  information is missing.

deny
  The action is forbidden by AIOS invariants: illegal access, coercion,
  deception, secret exfiltration, raw private export exposure, or child-repo
  scope bypass.

escalate
  The action may be legitimate, but it requires human approval because it has
  legal, safety, paid, credentialed, irreversible, public, or real-world
  authority impact.
```

## Required Fields

A proposed action should declare:

- `action_type`
- `target_repo`
- `authority`
- `risk`
- `privacy`
- `cost`
- `has_contract`
- `evidence_refs`
- `human_approved`
- `irreversible`
- `external_effect`
- `uses_credentials`
- `public_communication`
- `legal_or_safety_impact`

## Default Rules

- Deny forbidden actions even if a contract exists.
- Escalate high-authority or high-impact actions unless `human_approved=true`.
- Hold ambiguous actions with missing contract, owner, evidence, or budget
  details.
- Allow only low-risk local actions with an accepted/closed contract and at
  least one evidence reference.
- Preserve child repo ownership: `myworld` does not directly edit child repo
  source unless a smart contract explicitly grants scope.
