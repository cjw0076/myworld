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

## Scope-Aware Local Operator Rule

ASC-0060 fixes the ASC-0037 false-positive class: a myworld-only operator
script or docs dispatch with `risk=low`, `privacy=local`, an accepted contract,
and evidence refs is `allow`, not
`human_checkpoint_required:private_remote_data`. Founder-gated paths and any
action that sends private data to a remote surface still escalate. When the
contract declares `repos=["myworld"]` and all allowed files are under
`scripts/`, `tests/`, `docs/`, or `.aios/primitives/`, the policy records the
allow reason as `myworld_local_operator_scope` so later dispatch review can
distinguish this narrow shortcut from a generic low-risk local action.

## Authority-Model Permission Rule (ASC-0178)

Per the ASC-0174 verdict (`proceed_authority_routed_management_plane`) and the
AIOS DNA Authority Model v0.1 amendment:

A contract that expands provider or execution permission is `hold` (not
`allow`) unless it names ALL FOUR of:

1. `record_authority` — who owns the durable artifact the permission produces
2. a named stop condition
3. a named fallback path
4. a result receipt

Raw permission expansion without these four is the ASC-0178 **withdraw class**
(see ASC-0178 reconciliation table). The contract autodrafter must not emit
"Bind ASC-0066 provider backpressure role capsules..." template clones; goal
packets about provider backpressure route to the ASC-0173 consent-emit
delegation pattern instead of generating a new permission contract.

Detection: if ≥ 5 of the last 20 contracts share a permission-expansion
title-stem, that is the prompt-prison chain signature — surface to the operator
for Hive reframe, do not autodraft a 21st.
