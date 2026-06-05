# AIOS Substrate Boundary

AIOS should own the smallest kernel that makes autonomous work governable. It
should not absorb every useful tool, model, workflow engine, or knowledge
source into the kernel.

This boundary answers the recurring operator question:

```text
Should AIOS touch process/OS-level substrate, expose an agent-friendly plugin,
or retrieve broader knowledge?
```

## Boundary Decision

Use this order. The first matching layer owns the work.

| Layer | Use When | Owner | Output |
| --- | --- | --- | --- |
| Kernel primitive | A capability needs authority enforcement, scope checks, receipts, rollback, lifecycle state, or stop semantics before any model/tool acts. | `myworld` contract plus Hive kernel surface | syscall, receipt schema, policy gate, rollback or stop condition |
| Execution substrate | A provider, local model, process, watcher, CLI, or long-running worker must run bounded work. | `hivemind` | provider-loop receipt, run receipt, verification result |
| Capability/plugin route | A model, MCP server, plugin, API, skill, package, web route, or local tool might help, but should not execute without a contract. | `CapabilityOS` | recommendation, capability card, fallback plan, risk notes |
| Memory/knowledge route | Prior decisions, private context, external research, web evidence, or reviewed facts are needed to decide well. | `memoryOS` plus cited evidence receipts | context pack, retrieval trace, memory draft, source evidence |
| Genesis challenge | The frame, assumptions, language, or final-state definition is unstable. | `GenesisOS` | branch set, assumption mutations, semantic alignment notes |

If more than one layer applies, create a praxis envelope or smart contract that
names each role. Do not silently collapse the layers into one broad worker.

## Kernel Owns Less Than It Can

The kernel should own only:

- authority checks and action policy
- filesystem/process/network scope declarations
- dispatch, release, hold, retry, escalation, and stop states
- syscall-like write/read/execute receipts
- rollback or degradation records
- provider/tool lifecycle probes when they affect routing safety
- privacy gates for raw exports, auth stores, and private history

The kernel should not own:

- model-specific reasoning strategy
- full workflow expression with branches, loops, and business logic
- plugin implementation details
- tool-specific credentials
- accepted memory policy
- final truth selection without verification evidence

This keeps AIOS closer to a governed operating layer than a workflow engine.
Workflow systems, MCP hosts, provider CLIs, local LLMs, and external APIs can
run above or behind the kernel as routed substrates.

## Plugin-Friendly Default

Default new capability shape:

```text
discover -> recommend -> contract -> execute through Hive -> verify -> record
```

Do not start with:

```text
install/bind/execute because the tool looks useful
```

Plugin-friendly means:

- CapabilityOS can discover and score the route.
- The route has a capability id, allowed operations, risks, and fallback.
- Execution remains separate until a contract grants authority.
- Results return as bounded receipts, not raw logs or private transcripts.
- MemoryOS receives draft candidates only when the result should become
  durable knowledge.

## External Knowledge Default

Use broad external knowledge when the task depends on current public facts,
ecosystem behavior, research, standards, APIs, prices, model/provider behavior,
security posture, or cross-domain analogies.

External knowledge must enter through one of:

- cited web evidence receipt
- repository or paper research note
- CapabilityOS route observation
- MemoryOS draft with provenance
- GenesisOS branch/challenge note

Do not let external research directly mutate implementation state. Research
changes the contract, route, or hypothesis first; execution follows only after
scope and verification gates are visible.

## OS-Level Escalation Test

Escalate to process/OS-level substrate only if all are true:

1. Agent/plugin/tool-level execution cannot provide the needed guarantee.
2. The missing guarantee is about authority, lifecycle, isolation, persistence,
   receipt integrity, rollback, or privacy.
3. The new primitive can be tested without a specific provider being healthy.
4. The primitive reduces future special-case glue rather than adding another
   bespoke workflow.
5. Stop conditions are explicit before implementation begins.

If any item fails, keep the work at the plugin, capability, memory, or Genesis
layer.

## Practical Examples

| Question | Boundary Answer |
| --- | --- |
| "Can Claude/Gemini/local LLM give a better idea?" | CapabilityOS route plus GenesisOS branch; Hive may execute a bounded provider call; MemoryOS records only reviewed summaries. |
| "Should AIOS daemonize background cognition?" | Hive execution substrate first. Kernel only owns lifecycle receipt and stop semantics. |
| "Should a new MCP server be installed?" | CapabilityOS recommendation first; contract grants execution if needed; kernel never installs on discovery alone. |
| "Should web research change code?" | Web receipt or research note first, then contract or patch with verification. |
| "Should AIOS manage process groups?" | Kernel primitive only if needed for durable monitor/stop/receipt behavior. |
| "Should local LLM output be final?" | No. Local LLM may draft, summarize, classify, or challenge; final acceptance requires a verifier. |

## External Design Evidence

- MCP separates data-layer primitives (`tools`, `resources`, `prompts`) from
  transport/lifecycle concerns, which supports AIOS's split between capability
  routes and execution substrate.
- OpenAI Agents SDK guardrails distinguish agent-level and tool-level
  boundaries; side-effectful tool calls need guardrails at the tool boundary,
  not only at the final agent output.
- OpenAI Agents SDK tracing treats LLM generations, tool calls, handoffs,
  guardrails, and custom events as spans, matching AIOS's need for receipts and
  provenance instead of raw provider trust.

Sources:

- https://modelcontextprotocol.io/docs/learn/architecture
- https://openai.github.io/openai-agents-python/guardrails/
- https://github.com/openai/openai-agents-python/blob/main/docs/tracing.md

## Stop Conditions

- `kernel_scope_creep`: AIOS kernel absorbs workflow/business logic that can
  live above the kernel.
- `plugin_executes_without_contract`: a plugin, MCP server, API, or package
  executes because it was discovered, not because authority was granted.
- `capabilityos_executes_tool`: CapabilityOS crosses from recommendation into
  execution.
- `memory_auto_accepts_research`: external or provider-derived facts become
  accepted memory without review.
- `provider_truth_without_verifier`: a provider/local model output is treated
  as final without verification evidence.
- `raw_private_evidence_leak`: raw private data, provider logs, credentials, or
  private history enter shared docs or dispatch packets.
