# AIOS Agent-Service Infrastructure Delta

- repo: myworld
- agent: codex@myworld
- date: 2026-06-14
- authority: source-backed planning note
- scope: official/current external agent infrastructure signals for AIOS Gate A

## Why This Exists

The active AIOS objective asks whether the field has moved beyond
Messages API -> Agent SDK -> Managed Agents, and what AIOS must absorb before
it can become a real agent-service operating system instead of a single-device
workspace.

The current answer is: the field is converging on stateful agent runtimes,
sandboxed workspaces, tracing, connectors, background execution, and
agent-to-agent interoperability. AIOS should not treat any one provider surface
as the OS. AIOS should sit above them as memory, authority, receipts, routing,
credential grants, and entropy pressure.

## Plain Language

In plain language: the big AI providers are building better hired workers.
They can keep state, use tools, run in sandboxes, expose traces, and talk to
other agents. AIOS should become the company that hires those workers, gives
them permissions, keeps the records, checks their work, and learns from every
success and failure.

AIOS must not become dependent on a worker's notebook. The company ledger,
permits, evidence, and memory belong to AIOS.

## Cross-Domain Frame

Use a hospital as the distant-domain frame. The point is not branding; it is
institutional architecture and biology under stress:

- providers are specialists and contractors;
- sandboxes are operating rooms;
- credentials are controlled medication cabinets;
- MemoryOS is the patient record and audit office;
- CapabilityOS is credentialing and procurement;
- Hivemind is scheduling and clinical operations;
- GenesisOS is morbidity-and-mortality review that forces uncomfortable
  learning before the next procedure;
- MyWorld is the hospital administration that assigns responsibility and
  records decisions.

A hospital does not become safe because a brilliant surgeon has good notes.
It becomes safe when records, permissions, rooms, reviews, and handoffs remain
coherent even when specialists change.

## Current External Signals Checked

| Signal | Official Source | AIOS Consequence |
| --- | --- | --- |
| Code-first agents now include planning, tools, specialist collaboration, state, approvals, and orchestration. | OpenAI Agents SDK: <https://developers.openai.com/api/docs/guides/agents> | MyWorld should own contracts and state strategy; providers remain vendors. |
| Sandboxes are explicitly separate from the agent harness and used for persistent workspaces, files, commands, artifacts, ports, and pause/resume. | OpenAI Sandbox Agents: <https://developers.openai.com/api/docs/guides/agents/sandboxes> | Hivemind needs workspace refs, isolation receipts, and resumable execution evidence. |
| Tracing records model calls, tool calls, handoffs, guardrails, and custom spans. | OpenAI Agents observability: <https://developers.openai.com/api/docs/guides/agents/integrations-observability> | AIOS receipts should be first-class traces; MemoryOS should ingest trace summaries as drafts, never raw private logs. |
| Conversation state now has durable session strategies for resumable approvals and app-controlled storage. | OpenAI running agents/state: <https://developers.openai.com/api/docs/guides/agents/running-agents> | AIOS needs explicit session ownership and must avoid duplicate context between local replay and provider-managed state. |
| Agent Builder exposes typed multi-step workflows that can be embedded or exported to SDK code. | OpenAI Agent Builder: <https://developers.openai.com/api/docs/guides/agent-builder> | AIOS should maintain portable contract/workflow specs rather than binding to one visual builder. |
| MCP is a standard for connecting AI apps to external data, tools, and workflows. | MCP docs: <https://modelcontextprotocol.io/docs/getting-started/intro> | CapabilityOS should track MCP/tool routes as recommendations, not execution authority. |
| Claude Messages API can connect to remote MCP servers via an MCP connector beta. | Anthropic MCP connector: <https://platform.claude.com/docs/en/agents-and-tools/mcp-connector> | Credential grants and connector scopes must be modeled before provider calls. |
| A2A is designed for secure information exchange and action coordination across agents and enterprise systems. | Google A2A announcement: <https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/> | AIOS departments should become discoverable contract-bound agents without losing MemoryOS provenance. |
| Gemini Interactions API points toward stateful multi-turn workflows, background execution, and mapping managed agents into A2A surfaces. | Google Interactions API/ADK/A2A post: <https://developers.googleblog.com/building-agents-with-the-adk-and-the-new-interactions-api/> | AIOS must plan for background tasks, remote agent cards, interaction ids, and provider-side state reconciliation. |

