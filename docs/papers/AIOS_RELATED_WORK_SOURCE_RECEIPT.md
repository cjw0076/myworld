# AIOS Related Work Source Receipt

Status: source receipt for ASC-0161  
Date: 2026-05-14  
Scope: primary sources and official project documentation for positioning the
AIOS operating-layer paper.

## Source Table

| ID | Source | Type | Relevance To AIOS |
| --- | --- | --- | --- |
| RW-001 | AutoGen: <https://arxiv.org/abs/2308.08155> | research paper | Multi-agent conversation framework with customizable conversable agents using LLMs, humans, and tools. AIOS differs by emphasizing local contracts, dispatch receipts, memory review, and provider CLI wrapping as an operating layer. |
| RW-002 | LangGraph overview: <https://docs.langchain.com/oss/python/langgraph/overview> | official docs | Low-level orchestration runtime for long-running, stateful agents with durable execution, persistence, and human-in-the-loop. AIOS overlaps on stateful orchestration but focuses on local artifact governance around provider CLIs. |
| RW-003 | SWE-agent: <https://arxiv.org/abs/2405.15793> | research paper | Agent-computer interface for software engineering agents. AIOS aligns with the idea that agents need interfaces, but its unit of design is the operating loop around multiple provider substrates. |
| RW-004 | OpenHands: <https://arxiv.org/abs/2407.16741> | research paper | Platform for software-development agents that write code, use command lines, browse the web, coordinate agents, and run benchmarks. AIOS should cite it as adjacent software-agent infrastructure, not as a competitor model. |
| RW-005 | Temporal docs: <https://docs.temporal.io/> | official docs | Durable workflow platform emphasizing crash-proof resume after failures. AIOS borrows the durability motivation but implements lightweight local contracts and receipts rather than a distributed workflow engine. |
| RW-006 | OpenAI Swarm README: <https://github.com/openai/swarm> | official repository | Educational multi-agent orchestration with lightweight controllable handoffs. AIOS differs by treating provider state, memory, capability, and governance as persistent local operating artifacts. |
| RW-007 | CrewAI introduction: <https://docs.crewai.com/en/introduction> | official docs | Agent teams and structured flows combining autonomous crews with stateful process control. AIOS can position its five OS roles as a lower-level operating discipline around provider CLIs rather than an application framework. |
| RW-008 | Cloudflare long-running agents: <https://developers.cloudflare.com/agents/concepts/long-running-agents/> | official docs | Long-running agents as durable identities with persistent state, wake/sleep lifecycle, recovery, and workflows. AIOS shares the long-running-agent problem framing while remaining local-first and file/artifact-based. |

## Source Notes

- AutoGen establishes multi-agent conversation as a broad application
  framework. AIOS should not claim to invent multi-agent orchestration.
- LangGraph and CrewAI both make state/control first-class. AIOS should frame
  its novelty around local provider-CLI operation, contract artifacts, and
  reviewable cross-OS boundaries.
- SWE-agent and OpenHands are important software-agent systems. AIOS should
  position itself as an operating layer that can wrap software executors rather
  than a benchmark-winning software agent.
- Temporal and Cloudflare long-running agents show that durability, recovery,
  and stateful lifecycle are established systems concerns. AIOS adapts these
  concerns to agentic local work and evidence-bearing provider CLI workflows.

## Claim Boundary

The related-work section should use these sources to narrow AIOS's claim:

> AIOS is not the first multi-agent framework, not a new foundation model, and
> not a replacement for durable workflow platforms. It is a local-first,
> contract-bound operating layer that wraps provider CLIs and turns long-running
> agentic work into auditable contracts, receipts, memory traces, capability
> routes, and review loops.

## Next Evidence Need

Related work is now source-grounded, but evaluation claims still need matched
direct provider CLI versus AIOS-wrapped provider CLI runs.
