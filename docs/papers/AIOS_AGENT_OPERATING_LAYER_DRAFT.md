# AIOS: An Agent Operating Layer for Reliable Long-Running AI Work

Status: working manuscript draft — active under ASC-0098 (accepted 2026-05-18); prior refinement under ASC-0159/ASC-0160  
Date: 2026-05-14; revised 2026-05-18 (§4.3 active memory-graph control; claims C-023–C-025)  
Primary claim status: draft; claims must be tightened through the claim ledger
before public submission.

## Abstract

Provider command-line agents such as Claude CLI, Codex CLI, Gemini wrappers,
and local LLM runners are strong executors, but direct provider workflows are
fragile for long-running work. They often lose continuity across sessions,
hide tool and memory choices inside a chat transcript, fail silently under
provider backpressure, and leave weak audit trails for scope, verification, and
operator decisions. This paper introduces AIOS, a local-first, contract-bound
agent operating layer that wraps provider CLIs without replacing them. AIOS
turns one-shot provider execution into a persistent operating loop: goals are
converted into contracts, relevant memory is retrieved with provenance,
capabilities are routed explicitly, assumptions are challenged before closure,
provider execution is bounded by work packets, and results are collected as
receipts, ledgers, and memory drafts. The central claim is not that AIOS is a
smarter model than any provider. The claim is that provider CLIs wrapped by an
operating layer can improve continuity, reliability, governance,
recoverability, memory reuse, capability routing, and user visibility in
long-running agentic work. We further show that the operating layer can own
*algorithmic* properties a one-shot workflow cannot: an active memory-graph
control model runs during idle cycles and keeps the queryable surface of an
append-only knowledge graph bounded to O(communities) rather than O(nodes) as
the graph grows. We propose an evaluation comparing direct provider
CLI workflows against the same provider executed through AIOS, while also
measuring operational overhead introduced by contracts, artifacts, checkpoints,
and routing decisions. A first matched-run execution (N=3, §6.4) validates the
protocol and already separates the claim: the deterministic layer delivers a
measured continuity gain at bounded overhead, while the semantic-memory gain is
scaffolded but not yet realized — reported here as a null result, not hidden.

## 1. Introduction

Modern provider CLIs make high-quality AI execution available inside local
development workflows. A user can ask a model to inspect a repository, edit
files, run tests, and explain the result. For small tasks this is often enough.
For long-running projects, however, direct provider interaction has a different
failure profile. The problem is not that the model cannot write code or reason
about architecture. The problem is that the workflow around the model is
ephemeral.

Long-running AI work needs more than a strong executor. It needs continuity
when a session ends, recovery when a provider fails, explicit boundaries for
what can be touched, memory that can be reused without silently becoming
truth, tool routing that can be inspected, and evidence that later agents or
humans can audit. Without an operating layer, these responsibilities fall back
onto the user prompt, the chat transcript, or the provider's hidden internal
state.

AIOS addresses this gap by treating provider CLIs as substrates inside a
contract-bound operating loop. The system does not try to replace Claude,
Codex, Gemini, or local LLMs. Instead, it wraps them with a control plane,
memory layer, capability router, divergence layer, execution wrapper, and
durable artifact protocol.

The safest version of the thesis is:

> AIOS does not replace provider CLIs; it turns them from one-shot executors
> into a persistent, governed, inspectable, memory-bearing operating loop for
> long-running agentic work.

This framing changes the comparison. The relevant experiment is not "Claude
versus AIOS" or "Codex versus AIOS." The comparison is:

- Baseline: direct provider CLI workflow.
- System: the same provider CLI wrapped by the AIOS operating layer.

The provider should be held constant. The tested variable is whether the
operating layer improves the management of long-running work.

This paper makes four contributions.

First, it defines an agent operating layer: a local-first layer above provider
CLIs that manages contracts, memory retrieval, capability routing, divergence,
execution, verification, and learning as separate operating responsibilities.

Second, it describes a concrete implementation of this layer in AIOS, organized
around MyWorld, Hive Mind, MemoryOS, CapabilityOS, and GenesisOS. These are not
five competing agents. They are five operating roles that make direct provider
execution governable over time.

