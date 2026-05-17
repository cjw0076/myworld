---
contract_id: ASC-0077
slug: genesisos-semantic-alignment-kernel
status: closed
goal: Extend GenesisOS from divergence-only into a shared-meaning kernel that maps local/project/agent language onto canonical AIOS terms before cross-agent work begins.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder directive that GenesisOS should give meaning to what AIOS builds and fix common language between agents.
closed: 2026-05-15 KST
acceptance_authority: founder/operator approval in chat
origin: founder compared the need to human translation and machine multilingual embeddings: agents must call the same thing by the same meaning to understand each other.
depends_on:
  - ASC-0065 genesisos-bootstrap
  - ASC-0076 contract-closeout-reconciliation
---

# ASC-0077 GenesisOS Semantic Alignment Kernel

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
- `docs/contracts/ASC-0077-genesisos-semantic-alignment-kernel.md`
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
and later feed it into ASC-0068 project discovery. ASC-0077 does not need to
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

### WP-0077-A — codex@GenesisOS implements semantic kernel

- target_agent: codex
- target_repo: GenesisOS
- status: closed
- depends_on: ASC-0076 classification matrix
- brief: |
    Add the semantic normalization, handshake, and diff surface. Keep it local,
    deterministic, and authority-free. Update GenesisOS docs and tests.
- return_to: `.aios/outbox/GenesisOS/asc-0077.GenesisOS.result.json`
- result: `genesisos.semantic_normalization.v1`,
  `genesisos.semantic_handshake.v1`, and `genesisos.semantic_diff.v1`
  implemented in `GenesisOS/genesisos/semantic.py` with CLI support.

### WP-0077-B — codex@myworld documents shared AIOS language

- target_agent: codex
- target_repo: myworld
- status: closed
- depends_on: WP-0077-A
- brief: |
    Add `docs/AIOS_SHARED_LANGUAGE.md` using GenesisOS canonical terms and
    mark how ASC-0068 should consume semantic handshakes later.
- return_to: `.aios/outbox/myworld/asc-0077.myworld.result.json`
- result: `docs/AIOS_SHARED_LANGUAGE.md` now carries all 20 GenesisOS
  canonical anchors, non-collapse boundary pairs, required handshake shape,
  GenesisOS semantic CLI commands, and ASC-0068 consumption notes.

### WP-0077-C — claude@myworld reviews meaning boundaries

- target_agent: claude
- target_repo: myworld
- status: proposed
- depends_on: WP-0077-A, WP-0077-B
- brief: |
    Review whether the canonical terms preserve the founder's intended
    meanings and whether any Korean/English alias collapses important nuance.
- return_to: `.aios/outbox/myworld/asc-0077.claude-review.result.json`
- result: not executed in this closeout; packet remains proposed and is not a
  blocker for WP-0077-A/B closure.

## Receipts

### 2026-05-15 KST — codex closeout

- changed: `docs/AIOS_SHARED_LANGUAGE.md`,
  `docs/contracts/ASC-0077-genesisos-semantic-alignment-kernel.md`,
  `docs/contracts/README.md`, `docs/AIOS_AGENT_LEDGER.md`, and
  `GenesisOS/docs/AGENT_WORKLOG.md`.
- GenesisOS WP-A evidence: `genesisos.semantic` defines 20 canonical AIOS
  terms, Korean/English aliases, advisory normalization, semantic handshake,
  and diff outputs. Distinct pairs remain non-collapsed:
  `contract`/`dispatch_packet`, `memory_draft`/`accepted_memory`, and
  `capability_recommendation`/`provider_route`.
- MyWorld WP-B evidence: `docs/AIOS_SHARED_LANGUAGE.md` documents the same
  canonical anchors, boundary pairs, required handshake, GenesisOS CLI usage,
  and ASC-0068 `aios.semantic_handshake.v1` consumption notes.
- verification:
  - `cd GenesisOS && python -m py_compile genesisos/semantic.py genesisos/cli.py` passed.
  - `cd GenesisOS && python -m unittest tests/test_semantic.py tests/test_cli.py` passed 13/13.
  - `cd GenesisOS && python -m genesisos.cli semantics normalize --term "작업 장부" --json` normalized to `ledger`.
  - `cd GenesisOS && python -m genesisos.cli semantics handshake --text "../AGENTS.md" --json` emitted `genesisos.semantic_handshake.v1` with recognized terms and unknown surfaces.
  - `cd GenesisOS && python -m genesisos.cli semantics diff --left "contract" --right "dispatch packet" --json` returned `same_canonical=false` with boundary note.
  - `cd GenesisOS && python -m pytest tests/ -v` passed 48/48.
  - `python scripts/aios_semantic_handshake.py --json` passed for MyWorld child repo AGENTS glossary coverage.
  - `python -m unittest tests/test_aios_semantic_handshake.py` passed 3/3.
  - `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 360/360.
  - `python scripts/aios_monitor.py assess --json` ran after closeout with
    `health=attention`; remaining attention is dirty-repo triage, not
    ASC-0077 semantic verification failure.
- boundary: GenesisOS semantic output remains `advisory_only`; it proposes
  anchors and ambiguity checkpoints but does not claim final truth, execute
  work, accept memory, or route capabilities.
