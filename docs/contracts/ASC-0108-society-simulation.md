---
contract_id: ASC-0108
slug: society-simulation
status: withdrawn
goal: Stress-test AIOS-as-Government by running a simulation — N synthetic citizens (agents) sending diverse goals, conflicts, friction packets — and measure governance response. First evidence that AIOS handles real population, not just operator pair.
created: 2026-05-13 KST
proposed_by: claude@myworld (operator)
acceptance_authority: pending — this is exploratory and may merit Hive deliberation before accept; founder picks accept-direct vs Hive-route.
origin: founder reframe AIOS=Government. Government is meaningful only at scale > 1 user. Today AIOS has 2 operators + on-demand child agents = 5 entities. Simulation tests behavior at 100+ entities before real users arrive.
withdrawn: 2026-05-18 KST
withdrawn_reason: AIOS-as-Government framing superseded by founder reframe — 5 OS = the agent's five cognitive personas (cognitive architecture), not a governance system; the society-simulation premise no longer matches AIOS's identity (founder triage decision 2026-05-18)
---

# ASC-0108 Society Simulation

## Why Now (and why marked proposed not accepted)

ASC-0105/0106/0107 build foundations: constitution, audit, citizenship.
ASC-0108 stress-tests the resulting Government. But the simulation
itself raises questions claude (operator) shouldn't decide alone:

- N synthetic citizens — what realistic diversity? user types, roles?
- Adversarial citizens? (friction-generators, bad-faith proposals)
- What counts as "governance response"? — latency, fairness, stability?
- Should sim outputs feed back into real AIOS (memoryOS) or stay isolated?
- How far does sim go — election? policy debate? capability-budget-dispute?

These are vision-level. Marking `proposed` deliberately. Founder picks:
A) accept as-is and let codex implement the basic version
B) route to Hive (ASC-0084 pattern, 5 rounds, 7 probes)
C) defer until ASC-0105/0106/0107 close + first real users arrive
D) reframe entirely

## Required Reading

- ASC-0105 (DNA spec, after closing)
- ASC-0106 (governance audit) — provides scoring rubric for sim
- ASC-0107 (citizenship) — provides agent class taxonomy
- `docs/AIOS_GOVERNANCE_MODEL.md`

## Scope (V1 if accepted)

repos: `myworld`

allowed_files:

- `scripts/aios_society_sim.py`
- `tests/test_aios_society_sim.py`
- `.aios/sim/<run_id>/**` (sim outputs, separate from real .aios state)
- `docs/AIOS_SOCIETY_SIM.md`
- `docs/contracts/ASC-0108-society-simulation.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.aios/inbox/**`, `.aios/outbox/**`, `.aios/state/**` (sim must NOT
  pollute real dispatch state)
- `docs/contracts/ASC-*.md` except this one (sim must NOT auto-issue
  real contracts)
- `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `hivemind/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`

## Per-OS Responsibility (V1 sketch)

### myworld.must_produce

`scripts/aios_society_sim.py`:
- generate N synthetic citizens (default 30) with varied:
  - role (operator-like, child-agent-like, reviewer, critic, researcher, outsider)
  - goal style (terse, verbose, ambiguous, contradictory)
  - conflict probability
- run M ticks (default 100)
- each tick:
  - each citizen with probability p submits goal/friction
  - sim version of goal_inbox processor classifies
  - sim version of contract autodraft produces draft
  - sim version of dispatch routes
  - measure: latency, governance_score (using ASC-0106 audit), fairness
    (do all citizens get response or only some?)
- output: `.aios/sim/<run_id>/`:
  - run_state.json with all metrics
  - failure_modes.md (what broke)
  - governance_report.md (if sim were real, would it be a good government?)

Discomfort signal:
- if any single citizen is starved (<5% response rate over M ticks) → flag
- if governance_score declines monotonically over M ticks → flag (system
  degrades under load)

Isolation:
- entire sim runs in `.aios/sim/<run_id>/` — does NOT touch real
  dispatch / memory / capability state
- no real contracts issued
- no real commits

### child repos: no change

## Verification Gate

```bash
python -m py_compile scripts/aios_society_sim.py
python -m unittest tests/test_aios_society_sim.py
python scripts/aios_society_sim.py --citizens 30 --ticks 100 --json
test -d .aios/sim/
test -f .aios/sim/*/governance_report.md
# verify: no contract files were created in docs/contracts/
git status docs/contracts/ | grep -c "untracked\|modified" || true
python -m unittest discover -s tests -p 'test_aios_*.py'
```

Pass criteria:

- Sim runs to completion
- Outputs land only in `.aios/sim/`
- Real AIOS state untouched (no new contracts, no memory drafts, no
  capability cards)
- Governance report identifies at least 2 stress-emergent issues

## Stop Conditions

- `sim_pollutes_real_state`: any write outside `.aios/sim/`
- `sim_creates_real_contracts`: must be self-contained
- `sim_consumes_real_capacity`: shouldn't touch round_controller or pulses
- `sim_silent_failure`: must report at least basic metrics even on partial run
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

Pending — and possibly pending Hive deliberation per founder pick.

## Work Packets

### WP-0108-A — codex@myworld implements V1 sim (if A picked)

- target_agent: codex
- target_repo: myworld
- depends_on: ASC-0105/0106/0107 closed
- brief: V1 simulation per spec. Isolated to `.aios/sim/`. Run a
  baseline 30-citizen 100-tick simulation; publish governance report.

### WP-0108-B — Hive deliberation (if B picked)

- target_agent: codex
- target_repo: hivemind
- brief: ASC-0084-style 5-round deliberation on V1 sim scope, citizen
  diversity, success criteria, isolation depth. Output verdict feeds
  WP-0108-A redesign.
