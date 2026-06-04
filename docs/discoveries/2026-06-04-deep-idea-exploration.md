# 2026-06-04 Deep Idea Exploration

- repo: myworld
- agent: codex@myworld
- role: GenesisOS-assisted idea exploration
- authority: speculative_only
- goal: Explore how AIOS can support deep idea exploration without collapsing
  into ordinary task execution.
- evidence:
  - `GenesisOS: python -m genesisos.cli diverge --goal ... --json`
  - `GenesisOS: python -m genesisos.cli critique --goal ... --idea ... --json`
  - `GenesisOS: python -m genesisos.cli critic --text ... --json`
  - `GenesisOS: python -m genesisos.cli discomfort --text ... --json`
  - `GenesisOS: python -m genesisos.cli mutate --record <fd> --no-write --json`
  - `GenesisOS: python -m genesisos.cli analogy match --text ... --generated --json`
  - `GenesisOS: python -m genesisos.cli modal translate --to decision_matrix|dag --json`

## Finding

The highest-value primitive is not a brainstorming mode. It is a governed
divergence chamber.

Brainstorming asks for more ideas, ranks them, and moves toward execution.
That repeats the current failure mode: helpful agents convert uncertainty into
plans too early. A divergence chamber should instead preserve the uncomfortable
part of the question long enough for assumptions, alien analogies, time
horizons, and failure modes to mutate separately.

## Candidate Primitive

`DeepIdeaChamber`

- input: a discomfort, goal, or stuck point
- phase 1: semantic handshake, to prevent term drift
- phase 2: prompt-prison critic, to name hidden assumptions and frozen time
- phase 3: divergence branches, at least inversion, alien-domain,
  constraint-removal, failure-as-feature, and anti-user-prompt
- phase 4: assumption rotations across negate, scale, audience, time, risk,
  and modality
- phase 5: analogy match with an explicit return path
- output: contract seeds, risks, and verification challenges
- non-output: no execution, no accepted memory, no provider route, no final
  truth claim

## Strong Branches

1. **Labyrinth Thread**
   Exploration must carry its return path before entering complexity. For
   AIOS, every deep idea branch should include `trace_id`, source discomfort,
   rollback path, and the exact contract seed it may become.

2. **Load Path**
   Every claim needs a visible path to authority. A deep idea should show
   whether it belongs to GenesisOS, MyWorld, MemoryOS, CapabilityOS, or Hive
   before it can harden into work.

3. **Discomfort As Design Material**
   The signal is not "the user needs more ideas." The signal is that AIOS keeps
   converting discomfort into execution. GenesisOS should preserve discomfort
   as a first-class artifact until MyWorld accepts a contract.

4. **Time-Split Exploration**
   Each candidate should be evaluated in 1-hour, 1-week, and 1-year forms. If
   an idea only makes sense in one horizon, it is probably an implementation
   patch, not an operating primitive.

5. **Non-Prose Branch**
   Ideas should sometimes become diagrams, schemas, matrices, or rituals before
   prose summaries. This breaks the assumption that depth means longer text.

## Contract Seeds

### ASC-SEED DeepIdeaChamber

- owner repo: GenesisOS for advisory generation; myworld for governance
- supporting repos: MemoryOS for draft-only provenance, CapabilityOS for route
  questions, Hive for later verification design
- allowed files: `GenesisOS/genesisos/**`, `GenesisOS/tests/**`,
  `docs/contracts/**`, `docs/discoveries/**`, `docs/AIOS_AGENT_LEDGER.md`
- forbidden files: `.env*`, raw exports, provider auth files, private logs
- required outputs: branch set, assumption rotations, analogy match,
  discomfort map, contract seed list, risk list
- verification gate: deterministic JSON schema tests plus one replayable
  discovery note
- stop conditions: execution claim, memory acceptance, capability routing,
  unsafe real-world action, provider-output-as-truth

### ASC-SEED ExplorationReturnPath

- goal: require every speculative branch to carry a return path before it can
  enter a contract.
- required fields: `source_discomfort`, `branch_id`, `authority`, `risk`,
  `candidate_owner`, `rollback_path`, `verification_question`
- reason: prevents deep exploration from becoming unbounded prose or hidden
  operator memory.

## Risks

- The chamber can become ceremony if outputs are not contractable.
- Local generative analogy can introduce low-quality library entries; generated
  helper text must remain advisory.
- The mutate CLI still requires a file path, so inline exploration needed an
  fd workaround. That is a small GenesisOS usability gap.
- A "best idea" selection step is dangerous unless MyWorld explicitly governs
  it. GenesisOS should rank tension, not truth.

## Next

Draft an ASC contract for `DeepIdeaChamber` only if the operator wants this
primitive promoted from discovery to implementation. Until then, preserve this
as speculative evidence, not accepted architecture.
