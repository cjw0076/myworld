# Study: Observer vs Executor Framing for AIOS

- date: 2026-05-15 KST
- operator: claude@myworld
- capability route: `cap_web_research_route` (CapabilityOS recommend)
- execution tool: WebSearch (sub-agent dispatched)
- substrate compliance: this study uses CapabilityOS → execute → MemoryOS import flow, per founder directive "공부는 capability + memoryos 통해 web 전체와 소통"
- triggering question: should AIOS try to OWN execution of product repos (current ASC-0128..0142 + 0166..0171 chain framing) or BECOME the management plane that observes/absorbs/recommends without owning execution (ASC-0172 draft framing)?

## Method

1. CapabilityOS recommend for the study task returned `cap_web_research_route`
   with risk=medium, privacy=remote, requires_network=true. The route is
   recommendation-only: returns `search_plan, source_policy, evidence_requirements,
   risk_notes`. It does not browse directly.
2. WebSearch executed the plan (via sub-agent abcd8668d364464fe).
3. Citations recorded below for MemoryOS provenance chain (DNA Invariant 5).
4. This file is the draft memory candidate. Acceptance requires explicit review
   (DNA Invariant 2 — no auto-accept).

## Question 1 — Agent orchestration frameworks (LangGraph, AutoGen, CrewAI, MetaGPT)

**Finding**: All four position themselves as execution owners, not observers. 2025-2026 convergence is graph-based orchestration. **High lock-in per framework, narrow adoption**. None can retroactively capture a 187-sprint existing codebase without rewrite.

**AIOS implication**: AIOS's current "I'll take over uri execution" framing is the LangGraph/AutoGen pattern. Evidence: those frameworks only won greenfield projects. uri has 187 shipped sprints — equivalent to a brownfield enterprise codebase.

**Source**: [LangGraph vs CrewAI vs AutoGen architecture analysis 2025](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025)

## Question 2 — Observability platforms (LangSmith, Langfuse, Arize Phoenix, Helicone, Datadog LLM)

**Finding**: Fastest-growing category in agent infra. Explicitly do NOT own execution. Helicone's wedge: "drop-in proxy, no SDK change." LangSmith integrates with LangChain but observes. OpenTelemetry GenAI semantic conventions **went stable early 2026** — the industry standardized on observation, not orchestration.

**AIOS implication**: The market validated observer-first as the winning entry strategy for agent infrastructure. AIOS proposing 14 permission-expansion contracts to claim execution authority is fighting against a settled industry direction.

