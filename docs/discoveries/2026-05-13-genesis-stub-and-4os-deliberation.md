# Genesis stub + 4-OS distributed deliberation — Founder pick

Founder turn 2026-05-13: "aios 토론 4-OS 각자가 가져가. genesis inversion은
왜 계속 같은 답만 내뱉는지? genesisOS의 역할이 명확하지 않은가?"

## Q1 — Genesis가 같은 답만 내뱉는 이유

Verified by reading `GenesisOS/genesisos/cli.py`:

- 144 lines total
- 5 hardcoded `BRANCH_TYPES`: `inversion / alien_domain / constraint_removal /
  failure_as_feature / anti_user_prompt`
- Each is a fixed Python tuple of (premise, breaks, why_might_matter)
- Goal text gets inserted via slug substitution
- **Zero LLM calls. Zero true divergence.**

Every aios_invoke returned same first 3 branches because the stub returns
type[0:3] regardless of input.

**Genesis role IS clear in spec** (divergence, assumption mutation, multi-
universe branches, prompt-prison critique, contract seeds before
verification — per `docs/agents/GENESIS_AGENT.md`). But the spec is fully
unimplemented:

- ASC-0065 bootstrap: closed (just scaffold)
- ASC-0069 prompt-prison critic: accepted, not yet built
- ASC-0070 assumption mutator: accepted, not yet built
- ASC-0071 multi-universe branches: accepted, not yet built
- ASC-0072 multi-modal reasoning: accepted, not yet built
- ASC-0073 cross-domain analogy: accepted, not yet built
- ASC-0074 pre-close challenge: accepted, not yet built
- ASC-0075 seed library: accepted, not yet built
- ASC-0077 semantic alignment kernel: accepted, not yet built

**ALL of GenesisOS's real capabilities are in the open-contract queue but
none have been executed.** The 144-line stub is what's actually running.

## Q2 — 4-OS distributed deliberation

Today every "토론" routes through Hive only (ASC-0084, ASC-0089 pattern).
Hive does 5 rounds × 3 voices internally. But the OTHER 3 OS don't
participate as deliberation peers — they only serve as Hive's data sources
(MemoryOS context, CapabilityOS recommend) or as silent audit recipients.

Founder asks for **each OS to take a piece of the deliberation**:

- **MemoryOS lane**: what does prior accepted memory + ledger say?
  Surfaces precedent, prior reasoning, similar past decisions.
- **CapabilityOS lane**: what routes/tools/providers actually apply?
  Surfaces capability fit, fallback options, observation history.
- **GenesisOS lane**: what divergent / inverted / cross-domain branches?
  Surfaces non-obvious alternatives, prompt-prison signatures.
- **Hive lane**: how to verify each candidate? Adversarial probing.
  Surfaces breakage scenarios, scaling tests, composability conflicts.

Each OS produces its own artifact in parallel; a synthesis layer composes
them; operator (or founder) decides on the composed output.

This is structurally different from current Hive-only deliberation.

## Branches for founder pick

### B1 — fix Genesis stub first (then everything else gets real divergence)

- Implement ASC-0069 (critic) + ASC-0071 (branches) with actual LLM call
  (CapabilityOS top recommends Ollama Qwen 2.5 7B, which is local + cited)
- Each invocation produces context-specific branches, not template fills
- Side-effect: 4-OS deliberation gets non-trivial Genesis input automatically
- Cost: 1-2 days of work; depends on Hive worker spec for Genesis

### B2 — implement 4-OS deliberation primitive (independent of Genesis fix)

- New `aios_deliberate.py --topic "<text>" --rounds N --json` script
- Calls each OS sequentially (or parallel) with topic-specific prompts
- Composes 4 outputs into a synthesis doc (similar to Hive `final_state.md`)
- Operator-mode action: replaces ASC-0084-style single-OS Hive contracts
  with 4-OS distributed deliberations
- Cost: 1 day; standalone

### B3 — both as a coordinated sequence

- B1 first (so Genesis lane is real), then B2 (so 4-OS deliberation
  produces real output not stub-fill)
- Cost: 2-3 days total

### B4 — escalate to Hive (irony noted)

- Route this options doc itself to Hive ASC-0084-style adversarial
  deliberation. Hive picks B1/B2/B3.
- Cost: ~1h Hive deliberation; result feeds operator action.

### B5 — founder direct call

- Founder's intuition picks one. Operator implements via AIOS tools.

## Operator (claude) recommendation

**B3 (B1 then B2)**, and don't escalate to Hive this time — Hive without
real Genesis input would just produce more single-mode worker output.

But B5 (founder direct) is also fine if founder has clear intuition.

NOT auto-drafting. Surface to founder per discipline.

---

## Bonus observation — the recursion

Founder's question about Genesis's repetitive output is itself a
prompt-prison signature **applied to AIOS by the founder**. AIOS missed
it because Genesis (which was supposed to detect this) is the one stuck.

Self-referential gap: the system meant to catch convergent-default IS
convergent-default. Worth preserving as a Genesis seed when ASC-0075
(seed library) ships.
