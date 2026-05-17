# Hive ASC-0088 Alternatives Debate Result

ASC-0089 completed a 5-round Hive deliberation under
`hivemind/.runs/asc0088_alternatives_debate/`.

The convergence verdict is `pick_B1` with unanimous agreement. Hive rejected
ASC-0088's current B5 direction, which proposed a full standalone interface
spec plus buffer/sync infrastructure. The selected path is a tiny,
substrate-neutral AIOS Agent Interface Protocol definition: one Markdown spec,
roughly 50-80 lines, with no daemon, no sync system, no library requirement,
and no helper infrastructure in the first step.

The core reasoning:

- B1 has the lowest creation, maintenance, migration, and abandonment cost.
- B1 is most substrate-equivalent: cloud LLMs, local LLMs, scripts, and future
  providers can all read Markdown.
- B4 is not a valid starting point because ASC-0087 is a contract, not shipped
  machinery yet.
- B3 and B4 remain useful future layers, but only after the protocol definition
  exists.
- B5 is premature infrastructure and has the highest drift/sync failure risk.

Design requirements for the B1 successor:

- include `spec_version` in every observation;
- keep the spec near 80 lines, with extensions elsewhere;
- include an embedded YAML schema block;
- define the canonical observation path;
- define field semantics, examples, and evidence reference taxonomy;
- name retention as an open question;
- include known limitations instead of pretending the tiny spec solves sync.

Recommended disposition: supersede ASC-0088 with a new contract for B1:
`docs/AIOS_AGENT_INTERFACE.md`, tiny spec only, optionally with a validator.
Do not release ASC-0088 as written.