## Delta From ASC-0262

ASC-0262 correctly identified durable sessions, resumable sandbox workspaces,
typed execution, access grants, governed memory, observability, and Genesis
anti-convergence as serving requirements.

The 2026-06-14 delta is sharper:

1. **Harness/sandbox separation is now a first-class design boundary.**
   AIOS should never let sandbox state become the control plane.
2. **Sessions are not just chat history.** They are approval, resume,
   storage, compaction, and duplicate-context risk surfaces.
3. **Observability is not optional telemetry.** It is the substrate for
   MemoryOS drafts, support redaction, and contract closeout.
4. **MCP/A2A make tools and agents interchangeable vendors.** CapabilityOS
   must track route risk, credential scope, and fallback before execution.
5. **Managed/background agents increase state split-brain risk.** AIOS must
   know which state is provider-managed, app-managed, local replay, or
   MemoryOS-reviewed.

## Gate A Work That Can Start Before UI Selection

The following work is not blocked by `apps/serving/**` or browser proof because
it is internal, owner-bound, and non-UI:

| Contract | Owner | Why Safe Now |
| --- | --- | --- |
| ASC-0272 | MemoryOS | source/trace/provider event intake as draft memory; no user-facing UI |
| ASC-0273 | CapabilityOS | credential grant and provider blindspot schema; recommendation-only |
| ASC-0274 | GenesisOS + Hivemind | SMX design contract; execution remains gated by isolation receipts |
| ASC-0275 | GenesisOS | entropy quota check schema; speculative-only |
| ASC-0276 | MyWorld | Agent Company Studio product framing; docs-only until visual target |

## Assumptions And Negations

GenesisOS critic flagged the first draft as `assumption-silent` and
`time-frozen`. The Gate A pack therefore carries these explicit assumptions:

| Assumption | Negation | Contract Consequence |
| --- | --- | --- |
| Provider stateful agent APIs reduce AIOS infrastructure burden. | Provider-managed state increases split-brain and audit risk. | ASC-0272 must preserve source receipts and MemoryOS draft review; provider state is not authoritative memory. |
| MCP/A2A interoperability makes tools and agents easier to use. | Interoperability also makes unauthorized tool/agent movement easier. | ASC-0273 must model credential grants, route risk, revocation, and recommendation-only boundaries. |
| More branches and agents improve creativity. | Unbounded branches create cost, privacy, and false-consensus risk. | ASC-0274 and ASC-0275 require bounded branch schemas, isolation receipts, and entropy quota checks. |

## Time Horizons

| Horizon | What Should Be True | Evidence Needed |
| --- | --- | --- |
| 1 hour | Gate A contracts exist as proposed, source-backed, owner-bound artifacts. | Contract files, research delta, ledger/worklog, release gates still honest. |
| 1 week | At least one Gate A child contract has executed with tests and result packet. | Child repo test output, outbox result, MyWorld collect/ledger closeout. |
| 1 year | AIOS can treat external agents, MCP servers, A2A agents, and sandboxes as vendors under MemoryOS/CapabilityOS/Hivemind/Genesis governance. | Production serving gate, credential vault receipts, MemoryOS reviewed archive, cross-provider route observations, entropy quotas. |

## Non-Negotiable Absorption Rules

- Raw provider traces, tool outputs, MCP payloads, and web study bodies are not
  accepted memory. They become source receipts and MemoryOS drafts.
- Credential values stay outside sandboxes and prompts. Dispatch packets carry
  grant refs only.
- Provider-managed state must be reconciled with AIOS state. It is not the
  source of truth by default.
- A2A/MCP agent and tool surfaces are vendors. CapabilityOS recommends them;
  Hive executes only after a contract and receipt path exist.
- Managed/background execution does not remove the need for Hivemind receipts,
  stop conditions, retry semantics, and duplicate-action prevention.
- Major closeouts need Genesis discomfort or counter-branch evidence, not only
  green tests.
