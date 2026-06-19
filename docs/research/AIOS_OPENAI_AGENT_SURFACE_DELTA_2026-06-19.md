# AIOS OpenAI Agent Surface Delta

- repo: myworld
- agent: codex@myworld
- date: 2026-06-19
- authority: official-source planning note
- scope: OpenAI agent runtime surfaces that AIOS should absorb without becoming provider-locked

## Why This Exists

The active AIOS objective asks whether the platform world has moved past
Messages API -> Agent SDK -> Managed Agents, and what AIOS must absorb before it
can serve real users across devices, sessions, sandboxes, credentials, tools,
and memory.

As of 2026-06-19, the answer is sharper than the earlier ASC-0262/ASC-0271
baseline: OpenAI's public docs now expose a broader agent-service stack that
includes stateful Responses/Conversations, Agents SDK sessions and `RunState`,
Sandbox Agents, ChatKit, MCP/connectors, traces, and eval loops. Agent Builder
exists as a visual workflow surface, but the docs say it is being deprecated and
scheduled to shut down on November 30, 2026. The legacy Evals platform is also
deprecated; existing evals become read-only on October 31, 2026 and the Evals
dashboard/API are scheduled to shut down on November 30, 2026.

AIOS should not copy any one provider's architecture. It should absorb the
stable primitives as OS responsibilities.

## Plain Language

OpenAI is building useful parts of an agent company: workers, workspaces,
chat desks, tool vendors, activity logs, and quality reviews. AIOS should be
the company operating system above those parts. Hivemind runs work, MemoryOS
keeps the records, CapabilityOS approves routes and vendors, GenesisOS injects
discomfort and anti-consensus pressure, and MyWorld assigns authority.

## Official Signals Checked

| Signal | Official Source | AIOS Absorption |
| --- | --- | --- |
| Agents SDK is the code-first path when the application server owns orchestration, tool execution, state, approvals, and runtime behavior. | <https://developers.openai.com/api/docs/guides/agents> | MyWorld should keep workflow authority in contracts; Hivemind executes through receipts rather than outsourcing control-plane authority. |
| Agent Builder lets teams design, publish, and deploy visual workflows, but is deprecated with shutdown scheduled for 2026-11-30. | <https://developers.openai.com/api/docs/guides/agent-builder> | AIOS should treat visual builders as export/import aids only; canonical workflow state stays in contracts and receipts. |
| ChatKit can embed chats, but new apps should connect ChatKit to their own server-side agent implementation; each ChatKit session needs a unique authenticated end user. | <https://developers.openai.com/api/docs/guides/chatkit> | AIOS serving UI must preserve per-user session identity and backend-owned authority. |
| Agents SDK running guidance separates local history, SDK sessions, OpenAI-managed response chaining, and server-managed continuation. | <https://developers.openai.com/api/docs/guides/agents/running-agents> | AIOS must name which layer owns continuation to avoid duplicate context and split-brain memory. |
| Results/state surfaces include final output, replayable history, last agent, response id, interruptions, and resumable state. | <https://developers.openai.com/api/docs/guides/agents/results> | Hivemind receipts need the same boundary fields: output, owner, continuation ref, interruption, and resume state. |
| Sandbox Agents run in container-based environments with files, commands, packages, ports, snapshots, and resumable state. | <https://developers.openai.com/api/docs/guides/agents/sandboxes> | Hivemind's isolation receipts should model sandbox manifest, snapshot, resume, package, port, and filesystem boundaries. |
| MCP/connectors let models access external services and may require approvals; private MCP servers can be reached through Secure MCP Tunnel. | <https://developers.openai.com/api/docs/guides/tools-connectors-mcp> | CapabilityOS owns connector/vendor route policy, approval posture, credential refs, and official-server preference. |
| Observability guidance starts with traces showing prompts, tools, handoffs, and approvals before formal evals. | <https://developers.openai.com/api/docs/guides/agents/integrations-observability> | MemoryOS should ingest trace summaries as draft Akashic records; raw private trace bodies remain local-only. |
| Agent workflow evals use traces, graders, datasets, and eval runs to catch routing, handoff, instruction, safety, and regression failures. | <https://developers.openai.com/api/docs/guides/agent-evals> | GenesisOS should turn trace/eval failures into entropy pressure and counter-branch requirements. |
| Background mode supports long-running async Responses and polling, but stores response data briefly and is not ZDR-compatible. | <https://developers.openai.com/api/docs/guides/background> | Hivemind background jobs need retention/privacy labels and provider-state reconciliation before use in user-serving work. |
| Conversation state docs recommend Responses/Conversations for stateful multi-turn work and durable conversation IDs across sessions, devices, or jobs. | <https://developers.openai.com/api/docs/guides/conversation-state> | MemoryOS and Hivemind must distinguish provider conversation IDs from reviewed AIOS memory and local replay state. |
| The deprecations page names Agent Builder and the legacy Evals platform shutdown timelines. | <https://developers.openai.com/api/docs/deprecations> | ASC-0278 must be a reconciliation overlay, not a new implementation backlog duplicating existing contracts. |
| OpenAI's 2025 developer summary describes AgentKit as Agent Builder, ChatKit, Connector Registry, and evaluation loops; it also names AGENTS.md, MCP, and Skills as convergence points. | <https://developers.openai.com/blog/openai-for-developers-2025> | AIOS should use standard convergence where useful while preserving provider replaceability and local-first records. |

