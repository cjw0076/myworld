# Hive AIOS DNA Debate Result

ASC-0084 completed a 5-round Hive deliberation under
`hivemind/.runs/aios_dna_debate/`. Each round contains proposer, critic,
extender, and synthesis artifacts, followed by `final_state.md`.

The convergence verdict is `accept_with_dissent`. All three voices accepted a
DNA v0 package, but preserved four dissent points for future amendment. The
initial 7-invariant candidate became 8 invariants after the debate separated
principle from mechanism and added a reversibility requirement.

Final invariant set:

1. Decide before acting.
2. Draft-first.
3. No record destroyed, with a privacy-redaction tombstone exception.
4. Every loop has a named exit.
5. Provenance chain.
6. Operator override always possible, except where the privacy boundary has
   precedence.
7. AIOS never sends private-gated data.
8. Classify before committing.

Key additions from the debate:

- a 5-clause scope/security/root-of-trust/prompt-safety/liveness preamble;
- an interaction map for invariant conflicts, especially audit versus privacy;
- an amendment clause requiring future Hive deliberation;
- drift markers per invariant;
- a dissent register covering detection-first security, review quality,
  privacy-redaction tombstones, and execution-decision granularity.

Recommendation: open a downstream contract to write `docs/AIOS_DNA.md` from
the final-state package. That downstream spec should include compliance tests,
the interaction map, the dissent register, and the amendment clause. ASC-0084
deliberately did not create the DNA spec file.
