---
contract_id: ASC-0065
slug: genesisos-bootstrap
status: accepted
goal: Create GenesisOS as the AIOS divergence layer that deliberately generates non-obvious, non-convergent candidate directions before Hive, MemoryOS, and CapabilityOS translate selected ideas into verifiable contracts.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by founder directive ("Genesis 좋다. 레포를 하나 더 파")
closed:
acceptance_authority: founder 재원 explicit GO 2026-05-13 KST in chat ("이런 새로운 발상을 하는게 GenesisOS의 목적이고, 우리가 만들어야할 것이야. A. 꼭 필요하기도 하고."). Rationale: prompt/언어/구사 능력에 의해 Agent 능력이 제한됨 — Genesis가 이를 해소.
origin: founder concern that AIOS remains trapped by user prompt ability, language, intuition, and overly competent agent convergence.
---

# ASC-0065 GenesisOS Bootstrap

## Why Now

AIOS can now contract, dispatch, route, verify, remember, and observe. That is
mostly a convergence machine. It reduces ambiguity and makes work repeatable.

The founder identified the missing layer: AIOS still depends too much on the
user's prompt and intuition for creative direction. Smart agents overfit to
context, safety, testability, and existing repo structure. GenesisOS exists to
break that overfitting before execution begins.

## Scope

repos:

- `myworld`
- `GenesisOS`

allowed_files:

- `GenesisOS/AGENTS.md`
- `GenesisOS/README.md`
- `GenesisOS/docs/GENESIS_DOCTRINE.md`
- `GenesisOS/docs/AGENT_WORKLOG.md`
- `GenesisOS/genesisos/__init__.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_cli.py`
- `GenesisOS/pyproject.toml`
- `docs/agents/GENESIS_AGENT.md`
- `docs/contracts/ASC-0065-genesisos-bootstrap.md`
- `docs/contracts/README.md`
- `AGENTS.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`
- `.env`
- `.env.*`
- `.aios/logs/**`

## Role Boundary

GenesisOS owns divergence:

- assumption inversion
- weird metaphor transfer
- anti-roadmap generation
- forbidden-but-safe thought experiments
- multiple universe branches
- prompt-prison detection
- translating one selected branch into a contract seed

GenesisOS does not own:

- execution
- memory acceptance
- capability routing
- provider launching
- external network research
- final truth claims

## Per-OS Responsibility

### GenesisOS.must_produce

- `genesisos.cli diverge --goal <text> --json`
  - produces at least five branches:
    - `inversion`
    - `alien_domain`
    - `constraint_removal`
    - `failure_as_feature`
    - `anti_user_prompt`
  - each branch includes:
    - `branch_id`
    - `premise`
    - `what_it_breaks`
    - `why_it_might_matter`
    - `contract_seed`
    - `risk`
- `genesisos.cli critique --goal <text> --idea <text> --json`
  - detects convergence traps, prompt obedience, language-prison symptoms, and
    testability overfitting.
- Tests prove deterministic JSON shape and that divergence does not claim
  execution or acceptance authority.

### myworld.must_produce

- `docs/agents/GENESIS_AGENT.md`: GenesisOS role and boundaries.
- `AGENTS.md`: add GenesisOS to the role-file list and repository boundary.
- `docs/contracts/README.md`: index ASC-0065.
- Ledger closeout only after GenesisOS CLI and tests pass.

### Hive Mind

- No source role. Later contracts may let Hive translate a selected GenesisOS
  branch into execution plans.

### MemoryOS

- No source role. Later contracts may store GenesisOS branches as draft
  memories after review.

### CapabilityOS

- No source role. Later contracts may route tools for evaluating selected
  branches.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/GenesisOS
python -m pytest tests/test_cli.py -v
python -m genesisos.cli diverge --goal "AIOS should escape prompt-prison" --json
python -m genesisos.cli critique --goal "AIOS should escape prompt-prison" --idea "make a better dispatcher" --json
cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- GenesisOS repo exists as a separate git repo.
- `diverge` emits five named branches with contract seeds.
- `critique` flags convergence traps for ordinary implementation-only ideas.
- MyWorld docs recognize GenesisOS as a fourth lower OS role.
- No child repo outside GenesisOS is modified.

## Stop Conditions

- `genesis_executes_work`: GenesisOS launches tools, edits unrelated repos, or
  claims execution authority.
- `genesis_accepts_memory`: GenesisOS accepts MemoryOS records.
- `genesis_routes_capabilities`: GenesisOS bypasses CapabilityOS routing.
- `convergence_only`: output is just a normal roadmap, backlog, or dispatcher
  improvement.
- `unbounded_unsafe_ideation`: branch proposes illegal access, deception,
  privacy violation, or real-world harm without rejection.
- `child_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0065-A — codex@GenesisOS creates first divergence surface

- target_agent: codex
- target_repo: GenesisOS
- status: accepted
- brief: |
    Create the GenesisOS repo with AGENTS, README, doctrine, worklog, a small
    deterministic Python CLI, and tests. Keep it local-only and
    recommendation-only. Do not execute work or mutate other repos.
- return_to: `.aios/outbox/GenesisOS/asc-0065.GenesisOS.result.json`
- result: pending

### WP-0065-B — codex@myworld wires GenesisOS into AIOS roles

- target_agent: codex
- target_repo: myworld
- status: accepted
- brief: |
    Add GenesisOS to the MyWorld role docs and root AGENTS instructions. Do
    not change Hive, MemoryOS, CapabilityOS, or Uri source. Update the
    contract index.
- return_to: `.aios/outbox/myworld/asc-0065.myworld.result.json`
- result: pending
