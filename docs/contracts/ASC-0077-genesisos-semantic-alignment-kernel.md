---
contract_id: ASC-0077
slug: genesisos-semantic-alignment-kernel
status: accepted
goal: Extend GenesisOS from divergence-only into a shared-meaning kernel that maps local/project/agent language onto canonical AIOS terms before cross-agent work begins.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder directive that GenesisOS should give meaning to what AIOS builds and fix common language between agents.
closed:
acceptance_authority: founder/operator approval in chat
origin: founder compared the need to human translation and machine multilingual embeddings: agents must call the same thing by the same meaning to understand each other.
depends_on:
  - ASC-0065 genesisos-bootstrap
  - ASC-0069 contract-closeout-reconciliation
---

# ASC-0070 GenesisOS Semantic Alignment Kernel

## Why Now

AIOS is becoming a multi-agent, multi-project ecosystem. Different agents,
models, repos, languages, and users may use the same word with different
meaning. That causes subtle execution errors: one agent says "contract" and
means a Markdown proposal; another means accepted authority; another means a
provider prompt.

GenesisOS should not only generate divergent futures. It should also stabilize
shared meaning before the system converges. This is analogous to human
translation and multilingual embeddings: surface forms differ, but the system
needs a canonical semantic anchor.

## Scope

repos:

- `GenesisOS`
- `myworld`

allowed_files:

- `GenesisOS/genesisos/semantic.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_semantic.py`
- `GenesisOS/docs/GENESIS_SEMANTICS.md`
- `docs/AIOS_SHARED_LANGUAGE.md`
- `docs/contracts/ASC-0070-genesisos-semantic-alignment-kernel.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

read_only_files:

- `docs/AIOS_DEFINITION.md`
- `docs/AIOS_NORTHSTAR.md`
- `docs/AIOS_SMART_CONTRACT.md`
- `docs/AIOS_WORK_DISPATCH.md`
- `docs/AIOS_SWARM_NORTHSTAR.md`
- `docs/agents/*.md`
- child repo `AGENTS.md`

forbidden_files:

- Hive execution code
- MemoryOS accepted-memory stores
- CapabilityOS routing execution
- provider execution
- raw private exports
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.env`
- `.env.*`

## Semantic Kernel V1

GenesisOS must define canonical AIOS terms and map aliases to them.

Initial canonical terms:

- `aios`
- `myworld`
- `hive_mind`
- `memoryos`
- `capabilityos`
- `genesisos`
- `contract`
- `accepted_contract`
- `dispatch_packet`
- `receipt`
- `ledger`
- `memory_draft`
- `accepted_memory`
- `capability_recommendation`
- `provider_route`
- `projection`
- `local_posterior_belief`
- `operator_checkpoint`
- `stop_condition`
- `semantic_handshake`

CLI:

```bash
cd GenesisOS
python -m genesisos.cli semantics normalize --term "작업 장부" --json
python -m genesisos.cli semantics handshake --text "../AGENTS.md" --json
python -m genesisos.cli semantics diff --left "contract" --right "dispatch packet" --json
```

Required output schemas:

- `genesisos.semantic_normalization.v1`
- `genesisos.semantic_handshake.v1`
- `genesisos.semantic_diff.v1`

## MyWorld Integration

MyWorld must document the canonical language in `docs/AIOS_SHARED_LANGUAGE.md`
and later feed it into ASC-0068 project discovery. ASC-0070 does not need to
wire ASC-0068 automatically, but the schema must be compatible with
`aios.semantic_handshake.v1`.

## Verification Gate

```bash
cd GenesisOS
python -m py_compile genesisos/semantic.py genesisos/cli.py
python -m unittest tests/test_semantic.py tests/test_cli.py
python -m genesisos.cli semantics normalize --term "작업 장부" --json
python -m genesisos.cli semantics handshake --text "../AGENTS.md" --json
python -m genesisos.cli semantics diff --left "contract" --right "dispatch packet" --json

cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Korean aliases such as `작업 장부`, `계약`, `기억`, `능력`, `실행`, and
  `의미 정렬` normalize to stable canonical terms.
- Distinct AIOS terms do not collapse incorrectly: `contract` is not
  `dispatch_packet`, `memory_draft` is not `accepted_memory`, and
  `capability_recommendation` is not tool execution.
- Handshake output lists recognized terms, unknown terms, and ambiguities.
- Diff output explains overlap and boundary between two terms.
- GenesisOS does not claim final truth; it proposes canonical anchors and
  ambiguity checkpoints.
- No provider execution, no MemoryOS acceptance, no CapabilityOS execution.

## Stop Conditions

- `semantic_collapse`
- `canonical_truth_claim`
- `execution_authority_leak`
- `memory_lifecycle_confusion`
- `capability_recommendation_treated_as_execution`
- `translation_without_ambiguity_report`
- `verification_gate_failed`

## Work Packets

### WP-0070-A — codex@GenesisOS implements semantic kernel

- target_agent: codex
- target_repo: GenesisOS
- status: accepted
- depends_on: ASC-0069 classification matrix
- brief: |
    Add the semantic normalization, handshake, and diff surface. Keep it local,
    deterministic, and authority-free. Update GenesisOS docs and tests.
- return_to: `.aios/outbox/GenesisOS/asc-0070.GenesisOS.result.json`
- result: pending

### WP-0070-B — codex@myworld documents shared AIOS language

- target_agent: codex
- target_repo: myworld
- status: accepted
- depends_on: WP-0070-A
- brief: |
    Add `docs/AIOS_SHARED_LANGUAGE.md` using GenesisOS canonical terms and
    mark how ASC-0068 should consume semantic handshakes later.
- return_to: `.aios/outbox/myworld/asc-0070.myworld.result.json`
- result: pending

### WP-0070-C — claude@myworld reviews meaning boundaries

- target_agent: claude
- target_repo: myworld
- status: proposed
- depends_on: WP-0070-A, WP-0070-B
- brief: |
    Review whether the canonical terms preserve the founder's intended
    meanings and whether any Korean/English alias collapses important nuance.
- return_to: `.aios/outbox/myworld/asc-0070.claude-review.result.json`
- result: pending