Third, it presents one concrete mechanism by which the operating layer keeps a
growing memory substrate usable: an active memory-graph control model that runs
during idle cycles and bounds the *queryable surface* of an append-only
knowledge graph to O(communities) rather than O(nodes). This shows that the
operating layer's value is not only procedural (contracts, receipts) but can be
algorithmic — the layer can own properties, such as bounded retrieval cost,
that a one-shot provider workflow cannot.

Fourth, it proposes an evaluation protocol for measuring operating-layer value
against direct provider CLI use. The protocol measures continuity, reliability,
governance, memory usefulness, capability routing, divergence, user visibility,
and overhead. This keeps the claim operational rather than anthropomorphic:
AIOS should be judged by whether it makes long-running work more recoverable
and inspectable, not by whether it appears more intelligent than the provider.

## 2. Problem Statement

Direct provider CLI workflows expose several recurring operational failures.

### 2.1 Continuity Failure

Work often spans multiple sessions, days, repositories, and providers. Direct
chat or CLI workflows rely on the current prompt and local context window. Once
the session ends, the next executor may not know which contracts were accepted,
which files were forbidden, which provider failed, or which result packet was
already collected.

### 2.2 Reliability And Recovery Failure

Providers can rate-limit, require interactive authentication, return empty
output, or fail with localized errors. A direct workflow can stall until the
user notices and reprompts. AIOS treats provider failure as a system event that
must be classified, recorded, and routed to a fallback or checkpoint.

### 2.3 Governance Failure

Provider CLIs can edit files, run commands, or infer authority from prompt
wording. Long-running work needs named scope, forbidden paths, checkpoint
rules, and stop conditions. AIOS expresses these as contracts and dispatch
packets rather than relying on conversational memory.

### 2.4 Memory Ambiguity

A provider can use context from a chat, but that context may be unreviewed,
unproven, stale, or private. AIOS separates memory retrieval from memory
acceptance. MemoryOS can provide context packs and draft memory candidates, but
accepted memory requires review.

### 2.5 Tool Routing Ambiguity

Direct provider workflows often choose tools opportunistically. AIOS assigns
CapabilityOS the role of recommending tools, providers, APIs, web research,
MCPs, and fallback routes as explicit artifacts.

### 2.6 Convergence And Prompt-Prison Risk

Long AI work can converge on the user's current phrasing or the provider's
habitual solution style. AIOS gives GenesisOS a divergence role: challenge
assumptions, mutate frames, align semantics, and surface alternative world
branches before closure.

### 2.7 User Visibility Failure

Users need to see what the system is doing without reading raw logs. AIOS
records contracts, work packets, receipts, ledgers, monitor state, visual
Control Center surfaces, and memory drafts so users can inspect progress,
blockers, artifacts, and next work. The Control Center additionally projects a
multi-agent surface: a roster of repo-agents, each with a one-line status
digest, an out-of-band channel that floats blocked or input-needing agents to
the top, and a contract-lifecycle board. This surface is a read projection of
existing state — contracts, dispatch packets, the ledger — not a second store,
so what the user sees cannot drift from what the system actually recorded.

## 3. System Model

AIOS is a stateful operating loop, not a fixed linear pipeline. A goal enters
the control plane and activates only the OS layers needed for the current
decision. A typical loop is:

```text
Goal
  -> MyWorld contract + dispatch
  -> MemoryOS retrieves context
  -> CapabilityOS recommends routes
  -> GenesisOS challenges assumptions
  -> Hive Mind executes/verifies through providers
  -> MyWorld collects, records, and advances the next loop
```

The order is not always rigid. Some tasks need MemoryOS before dispatch. Some
need CapabilityOS first because the central uncertainty is tool choice. Some
need GenesisOS before any implementation because the goal framing may be wrong.
The control plane decides which layer to call and records the decision as an
artifact.

At the infrastructure level, the direct provider CLI path is:

```text
User prompt -> Provider CLI -> Output
```

AIOS inserts an operating layer:

