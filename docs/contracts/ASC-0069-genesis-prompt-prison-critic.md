---
contract_id: ASC-0069
slug: genesis-prompt-prison-critic
status: proposed
goal: Add a GenesisOS critic that detects when an agent (claude/codex/local LLM) is stuck in a single line of reasoning produced by prompt structure, language pattern, or training distribution — and surfaces escape vectors.
created: 2026-05-13 KST
proposed_by: claude@myworld (operator) per founder GO of GenesisOS sub-contract sequence.
acceptance_authority: pending founder GO ("GO ASC-0069" or batch).
origin: founder directive 2026-05-13 KST "프롬프트, 언어, 구사 능력에 의해 Agent의 능력이 너무 제한되는 느낌을 받았어. GenesisOS는 이걸 해소" — first sub-contract addressing the prompt-prison constraint directly.
---

# ASC-0069 Genesis Prompt-Prison Critic

## Why Now

Founder observed: agents (claude/codex/LLMs) are constrained by prompt
structure (linear single-thread), language pattern (English/Korean
encoding bias), and training-distribution defaults. They tend to
converge on the most-common path — *the prompt becomes a prison*.

GenesisOS exists to break this. The first sub-piece is a **detector**:
something that notices when the current reasoning has the signatures of
prompt-prison and surfaces concrete escape vectors before the agent
commits to the convergent answer.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/critic.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_critic.py`
- `GenesisOS/docs/PROMPT_PRISON.md`
- `scripts/aios_genesis_critic_dispatch.py`
- `tests/test_aios_genesis_critic_dispatch.py`
- `docs/contracts/ASC-0069-genesis-prompt-prison-critic.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.critic` module exposing `Critic.detect(text|chain)` →
  returns `{prison_signatures: [...], escape_vectors: [...], confidence: float}`.
- Detection signatures (V1, deterministic + auditable):
  - **mono-language**: response is single language only (no formal
    notation, no diagram, no code) → suggest formal/visual escape
  - **single-frame**: same metaphor / domain / scale used throughout
    → suggest cross-domain analogy
  - **convergent-default**: response matches the most common AIOS
    pattern for similar inputs (looked up from MemoryOS accepted
    memories) → suggest counter-default branch
  - **assumption-silent**: zero explicit assumptions named → suggest
    enumerate-then-negate pass
  - **terminology-trapped**: uses ≥3 jargon terms without unfolding →
    suggest plain-language re-statement
  - **time-frozen**: no consideration of "in 1h vs 1y" alternatives →
    suggest temporal escape
- `genesisos cli critic --text <file>` and `--chain <file>` for both
  text and reasoning-chain inputs. JSON output.
- `GenesisOS/docs/PROMPT_PRISON.md` documents each signature with one
  example of the prison and one example of the escape.

### myworld.must_produce

- `scripts/aios_genesis_critic_dispatch.py` — small wrapper that runs
  the critic against current open-contract drafts and surfaces results
  as a finding in `aios_monitor.py assess`. Recommendation only —
  never modifies the contract.
- Tests for the wrapper.

### Hive / Memory / Capability

- No source change. Critic output may later be consumed but not in V1.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_critic.py -v
python -m genesisos.cli critic --text README.md --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_critic_dispatch.py
python scripts/aios_genesis_critic_dispatch.py --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Critic detects at least 2 of 6 signatures on a deliberately
  prompt-prisoned test fixture.
- Detects 0 signatures on a deliberately diverse test fixture.
- Recommendation-only — no contract or memory mutation.

## Stop Conditions

- `critic_modifies_contract`: critic must never edit a contract.
- `critic_blocks_dispatch`: critic is advisory; may not gate dispatch.
- `critic_uses_remote_llm_v1`: V1 stays deterministic + local for
  audit. Remote LLM critic is a future contract.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0069-A — codex@GenesisOS implements critic + cli

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 (GenesisOS bootstrap closed)
- brief: implement the 6 detection signatures, cli wrapper, tests, doc.

### WP-0069-B — codex@myworld dispatch wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0069-A
- brief: wire the critic into monitor assessment as advisory finding.
