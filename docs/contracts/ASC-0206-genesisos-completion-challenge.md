---
contract_id: ASC-0206
slug: genesisos-completion-challenge
status: closed
created: 2026-05-20T16:31:00+09:00
accepted: 2026-05-20T16:31:00+09:00
closed: 2026-05-20T16:33:00+09:00
accepted_by: codex_delegated_operator
origin: ASC-0205 CC1 requires GenesisOS dispatch evidence; current evidence has two passed GenesisOS result packets and one held packet.
goal: Ask GenesisOS to challenge ASC-0205's completion frame before CC1 is counted closed, producing a third passed GenesisOS result packet and anti-convergence evidence.
---

# ASC-0206 GenesisOS Completion Challenge

## Why Now

ASC-0205 defines AIOS completion with six measurable criteria. That is useful,
but it can become a checklist trap. GenesisOS already removed the obvious
prompt-prison signatures from ASC-0205, but CC1 should not be closed by
counting a held GenesisOS result as healthy activation evidence.

This contract asks GenesisOS to challenge the completion frame itself: what
would AIOS still fail at after the criteria look green?

## Scope

repos:

- `GenesisOS`
- `myworld`

allowed_files:

- `docs/contracts/ASC-0206-genesisos-completion-challenge.md`
- `docs/contracts/ASC-0205-aios-completion-north-star.md`
- `docs/AGENT_WORKLOG.md`
- `.aios/inbox/GenesisOS/asc-0206.GenesisOS.json`
- `.aios/outbox/GenesisOS/asc-0206.GenesisOS.result.json`

forbidden_files:

- `.env`
- raw exports
- provider auth files
- GenesisOS implementation files
- child repo implementation files

## Requirements

must_produce:

- A GenesisOS result packet with `status=passed`.
- Critic, mutation, analogy, divergence, and critique evidence over
  `ASC-0205`.
- At least one named residual failure mode that could remain after all six
  ASC-0205 criteria appear green.

must_not:

- Execute implementation work.
- Accept memory.
- Claim ASC-0205 is complete.
- Rewrite ASC-0205 criteria without a later MyWorld/operator decision.

## Verification Gate

```bash
cd GenesisOS
python -m genesisos.cli critic --text ../docs/contracts/ASC-0205-aios-completion-north-star.md --json --generated
python -m genesisos.cli mutate --record ../docs/contracts/ASC-0205-aios-completion-north-star.md --no-write --json
python -m genesisos.cli analogy match --text ../docs/contracts/ASC-0205-aios-completion-north-star.md --top 3 --generated --json
python -m genesisos.cli diverge --goal "What would AIOS still fail at after ASC-0205 looks green?" --json
python -m genesisos.cli critique --goal "Challenge ASC-0205 completion north star" --idea "Close CC1 only if GenesisOS has three passed result packets and the completion criteria still expose discomfort after green checks" --json
```

## Stop Conditions

- `genesisos_result_not_passed`
- `challenge_claims_completion`
- `challenge_executes_implementation`
- `residual_failure_mode_missing`

## Receipts

- dispatch result: `.aios/outbox/GenesisOS/asc-0206.GenesisOS.result.json`
- dispatch status: `asc-0206` sent to `GenesisOS`, watcher passed, collected
  2026-05-20T16:32:14+09:00.
- GenesisOS residual failure mode: AIOS may still fail by treating green
  criteria as completion; GenesisOS divergence recommends refusing premature
  completion and changing the question when necessary.
- local helper evidence: critic and analogy slots generated advisory payloads
  through local `ollama` model `qwen3:8b`, with
  `local_generation_only_no_source_mutation`.