```text
User / Goal
  -> MyWorld Control Plane
       contract, dispatch, ledger, monitor, UI
  -> Hive Mind
       provider CLI wrapper, execution scheduler, fallback, verification
  -> MemoryOS
       user/project memory, ontology, hypergraph, retrieval trace, context pack
  -> CapabilityOS
       tool/API/MCP/web route, provider selection, capability gap detection
  -> GenesisOS
       divergence, semantic alignment, assumption challenge, world branches
  -> Evidence, ledger, memory writeback, and next loop
```

The important distinction is state. A provider CLI call produces an answer or
patch. AIOS produces a recoverable work state: what goal was accepted, what
memory was used, what route was recommended, what assumption was challenged,
what executor ran, what verification passed, what failed, and what should
happen next.

## 4. Architecture

AIOS is organized as five cooperating roles.

### 4.1 MyWorld: Sovereign Control Plane

MyWorld owns contracts, dispatch, monitor state, global ledger entries,
operator checkpoints, and release decisions. It is the root coordination layer.
It should not directly become a broad worker for child repositories. Its main
job is to convert goals into governed work packets, collect evidence, and move
the loop forward.

### 4.2 Hive Mind: Execution Wrapper

Hive Mind owns execution, scheduling, provider wrapping, proofs, and
verification. It treats provider CLIs and local LLMs as executor substrates. A
provider can be strong, unavailable, degraded, or replaced; Hive Mind provides
the operating surface that allows AIOS to reason about that provider behavior.

### 4.3 MemoryOS: Retriever And Memory Lifecycle

MemoryOS owns context packs, provenance, retrieval traces, memory drafts,
review queues, and accepted memory. Its core design rule is draft-first memory:
retrieved context can inform execution, but new memories are not silently
accepted.

Draft-first review is a passive guard: it keeps the graph from breaking, but it
does not bound the graph's growth. As the append-only knowledge graph grows —
currently ~198K nodes — an ungoverned graph degrades retrieval: noisy hubs,
duplicate proliferation, and stale facts inflate the queryable surface. AIOS
therefore treats graph growth as an actively governed process. A **memory-graph
control model** runs as a stage of the idle "dream" cycle in seven steps:
salience scoring, entity merge, bi-temporal invalidation (superseded facts are
invalidated, never deleted, preserving the append-only audit), episodic-to-
semantic consolidation, hierarchical community layering, access-based decay,
and a final bound check. The load-bearing property is that the *queryable
surface* becomes O(communities) rather than O(nodes): the graph may keep
growing while the cost of a query stays bounded. Each run emits a bound ratio
(reclamation over raw ingest) and halts on named failure modes — duplicate
proliferation, semantic drift, temporal obsolescence — rather than degrading
silently. This is the difference between a memory store that merely persists
and one that stays coherent as it scales.

### 4.4 CapabilityOS: Tool And Provider Router

CapabilityOS owns capability maps, route recommendations, fallback plans, and
tool/API/provider selection surfaces. In early AIOS, CapabilityOS recommends
but does not silently execute external tools. This keeps execution authority
inside contracts.

Routing a conversational turn is two-tier. A fast local-LLM pre-router
classifies the turn's intent before any expensive execution, and CapabilityOS's
recommendation matrix — ranked by cost and confidence — selects a substrate
from that classification rather than from substring heuristics. Because a cheap
route can still misjudge a non-trivial turn, the operating layer adds a
post-generation quality gate: a deterministic adequacy check followed, when it
passes, by an LLM-as-judge that scores the answer against a criterion rubric
and defaults to a fail verdict. On an inadequate verdict the turn is escalated
once to a stronger model. This is the two-tier RouteLLM pattern — a cheap
pre-router plus a post-hoc escalation path — placed inside the operating layer,
so a misroute is detected and recovered rather than silently shipped to the
user.

### 4.5 GenesisOS: Divergence And Semantic Alignment

GenesisOS owns divergence, assumption mutation, prompt-prison critique,
semantic alignment, and multiple candidate world branches. Its role is not to
choose final truth. Its role is to prevent the operating loop from collapsing
into a single habitual frame too early.

## 5. Artifact Protocol

AIOS turns agent work into durable artifacts:

- Contracts define goal, scope, allowed files, forbidden files,
  responsibilities, verification gates, and stop conditions.