**Sources**:
- [OpenTelemetry AI Agent Observability (2025)](https://opentelemetry.io/blog/2025/ai-agent-observability/)
- [9 AI Observability Platforms Compared (2025)](https://softcery.com/lab/top-8-observability-platforms-for-ai-agents-in-2025)

## Question 3 — MLOps platforms (W&B, MLflow, Comet)

**Finding**: W&B reached unicorn valuation as a pure logger. `wandb.log()` is one line dropped into the user's training loop. Never tried to own the training loop. The strategic lesson is canonical in MLOps practice: trackers that demanded code restructuring lost; trackers that observed what was already written won.

**AIOS implication**: MemoryOS bulk-ingest of uri's 187 commits as drafts (ASC-0172 Packet A) follows the W&B pattern. But adversarial critic raised a valid concern: bulk-ingest without uri consent risks Invariant 6 (operator override) violation. Resolution: ingestion should be uri-emitted, not myworld-pulled (uri sends recap packets; AIOS absorbs them).

**Source**: [MLflow vs W&B vs ZenML (ZenML)](https://www.zenml.io/blog/mlflow-vs-weights-and-biases)

## Question 4 — Architecture vocabulary for the reframe

**Finding**: There is established vocabulary.

- **Control plane vs data plane** (Envoy/Istio): control plane scales with configuration complexity, data plane with traffic volume. AIOS currently tries to be both.
- **Sidecar pattern**: observability injected next to the workload, not in front of it.
- **Three-plane model** (HashiCorp): control / data / **management plane**. Management plane = audit, policy recommendation, provenance. This is precisely the ASC-0172 reframe target.
- **Microkernel + external servers** (Plan 9): mechanism in kernel, policy in external servers. Maps to "AIOS holds invariants; product repos hold execution."

**AIOS implication**: The reframe target has a name — management plane. The ASC-0124 Hive verdict's phrase "semantic authority" aligns with this. AIOS already converged on this language in ASC-0124; the in-flight chain (ASC-0128..0171) did not update after.

**Sources**:
- [Service mesh data plane vs control plane (Matt Klein, Envoy)](https://blog.envoyproxy.io/service-mesh-data-plane-vs-control-plane-2774e720f7fc)
- [HashiCorp: Design control, management, and data planes](https://developer.hashicorp.com/well-architected-framework/design-resilient-systems/design-control-data-management-plane)
- [Plan 9 architectural overview](https://ondoc.logand.com/d/5736/pdf)

## Question 5 — Audit-first → control-plane phasing

**Finding**: Enterprise AI governance literature (Google Cloud, Microsoft Copilot, CIO 2026) advocates a phased model: "**start audit-based** to observe behavior and identify patterns, **then gradually introduce stricter controls**." Pure-audit (Datadog model) builds moats via integration breadth and switching cost, not execution ownership.

**AIOS implication**: AIOS does not have to choose "observer forever" vs "executor now." Audit-first → control-plane is the documented enterprise path. ASC-0172 framing can be re-stated as: **enter the audit/observer phase first, defer control-plane authority until uri adoption is voluntary**.

**Sources**:
- [From copilot to control plane: AI governance (CIO, 2026)](https://www.cio.com/article/4165609/from-copilot-to-control-plane-where-serious-ai-governance-starts.html)
- [Google Cloud Recommended AI Controls framework](https://cloud.google.com/blog/products/identity-security/audit-smarter-introducing-our-recommended-ai-controls-framework)

## Counter-evidence from adversarial critic (logged for review)

The independent critic agent argued strongly against ASC-0172 as drafted:

1. **Executor prevents, observer detects**: pure-observer cannot enforce DNA invariants pre-fact. Privacy leaks (Invariant 7) and irreversible actions (Invariant 8) become forensic, not preventable.
2. **ASC-0124 verdict was hybrid, not observer-only**: Probe 9 explicitly proposed protocol-only/thin-coordination and DID NOT win in the debate. ASC-0172 reasserts probe 9 single-head.
3. **Bulk-ingestion violates Invariant 6**: uri did not consent to AIOS observing its 187 sprints. Ingestion must be uri-emitted (push), not myworld-pulled.
4. **Six of the 14 "permission expansion" contracts are CLOSED with shipped harness code (ASC-0166..0171)**: calling them prompt prison erases real codex chain work. The proper fix is closeout reconciliation (ASC-0076 pattern), not blanket supersession.
5. **Drafting ASC-0172 single-head 24 hours after ASC-0124 closed is the exact failure mode ASC-0084 DNA Invariant "decide before acting" is designed to prevent**.

## Synthesis

Both the prior-art research and the adversarial critic converge on the **split recommendation**:

1. **Additive ingestion contract** (NOT supersession): uri can emit recap packets; AIOS absorbs as MemoryOS drafts with provenance. CapabilityOS observes uri's stack via uri-emitted capability declarations. No bulk pull without consent.
2. **Reframe debate** (Hive, not single-head): the deeper observer-vs-executor question should re-enter Hive deliberation under ASC-0084 format. Probe 9 was raised but not the only frame; new evidence (OpenTelemetry stable, audit-first enterprise canonical) was not available during ASC-0124.

**Do not accept ASC-0172 as written.**

The single-head intuition that triggered ASC-0172 was directionally right but the contract shape was too sweeping and violated process invariants. The correct response respects the DNA: a small additive contract that delivers value now, plus a Hive debate that re-tests the framing with new evidence.

## Drafts for MemoryOS (review pending)

Each finding below should become a separate MemoryOS draft record on import:

- `mem_draft_observability_winning_pattern`: industry consensus 2026 is observer-first for agent infra; OpenTelemetry GenAI conventions stable; relevant when AIOS framing decisions touch execution authority.
- `mem_draft_management_plane_vocabulary`: HashiCorp 3-plane model gives canonical vocabulary for AIOS reframe; "management plane" = audit + recommendation + provenance.
- `mem_draft_audit_first_phasing`: enterprise AI governance canonically phases audit → control-plane; AIOS does not need to choose observer-forever vs executor-now.
- `mem_draft_critic_pre_fact_enforcement`: pure observers cannot enforce DNA invariants pre-fact; counter-argument to observer-only framing; must be addressed before any execution-authority demotion.
- `mem_draft_bulk_ingest_consent_violation`: ingesting product-repo work without explicit emission violates Invariant 6; ingestion must be repo-emitted.
- `mem_draft_chain_did_not_update_after_verdict`: codex chain continued generating permission contracts (ASC-0166..0171) after ASC-0124 verdict was rendered; chain reconciliation gap detected.

## Provenance / acceptance pending

This study is a draft. Acceptance requires:

- Operator review.
- Optionally, GenesisOS critic pass to detect prompt-prison in the synthesis itself.
- Optionally, founder direction on whether to immediately propose split contracts (ASC-0173 additive + ASC-0174 Hive debate) or whether the synthesis itself should also be Hive-reviewed.
