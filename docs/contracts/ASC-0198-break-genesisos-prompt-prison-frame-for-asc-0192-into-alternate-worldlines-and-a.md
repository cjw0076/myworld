---
contract_id: ASC-0198
status: withdrawn
authority: speculative_only
goal: Break GenesisOS prompt-prison frame for ASC-0192 into alternate worldlines and a verifiable AIOS work contract.
source_contract: ASC-0192
withdrawn: 2026-05-18 KST
withdrawn_reason: moot — source_contract ASC-0192 closed successfully via two-tier routing (ASC-0193/0203/0204); the break-frame seed was never developed into an operator contract (claude@myworld triage 2026-05-18)
---

# ASC-0198 Genesis Break-Frame Seed

This file is not execution authority; it is a reviewable bridge from GenesisOS
discomfort to an operator-approved AIOS smart contract.

## Proposed Goal

Break GenesisOS prompt-prison frame for ASC-0192 into alternate worldlines and a verifiable AIOS work contract.

## Source Friction

- source_contract: `ASC-0192`
- source_path: `docs/contracts/ASC-0192-aios-interface-two-tier-routing.md`
- source_seed: `.aios/chat/friction-radar-050a641cdef50c41/friction_contract_seed.md`
- reason: GenesisOS critic found advisory prompt-prison signatures in open contracts.

## Escape Vectors

- restate as table, diagram, pseudocode, or machine-checkable schema
- force one analogy from a distant domain before deciding
- enumerate assumptions, then negate the top three
- rewrite in plain language before using the jargon again

## Prompt-Prison Signatures

- `mono-language`: long prose without code, schema, table, diagram, or formal notation
- `single-frame`: no cross-domain frame markers found
- `assumption-silent`: no explicit assumptions named
- `terminology-trapped`: jargon terms without unfolding: agent, aios, capabilityos, contract, genesisos, memoryos

## Alternate Worldlines

1. Schema worldline: restate the target work as machine-checkable inputs,
   outputs, stop conditions, and verification gates before implementation.
2. Inversion worldline: negate the top three hidden assumptions and produce a
   counter-plan that intentionally avoids the default wording.
3. Distant-domain worldline: map the contract to a non-software operating
   system analogy, then import one concrete mechanism back into AIOS.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `docs/contracts/ASC-0192-aios-interface-two-tier-routing.md`
- `docs/contracts/ASC-0198-break-genesisos-prompt-prison-frame-for-asc-0192-into-alternate-worldlines-and-a.md`
- `.aios/promotions/**`

forbidden_files:

- `.env`
- raw exports
- private runtime auth files
- child repo implementation files

## Verification Gate

```bash
python -m py_compile scripts/aios_control_snapshot.py
python -m unittest tests.test_aios_control_snapshot -v
```

## Stop Conditions

- The seed is treated as accepted execution authority.
- GenesisOS critique loses the cited source contract or escape vectors.
- The generated contract cannot be reviewed independently of this chat turn.

## Promotion Receipt

- promotion_receipt: `.aios/promotions/friction-bbc06575a205-20260518T020758/promotion.json`
- source_seed: `.aios/chat/friction-radar-050a641cdef50c41/friction_contract_seed.md`