- Dispatch packets translate contracts into repo-specific instructions.
- Result packets report execution status, evidence, and stop conditions.
- Ledgers record stable closeout decisions.
- Worklogs preserve cross-agent handoff details.
- Memory drafts capture reusable lessons without auto-acceptance.
- Capability routes and observations preserve tool/provider decisions.
- Genesis critiques preserve alternative frames and assumption challenges.
- Monitor snapshots summarize current health and next actions.

This artifact protocol is the operating layer's main mechanism. AIOS does not
depend on a provider remembering the whole project. It makes the project
rememberable through files and receipts.

## 6. Evaluation Design

The evaluation should compare direct provider CLI workflow against the same
provider CLI wrapped by AIOS. The provider must be held constant whenever
possible. Otherwise, improvements could be caused by a stronger model rather
than the operating layer.

The evaluation is organized around four research questions:

- RQ1 Continuity: Does AIOS improve restart and handoff behavior compared with
  direct provider CLI use?
- RQ2 Reliability: Does AIOS recover from provider failure, empty output,
  access denial, or blocked execution more often than direct use?
- RQ3 Governance and visibility: Does AIOS reduce unverified closure, scope
  ambiguity, and invisible state?
- RQ4 Cost: What operational overhead does AIOS add, and when is that overhead
  justified?

### 6.1 Conditions

Baseline:

- Same repository snapshot.
- Same task prompt.
- Same provider CLI.
- No AIOS contracts, dispatch packets, memory retrieval, route artifacts, or
  monitor-driven recovery.

System:

- Same repository snapshot.
- Same task prompt transformed into an AIOS contract or governed goal.
- Same provider CLI used as executor.
- AIOS contract, memory, capability, Genesis, Hive, monitor, and ledger
  surfaces active as required.

### 6.2 Task Set

The task set should include:

- Single-repo bug fix.
- Multi-file feature implementation.
- Multi-repo coordination.
- Provider failure or empty-output recovery.
- Long-running refactor across sessions.
- External tool/API research and integration.
- Work that depends on prior decisions or accepted memory.

### 6.3 Metrics

Core operational metrics:

| Metric | Direct CLI | AIOS |
| --- | --- | --- |
| completion_rate | TBD | TBD |
| verification_pass_rate | TBD | TBD |
| restart_resume_success | TBD | TBD |
| human_reprompt_count | TBD | TBD |
| provider_failure_recovery | TBD | TBD |
| scope_violation_count | TBD | TBD |
| artifact_trace_completeness | TBD | TBD |
| memory_reuse_count | TBD | TBD |
| tool_route_accuracy | TBD | TBD |
| user_visibility_score | TBD | TBD |

Overhead metrics:

| Metric | Direct CLI | AIOS |
| --- | --- | --- |
| extra_time_per_task | TBD | TBD |
| generated_artifact_count | TBD | TBD |
| false_checkpoint_count | TBD | TBD |
| false_escalation_count | TBD | TBD |
| user_cognitive_load | TBD | TBD |
| contract_authoring_cost | TBD | TBD |

The overhead section is essential. AIOS adds contracts, result packets,
monitors, and ledgers. These can make work slower, heavier, and more verbose.
The system is only valuable if reliability and continuity gains justify that
operational cost.

The benchmark must also preserve negative evidence. Failures, bad routes,
unhelpful memories, false checkpoints, and misleading tool recommendations are
not cleanup noise. They are training signal for the operating layer. A system
that stores only successful examples cannot learn when not to reuse a memory,
when not to select a tool, or when a provider habit is steering the work toward
a plausible but wrong pattern.

The expected result is not that AIOS wins every task. For short, isolated
edits, direct provider CLI use may be faster and sufficient. AIOS should show
its value on tasks where continuity, recovery, governance, memory, routing, or
multi-step evidence matter. A negative result on simple tasks is not a failure
of the thesis; it identifies the boundary where an operating layer is not worth
its overhead.

Negative evidence becomes useful when it is recombined, not merely archived.
GenesisOS should therefore be evaluated as a combinatorial creativity layer:
it can combine a failure memory, a bad tool observation, a founder pattern, a
distant domain analogy, and a current goal into a new candidate worldline. This
models the human creative move of feeling discomfort, naming a need, and
borrowing a pattern from elsewhere. The V1 evidence contract for this is
`docs/AIOS_NEGATIVE_EVIDENCE_AND_COMBINATORIAL_CREATIVITY.md`.

