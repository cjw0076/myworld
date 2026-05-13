---
contract_id: ASC-0073
slug: genesis-cross-domain-analogy
status: accepted
goal: Add a GenesisOS analogy engine that pulls solution patterns from unrelated domains (biology, geology, music, architecture, sports, mythology, etc.) and proposes how they apply to a current AIOS problem, breaking domain frame-lock.
created: 2026-05-13 KST
proposed_by: claude@myworld
acceptance_authority: claude@myworld (operator) per founder "네가 판단" delegation 2026-05-13 KST. Founder declined to micromanage; operator pair authorized for batch decisions on this proposed queue.
origin: founder directive on prompt-prison. Cross-domain analogy is one of the most powerful escape mechanisms — biology's evolution patterns, music's polyphony, architecture's load-bearing all encode novel solutions.
---

# ASC-0073 Genesis Cross-Domain Analogy Engine

## Why Now

When stuck on a software / AI problem, the most useful unlock is often
a pattern from a completely different field:

- "Mitochondria are foreign cells the host absorbed" → AIOS absorbs
  external providers as cards (ASC-0050 was implicitly biological)
- "A trio fugue has 3 independent voices" → multi-universe branches
  (ASC-0071) is musical
- "Load path must reach foundation" → privacy boundary chains
- "Compound interest is exponential" → memory accumulation

The analogy engine maintains a small curated library of well-known
patterns from N domains and matches them against current AIOS state /
open contracts.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/analogy.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/genesisos/data/analogy_library.json`
- `GenesisOS/tests/test_analogy.py`
- `GenesisOS/docs/CROSS_DOMAIN.md`
- `scripts/aios_genesis_analogy.py`
- `tests/test_aios_genesis_analogy.py`
- `docs/contracts/ASC-0073-genesis-cross-domain-analogy.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility

### GenesisOS.must_produce

- `analogy_library.json` seeded with ≥30 well-known patterns across
  ≥6 domains (biology, music, architecture, geology, sports,
  mythology, mathematics, economics, war/strategy, urban planning).
  Each entry: `{id, domain, pattern_name, abstract_rule,
  example_in_domain, suggested_applications: [aios_term, ...]}`.
- `genesisos.analogy.Analogy.match(current_problem_text) → ranked list`
  using bag-of-terms over `abstract_rule + suggested_applications`.
- `genesisos cli analogy match --text <file> --top N --json`
- `genesisos cli analogy add --domain D --pattern-name P --rule R
  --example E --applications A1,A2 --json` (operator can grow library)
- `CROSS_DOMAIN.md` lists all entries + how to add.

### myworld.must_produce

- `scripts/aios_genesis_analogy.py` wrapper — for a given contract,
  surfaces top-3 analogies as a `.aios/genesis_analogies/<id>.json`
  artifact. Recommendation only.
- Test.

### Hive / Memory / Capability

- No source change.

## Verification Gate

```bash
cd GenesisOS && python -m pytest tests/test_analogy.py -v
python -m genesisos.cli analogy match --text /tmp/sample.md --top 3 --json
python -m genesisos.cli analogy add --domain biology --pattern-name "test" --rule r --example e --applications x --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest tests/test_aios_genesis_analogy.py
python scripts/aios_genesis_analogy.py --contract-id ASC-0050 --json
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Library has ≥30 entries across ≥6 domains.
- Match returns ≥3 ranked patterns for a non-trivial input.
- Each match cites domain + abstract_rule + applications.

## Stop Conditions

- `analogy_modifies_source`
- `analogy_executes_action`: only suggests, never acts.
- `library_silent_drift`: any new entry must be operator-attributable.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending.

## Work Packets

### WP-0073-A — codex@GenesisOS implements engine + library

- target_agent: codex
- target_repo: GenesisOS
- depends_on: ASC-0065 closed.

### WP-0073-B — codex@myworld wrapper

- target_agent: codex
- target_repo: myworld
- depends_on: WP-0073-A