## Delta From 2026-06-14

1. **Agent Builder is not a durable target.** AIOS should not build its north
   star around a surface scheduled for shutdown on November 30, 2026.
2. **The stable target is code-first orchestration plus owned state.** Agents
   SDK, Responses/Conversations, sandbox sessions, traces, and evals map more
   cleanly to AIOS OS boundaries.
3. **Legacy Evals is also not the durable target.** AIOS should use trace
   grading and datasets as current evaluation primitives while avoiding
   dependency on deprecated Evals dashboard/API state.
4. **Session ownership is now a release-critical decision.** AIOS must decide
   per conversation whether state is local replay, SDK session, OpenAI
   conversation, background response, sandbox snapshot, or reviewed MemoryOS
   memory.
5. **Trace/eval loops are the bridge from service operation to learning.** Raw
   traces are not memory. Redacted trace summaries, grader failures, and
   route mistakes are MemoryOS draft candidates and GenesisOS discomfort fuel.
6. **Connectors are vendor routes, not authority.** MCP/connectors raise prompt
   injection, data leakage, OAuth, official-server, and private tunnel
   questions that belong in CapabilityOS before Hive executes.

## Assumptions And Negations

| Assumption | Negation | AIOS Consequence |
| --- | --- | --- |
| Managed provider state makes AIOS easier to host. | Managed state can hide retention, duplicate context, and resume authority. | Every provider state ref needs an AIOS owner, retention class, and reconciliation rule. |
| ChatKit/AgentKit can become the AIOS serving UI. | Agent Builder deprecation and provider-specific runtime shape can create lock-in. | AIOS UI may embed ChatKit-like surfaces, but canonical workflows remain server-side AIOS contracts. |
| Traces/evals are enough observability. | Trace bodies can contain raw prompts, tool output, private data, and provider-specific IDs. | MemoryOS stores redacted summaries and source refs first; acceptance requires review. |

## Time Horizons

| Horizon | Required Move | Evidence |
| --- | --- | --- |
| 1 hour | Propose one MyWorld contract that binds this external delta to OS ownership and Claude hardening. | ASC-0278 contract, this research note, ledger/worklog entry. |
| 1 week | Split ASC-0278 into owner-specific child contracts for Hivemind, MemoryOS, CapabilityOS, and GenesisOS. | Dispatch packets, result packets, tests, and closeout ledger entries. |
| 1 year | AIOS can swap OpenAI, Claude, Gemini, local, MCP, and future managed-agent surfaces without losing memory, authority, or traceability. | Serving release proof, reviewed Akashic archive, credential-grant receipts, trace/eval ingestion, and cross-provider route observations. |

## Absorption Rules

- Provider conversation IDs, response IDs, sandbox snapshots, and background job
  IDs are source references, not accepted AIOS memory.
- User identity, end-user session identity, credential grants, and connector
  OAuth scopes must never be inferred from provider convenience fields alone.
- Raw traces, prompt bodies, tool outputs, MCP payloads, and sandbox file bodies
  stay out of public/shared docs.
- Agent Builder workflows may be imported or exported for transition, but AIOS
  canonical workflow definitions must remain contract-bound and provider
  replaceable.
- Any background or sandbox execution that can retry a user-affecting action
  must carry duplicate-action prevention receipts.
- Major serving closeouts must include trace/eval evidence and a GenesisOS
  counter-branch or discomfort finding.