### 6.4 Executed First Matched-Run Results (N=3)

The protocol above was executed on a first synthetic fixture (ASC-0182, repo
snapshot `b1fdb2a`). This is a **protocol-validation run, not a superiority
claim**: N=3, one task per discriminating family. Full tables and artifacts:
`docs/papers/AIOS_BENCHMARK_RESULTS.md`, `benchmark/`.

The same provider (claude-opus-4-7) ran each task twice on an identical
snapshot; only the operating layer was manipulated. Results:

| Task | Family | Direct CLI | AIOS | Verdict |
| --- | --- | --- | --- | --- |
| A | single-repo bug fix | 4/4 pass | 4/4 pass, +3 artifacts | AIOS = pure overhead |
| B | restart/resume across a session boundary | resume partial, 1 reprompt | resume success, 0 reprompt | AIOS gain (real) |
| C | prior-decision-dependent work | fail (no recall) | fail → **success after embedding** | AIOS gain realized once embeddings close |

Three findings, reported including the unfavorable ones:

1. **On clean isolated work, AIOS is pure overhead.** Tasks A's fix was
   byte-identical in both conditions (confirming the model was held constant);
   AIOS added three governance artifacts and contract-authoring time for zero
   outcome gain. This locates the boundary the thesis predicts: an operating
   layer is not worth its cost on short, isolated edits.

2. **On continuity across a session boundary, AIOS delivers a measured gain.**
   Task B's fixture embedded a design decision the *code did not encode*. The
   baseline resumer could re-derive the code but had to guess the intent; the
   AIOS resumer read the decision from the contract and certified consistency
   (0 reprompts vs 1). The gain came from the deterministic layer — contract
   and ledger — which is built and works.

3. **On memory-dependent work, AIOS's gain is real once the embedding gap is
   closed.** At first run, `memoryos context build` returned 0 items and
   `search` 0 hits for a memory-relevant query, because embedding coverage was
   0.0% (0 of 44 objects) — reported as a null result. After the embedding job
   completed (coverage 0.0% → 100.0%, 44/44 objects, 197,345 nodes), Task C was
   re-run: the same query class returned 10 ranked decision records. The null
   result flipped to success. The earned claim is "the memory layer
   retrieves"; retrieval *ranking quality* remains untested.

The N=3 result separates AIOS's value along a clear fault line: its
deterministic layer (contracts, dispatch, ledger) delivers verifiable
continuity at a bounded artifact-overhead cost, while its cognition-closing
layer (semantic memory) is scaffolded but unrun and so does not yet deliver
its headline gain. No broad utility claim is made until families 2, 3, 4, and
6 are also executed.

## 7. Dogfood Observations From Writing This Draft

Writing this paper through AIOS immediately surfaced useful friction.

### 7.1 Release Authority Was Audited But Not Binding

During ASC-0157 closeout, AIOS recorded that `codex` lacked operator
citizenship for `release_dispatch`, but the release still returned `ok=true`
and wrote a MemoryOS closeout draft. This contradicted the governance claim.
AIOS then opened ASC-0158 and changed dispatch release so hard authority denial
blocks release and memory writeback unless `--override-authority` is explicitly
provided.

This is a strong example of the paper thesis. Direct provider execution could
have silently moved on. The AIOS operating loop turned the inconsistency into a
contract, test, receipt, and memory draft.

### 7.2 Monitor Alerts Create Both Safety And Overhead

The monitor flagged pending result packets for active contracts. This prevented
silent closeout, but it also required extra collect/watch/release steps. This
is useful safety friction, but it contributes to operational overhead.

### 7.3 Generated Artifacts Improve Continuity But Increase Surface Area

ASC-0157 added AIOS role evidence slots to generated contract seeds. This
makes future work less likely to bypass MemoryOS, CapabilityOS, GenesisOS, or
Hive Mind. It also means each contract carries more structure. The evaluation
must measure whether that structure improves outcomes enough to justify the
additional artifact load.

