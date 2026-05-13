---
contract_id: ASC-0074
slug: genesis-pre-close-challenge
status: accepted
goal: Make every accepted contract pass through a GenesisOS challenge gate before close — running the prompt-prison critic, assumption mutator, multi-universe fork, modal compare, and analogy match — so closeouts ship only after their prompt-prison risk is examined.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: claude@myworld (operator) per founder "네가 판단" delegation 2026-05-13 KST. Founder declined to micromanage; operator pair authorized for batch decisions on this proposed queue.
origin: integration of ASC-0069..0073 into AIOS contract lifecycle. The Genesis tools are useful only if the loop actually consults them — this contract enforces consultation as a gate.
---

# ASC-0074 Genesis Pre-Close Challenge

## Why Now

ASC-0069..0073 add Genesis tools (critic / mutator / branches /
modalities / analogies). But unless the AIOS contract lifecycle
*forces* the loop to consult them, agents will skip.

This contract adds a `genesis_challenge` step that runs ALL Genesis
tools against a contract just before closeout, attaches the result as
an artifact, and surfaces any high-confidence prison signature as a
soft-block (operator override required to close anyway).

This is the **integration layer** for the Genesis sub-contracts.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_genesis_challenge.py`
- `tests/test_aios_genesis_challenge.py`
- `GenesisOS/genesisos/challenge.py`
- `GenesisOS/tests/test_challenge.py`
- `docs/AIOS_GENESIS_GATE.md`
- `docs/contracts/ASC-0074-genesis-pre-close-challenge.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.challenge.run(contract_id) → ChallengeReport` invoking
  critic + mutator + branches.snapshot + modal compare + analogy match.
- Report shape: `{contract_id, signatures: [...], assumption_seeds: N,
  alive_branches: N, modality_views: [...], top_analogies: [...],
  risk_level: low|medium|high, soft_block: bool, recommendation: str}`.
- Report saved under `.aios/genesis_challenges/<contract_id>.json`.

### myworld.must_produce

- `aios_dispatch.py release` extended: when called with
  `--with-genesis-challenge` (default true once ASC-0074 closes), runs
  challenge first. If `soft_block=true`, refuses release unless
  `--operator-override-genesis-block` is also passed (with reason).
- `scripts/aios_genesis_challenge.py` standalone CLI for ad-hoc runs.
- Test for both gate paths (soft-block respected; override works).

### Hive / Memory / Capability

- No source change.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_challenge.py -v
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_challenge.py
python scripts/aios_genesis_challenge.py --contract-id ASC-0050 --json
# soft block path
python scripts/aios_dispatch.py release --dispatch-id <test_id> 2>&1 | grep -i "challenge\|block\|recommendation"
# override path
python scripts/aios_dispatch.py release --dispatch-id <test_id> --operator-override-genesis-block --reason "tested" 2>&1 | tail -3
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Challenge report generated for any contract.
- Soft-block triggers when `risk_level=high`.
- Operator override with reason works and is logged.
- Without override, high-risk release is refused.

## Stop Conditions

- `challenge_hard_block`: must be soft-block only — operator can always
  override with reason.
- `challenge_modifies_contract`: gate is read-only.
- `challenge_skipped_silently`: every release attempt must show
  challenge ran (or explicit `--without-genesis-challenge`).
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0074-A — codex@GenesisOS implements challenge

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0069, 0070, 0071, 0072, 0073 ALL closed.

### WP-0074-B — codex@myworld wires gate into dispatch release

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0074-A
