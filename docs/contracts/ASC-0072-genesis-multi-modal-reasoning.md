---
contract_id: ASC-0072
slug: genesis-multi-modal-reasoning
status: proposed
goal: Give GenesisOS a non-language reasoning surface — diagram, code, formal logic, math, constraint graph — so agents can think in modalities outside their training-language defaults and escape the linguistic prison.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: pending founder GO.
origin: founder directive on prompt-prison — "프롬프트, 언어, 구사 능력에 의해 Agent의 능력이 제한". Multi-modal reasoning is the most direct escape from language-only thinking.
---

# ASC-0072 Genesis Multi-Modal Reasoning

## Why Now

Agents are trained on tokens — language. They tend to think in
sentences. Many problems are easier in other modalities:

- **Diagram** (mermaid, plantuml): structural relationships, flows
- **Code** (lambda, types, prolog, z3): formal constraints
- **Math** (LaTeX, equations): quantitative relationships
- **Graph** (DAG, CRDT): dependency / time / state
- **Table** (csv, decision matrix): comparison spaces

GenesisOS provides a CLI that *forces* an agent to express the same
problem in N modalities. The translation often surfaces what language
hid.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/modalities.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_modalities.py`
- `GenesisOS/docs/MULTI_MODAL.md`
- `scripts/aios_genesis_modal.py`
- `tests/test_aios_genesis_modal.py`
- `docs/contracts/ASC-0072-genesis-multi-modal-reasoning.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.modalities` module with adapters per modality:
  - `to_mermaid(text) → str` — extract entities + relations, emit mermaid
  - `to_plantuml(text) → str`
  - `to_lambda_calculus(text) → str` — extract first-order constraints
  - `to_decision_matrix(text) → csv str` — alternatives × criteria
  - `to_dag(text) → dot str` — dependencies / sequencing
  - `to_constraint_graph(text) → z3-script str`
- `genesisos cli modal translate --text <file> --to <modality> --json`
- `genesisos cli modal compare --text <file> --modalities all --json`
  → returns dict of modality → translation, lets operator scan
- V1 adapters are deterministic / heuristic (rule-based extraction).
  V2 may use local LLM (out of scope).
- `MULTI_MODAL.md` documents each modality with one example.

### myworld.must_produce

- `scripts/aios_genesis_modal.py` — wrapper that takes a contract or
  draft and surfaces the multi-modal view as a comparison artifact
  under `.aios/genesis_modal_views/<id>.json`. Recommendation only.
- Test.

### Hive / Memory / Capability

- No source change.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_modalities.py -v
python -m genesisos.cli modal compare --text /tmp/sample.md --modalities all --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_modal.py
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- All 6 modalities produce non-empty output for a sample input.
- Decision matrix has ≥2 alternatives × ≥2 criteria.
- DAG has ≥1 edge.
- Output is recommendation only (no source mutation).

## Stop Conditions

- `modal_uses_remote_llm_v1`
- `modal_modifies_source`
- `modality_silent_failure`: every modality must return either output
  or explicit `unable: <reason>`.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0072-A — codex@GenesisOS implements modality adapters

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed.

### WP-0072-B — codex@myworld wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0072-A