### 7.4 Refinement Loop Produced Role Evidence

ASC-0160 ran a plan-only AIOS invocation for this paper refinement. The
invocation produced MemoryOS, CapabilityOS, GenesisOS, and Hive artifacts under
`.aios/invocations/asc-0160-paper-refinement/`.

MemoryOS returned a context pack with retrieval trace
`rtrace_7124ea1c1fee8eff` and ten selected memory ids. This supports a more
precise evaluation question: does retrieved, provenance-bearing context improve
restart/resume quality or reduce repeated prompting?

CapabilityOS recommended local, recommendation-only routes such as
`cap_memoryos_context_build`, `cap_hivemind_execution_harness`, and
`cap_capabilityos_recommendation`. This reinforces that tool-route accuracy
should be evaluated as route-to-artifact fit, not merely task success.

GenesisOS surfaced the branch `failure_as_feature`: the system should treat
friction as evidence rather than hide it. This strengthens the overhead
section. The same mechanisms that improve recoverability can create extra
steps, checkpoint friction, and artifact load.

ASC-0163 repeated this paper-building loop for negative evidence and
combinatorial creativity. The plan-only invocation produced MemoryOS trace
`rtrace_0fa028fc49623cad`, CapabilityOS recommendation-only route artifacts,
and GenesisOS branches including `alien_domain`, `failure_as_feature`, and
`anti_user_prompt`. This reinforced a sharper future-work claim: GenesisOS is
not valuable only when it criticizes a draft. It is valuable when it turns
failure, bad tools, and semantic discomfort into testable candidate contracts.

Hive remained plan-only and preserved the boundary between paper drafting and
empirical claims. This keeps the current manuscript as a system paper draft
until matched-run experiments exist.

## 8. Threats To Validity

Provider variation is the largest threat. If AIOS uses one provider and the
baseline uses another, the experiment measures model differences instead of
operating-layer effects. The evaluation should therefore keep the executor
constant.

Task selection is another threat. AIOS is expected to help most on long,
multi-step, failure-prone tasks. It may be unnecessary overhead for a
single-file typo fix.

Implementation maturity is also a threat. AIOS is still a living system under
development. Some claimed surfaces are implemented, some are proposed, and some
are only partially verified. The claim ledger must separate evidence-bound
claims from hypotheses.

Finally, local-first artifacts can improve privacy boundaries but do not
guarantee privacy by themselves. Provider prompts, external tools, and user
configuration remain deployment-level risks.

The dogfood setting is also a threat. AIOS is being built with AIOS, which
creates both useful evidence and confirmation risk. The paper should treat
dogfood observations as system-building evidence, not as a substitute for
matched comparisons. The claim ledger and reviewer-attack loop exist to force
this separation.

## 9. Limitations

AIOS is heavier than direct provider CLI use. It can create many files, require
contract authoring, produce false holds, and slow down simple tasks. Its
benefits should be expected when task duration, risk, or coordination cost is
high enough to justify the operating layer.

AIOS is not a fully autonomous AI institution. It currently supports persistent
loops, contracts, monitor state, memory drafts, capability routing, and
provider wrapping, but operator authority and review boundaries remain central.
Autonomy claims must be stated conservatively.

AIOS also depends on providers. It can route around failure and record
backpressure, but it does not eliminate provider limits, authentication
requirements, or model quality constraints.

## 10. Related Work Positioning

AIOS sits near several existing bodies of work. The source receipt for this
section is `docs/papers/AIOS_RELATED_WORK_SOURCE_RECEIPT.md`.

AutoGen frames multi-agent LLM applications around customizable conversable
agents that can combine LLMs, human inputs, and tools. AIOS should therefore
not claim to invent multi-agent orchestration. Its narrower contribution is a
local operating discipline around provider CLIs: contracts, work packets,
receipts, memory review, capability routes, and closeout ledgers.

LangGraph and CrewAI both make state and control explicit in agent workflows.
LangGraph emphasizes long-running, stateful agent orchestration with durable
execution and human-in-the-loop support. CrewAI distinguishes structured Flows
from autonomous Crews. AIOS overlaps with these concerns, but its boundary is
different: it treats provider CLIs as replaceable executor substrates and
records the operating loop through local files.

SWE-agent and OpenHands are adjacent software-agent systems. They focus on
agent-computer interfaces, sandboxed software work, command-line interaction,
web browsing, coordination, and benchmark performance. AIOS should be compared
against such systems only when the task is software engineering; otherwise its
main comparison remains direct provider CLI workflow versus the same provider
wrapped by AIOS.

Temporal and Cloudflare long-running-agent documentation show that durable
execution, restart recovery, persistent state, wake/sleep lifecycle, and
explicit workflow boundaries are established systems problems. AIOS adapts
these ideas to local-first agent work with a lightweight artifact protocol
rather than a distributed workflow runtime.

OpenAI Swarm is a useful boundary case. Its README describes a lightweight,
controllable, educational multi-agent orchestration framework and notes that it
is stateless between calls. AIOS makes the opposite design choice for its
target problem: state, contracts, receipts, and memory review are the operating
layer.

The related-work claim boundary is therefore conservative: AIOS is not the
first multi-agent framework, not a new foundation model, and not a replacement
for durable workflow platforms. It is a contract-bound operating layer around
provider CLIs for persistent, inspectable, memory-bearing work.

## 11. Future Work

The next paper-building loop should:

1. Build a small benchmark suite with matched direct CLI and AIOS-wrapped
   runs.
2. Define artifact trace completeness scoring.
3. Measure operational overhead with actual time and artifact counts.
4. Add user-facing visibility measures from the Control Center.
5. Run reviewer-style attack passes against unsupported claims.
6. Turn MemoryOS retrieval and CapabilityOS routing usefulness into measurable
   task-level outcomes.
7. Add negative evidence handling so MemoryOS remembers failed patterns and
   CapabilityOS learns to distinguish harmful or low-value tools from useful
   routes.
8. Add GenesisOS recombination candidates that combine negative evidence,
   founder patterns, distant-domain analogies, and current goals into
   verifiable contract seeds.

### 11.1 Evidence-Tightening Loop

Before submission, each paper revision should run this loop:

```text
draft claim
  -> MemoryOS context and accepted-memory provenance
  -> CapabilityOS route and related-work/source plan
  -> GenesisOS reviewer attack and assumption mutation
  -> Hive verification plan
  -> claim ledger update
  -> paper edit or claim downgrade
```

The loop has a named exit: every claim becomes `evidence_bound`,
`evidence_needed`, `hypothesis`, or `blocked`. No claim should be promoted
because it sounds plausible in the manuscript.

## 12. Conclusion

AIOS is best understood as an agent operating layer, not a replacement model.
Its role is to make provider CLI work persistent, governed, inspectable,
recoverable, and memory-bearing. The core research question is whether this
operating layer improves long-running AI work compared with direct provider CLI
use, and whether those gains justify the overhead of contracts, artifacts,
checkpoints, and routing. This framing is more defensible than claiming AIOS is
more intelligent than its underlying providers, and it gives the system a clear
evaluation path.

The first executed matched-run (§6.4) supports this framing empirically at
small scale. On clean isolated work AIOS is pure overhead; across a session
boundary it delivers a verifiable continuity gain through its deterministic
contract/ledger layer; on memory-dependent work its advantage is currently
unrealized because semantic retrieval is not yet closed. The honest verdict
from N=3 is therefore conditional: AIOS today buys verifiable continuity and
governance at an artifact-overhead cost, and its memory advantage remains a
hypothesis pending the embedding gap being closed. That is a narrower claim
than "AIOS is useful across diverse tasks" — and it is the claim the evidence
currently supports.

A separate and stronger result stands on its own. Independent of whether
semantic retrieval *usefulness* is yet realized, the operating layer
demonstrably owns an *algorithmic* property the bare provider workflow cannot:
the active memory-graph control model bounds the queryable surface of an
append-only knowledge graph to O(communities) as the graph grows (§4.3). This
distinguishes two kinds of operating-layer value — procedural governance
(contracts, receipts, continuity) and algorithmic governance (bounded memory
cost) — and shows the second is achievable today even while the first kind's
memory-retrieval payoff remains under evaluation.
