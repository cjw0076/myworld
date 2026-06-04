# AIOS Smart Contracts

This directory holds AIOS smart contracts — the machine-checkable work agreements that bind Hive Mind, MemoryOS, CapabilityOS, and the operator on a specific goal.

Read these first:

- `../AIOS_SMART_CONTRACT.md` — minimal contract shape and invariants
- `../AIOS_AGENT_PROTOCOL.md` — durable record format
- `../WORKSTREAMS.md` — Codex/Claude lead split and default task flow

## Naming

`ASC-NNNN-<short-slug>.md` — sequential, append-only. Once an ID is assigned, never re-use it. Superseded contracts get a new ID and a `supersedes:` field.

## Contract File Shape

Each contract file should contain at minimum:

1. **Frontmatter / header** — `contract_id`, `status` (proposed | accepted | active | closed | superseded), `goal`, `created`, `accepted` (when operator approves), `closed` (when verification gate passes or contract is cancelled).
2. **Scope** — `repos[]`, `allowed_files[]`, `forbidden_files[]`. Be specific; broad globs are a smell.
3. **Per-OS responsibility** — what `hive_mind`, `memoryos`, `capabilityos`, and `operator` each must produce. Use the `must_produce` lists from `AIOS_SMART_CONTRACT.md`.
4. **Verification gate** — concrete check that decides done vs. not done (test name, CLI command, artifact existence). No verification gate = no contract.
5. **Stop conditions** — explicit triggers that pause for operator checkpoint. Default set in `AIOS_SMART_CONTRACT.md` invariants.
6. **Receipts** — once executed, link to receipts/traces/observations in each OS, not paste them.
7. **Work Packets** — every dispatch issued under this contract. See section below.

Generated contract seeds should also include `## AIOS Role Evidence` with
MemoryOS, CapabilityOS, GenesisOS, and Hive Mind placeholders. Proposals may
leave those fields as `pending_or_not_required`; accepted contracts should
either fill them or explicitly say why that OS has no role.

For AIOS self-development contracts, add a compact 5-persona note under the
same section:

```md
### 5-Persona Use
- Hive / Wrapper: provider route, fallback, or single-provider justification
- MemoryOS / Retriever: `rtrace_...`, selected memory ids, `signal_coverage`
- CapabilityOS / Router: recommendation, selected route, fallback/deviation
- GenesisOS / Philosophy: critic branch, alternative, or escape vector
- MyWorld / Sovereign: founder/operator authority and override path
```

If one persona has no role, say why. Missing-by-silence becomes an advisory
gap in `scripts/aios_persona_audit.py`; a justified absence remains reviewable
without rewriting history.

## Work Packets

A work packet is a single, durable dispatch from the control plane to one specific agent (e.g. `codex@hivemind`, `codex@memoryOS`, `claude@myworld` for review). Every dispatch lives as an entry in the `## Work Packets` section of the contract that authorized it — never in chat alone.

Packet ID convention: `WP-<contract_number>-<letter>` (e.g. `WP-0001-A`, `WP-0001-B`). Letters are append-only within a contract; do not re-use.

Packet entry shape:

```md
### WP-NNNN-X — <one-line title>

- target_agent: <codex|claude|local-llm|operator>
- target_repo: <hivemind|memoryOS|CapabilityOS|myworld>
- status: issued | accepted | done | rejected | superseded
- issued: <YYYY-MM-DD>
- accepted: <YYYY-MM-DD or pending>
- closed: <YYYY-MM-DD or pending>
- depends_on: <other WP id, or none>
- brief: |
    <self-contained instruction. Assume target agent has not seen any chat
    context. Cite file paths for required reading. State what artifact the
    agent must produce and where.>
- result: <link to artifact / receipt / trace once closed>
```

Status transitions:
- `issued` → `accepted`: target agent acknowledges and begins.
- `accepted` → `done`: target agent posts the result link.
- `issued` or `accepted` → `rejected`: target agent declines with reason in `result`.
- any → `superseded`: a new packet replaces this one; new packet's `depends_on` field cites this packet's id.

Packets are append-only. Edits limited to status/accepted/closed/result fields. Brief content does not change after `issued`.

## Lifecycle

```
proposed   -> Claude or Codex drafts, posts for review
accepted   -> operator (재원) approves; status flips
active     -> Codex begins implementation under contract scope
closed     -> verification gate passes; receipts linked; ledger entry appended
superseded -> a newer contract replaces; this one becomes read-only reference
```

A `closed` contract gets a final entry in `../AIOS_AGENT_LEDGER.md` linking to its receipts.

## Operator Acceptance

Default acceptance is a frontmatter status flip in the contract file:

1. Operator approves the proposed contract.
2. Contract `status` changes from `proposed` to `accepted`.
3. `accepted` is filled with the approval timestamp.
4. The accepted snapshot is committed in git.

Do not write proposal-time ledger entries. Write one ledger entry only when the
accepted snapshot or closeout is ready, so the ledger records a stable contract
decision rather than draft churn.

## DNA Citation Requirement

New contracts that cross from `myworld` into a child repo, or that introduce
authority, execution, dispatch, provider, capability, privacy, credential, or
external-action behavior, must cite at least one relevant AIOS DNA invariant
from `../AIOS_DNA.md`.

The citation can use `Invariant N` or `DNA Invariant N`. Existing contracts are
not retroactively blocked; they are surfaced as a baseline by:

```bash
python scripts/aios_dna_lint.py docs/contracts/ASC-0091-memoryos-auto-writeback.md --json
```

Missing citations are governance evidence, not automatic failure, unless a
new contract explicitly makes the DNA lint a blocking verification gate.

## Governance Audit

Contract governance quality is measured by:

```bash
python scripts/aios_governance_audit.py --write docs/AIOS_GOVERNANCE_AUDIT.md --json
```

The generated report at `../AIOS_GOVERNANCE_AUDIT.md` records the current
baseline, lowest-scoring contracts, and whether the recent contract stream is
in a `governance_theater` state.

## Index

| ID | Slug | Status | Goal |
| --- | --- | --- | --- |
| ASC-0001 | memoryos-hivemind-loop | closed | Codify the existing MemoryOS <-> Hive Mind memory loop as a gated cross-OS contract. |
| ASC-0002 | capabilityos-executable-surface | closed | Create the first recommendation-only CapabilityOS package and CLI surface. |
| ASC-0003 | dispatch-packet-enrichment | closed | Enrich aios_dispatch.py JSON packets so child agents do not have to re-derive their task slice from the contract body. |
| ASC-0004 | dispatch-watcher-and-state-machine | closed | Add release/hold/retry/escalate state machine to aios_dispatch and a V1 watcher that auto-runs verification gates from inbox packets. |
| ASC-0005 | hive-capability-bridge | closed | Add hivemind/hivemind/capability_bridge.py mirroring memory_bridge.py — calls CapabilityOS recommend during route phase, optional and non-blocking. |
| ASC-0006 | aios-l6-repeatable-proof | closed | Add a machine-readable AIOS readiness gate that proves or blocks L6 repeatable completion. |
| ASC-0007 | workspace-doc-scout-task-radar | closed | Add a control-plane doc scout that searches jaewon workspace docs and turns signals into an AIOS task radar and next contract candidates. |
| ASC-0008 | workspace-doc-ingest-memoryos | closed | Turn ASC-0007 doc scout signals into reviewed MemoryOS context records with provenance, without raw export ingestion. |
| ASC-0009 | capability-observation-feedback | closed | Consume task-radar entries and dispatch result packets to record CapabilityOS observations and fallback plans. |
| ASC-0010 | hive-semantic-quality-gate | closed | Add a Hive verification packet that reviews top task-radar candidates for executable next steps before broad dispatch. |
| ASC-0011 | control-plane-loop-policy | closed | Decide which doc-radar candidates become accepted contracts and which remain held through a checkable policy. |
| ASC-0012 | child-repo-durability-closeout | closed | Turn ASC-0008, ASC-0009, and ASC-0010 child-repo working-tree implementations into repo-local durable commits or explicit holds. |
| ASC-0013 | workspace-instruction-index | closed | Index AGENTS, CLAUDE, CODEX, CURRENT, and repo ownership rules into a control-plane instruction map. |
| ASC-0014 | control-plane-monitor-hygiene | closed | Remove monitor false positives for normal contract closeout and repo-suffixed legacy result dispatch ids. |
| ASC-0015 | child-repo-dirty-triage | closed | Resolve the remaining memoryOS and hivemind dirty files left after ASC-0012 and ASC-0014. |
| ASC-0016 | monitor-reconciliation-registry | closed | Add an audited monitor reconciliation registry for known legacy dispatch-history drift. |
| ASC-0017 | control-plane-monitor-sidecar | closed | Keep the MyWorld control-plane observer available as a long-running sidecar. |
| ASC-0018 | loop-policy-source-hygiene | closed | Prevent loop policy from accepting already-closed contract documents as new executable work. |
| ASC-0019 | monitor-assessment-brain | closed | Give the control-plane monitor an assessment layer that maps alerts to owner, severity, and next action. |
| ASC-0020 | hive-worklog-gap-cleanup | closed | Turn Hive worklog and gap-radar signals into one current executable Hive packet without re-opening closed work. |
| ASC-0021 | hive-arrival-pack | closed | Add a Hive arrival-pack surface that gives incoming agents a compact, privacy-safe run brief from live run state. |
| ASC-0022 | aios-goal-evolution-loop | closed | Add a goal-level AIOS evolution loop that turns one active north-star goal into the next best contract candidate with evidence. |
| ASC-0023 | hive-source-read-registry | closed | Add a Hive source-read registry so runs can record which agents read which source artifacts and surface divergent interpretations. |
| ASC-0024 | goal-planner-source-hygiene | closed | Keep the goal evolution planner from selecting broad history/index documents as direct implementation candidates and advance completed preferred-next items. |
| ASC-0025 | child-watcher-provider-fallback | closed | Make child watcher implementation runs recover once from provider access-denied by trying an allowed alternate agent and recording structured fallback evidence. |
| ASC-0026 | capability-observation-aware-routing | closed | Make CapabilityOS recommendations consume prior observation outcomes so later routing decisions reflect real AIOS result history. |
| ASC-0027 | memory-feedback-directives | closed | Make accepted MemoryOS context produce explicit next-run feedback directives and have Hive render them into context_pack.md. |
| ASC-0028 | capability-route-binding | closed | Bind child watcher provider fallback selection to CapabilityOS observation-aware provider route recommendations. |
| ASC-0029 | persistent-control-loop | closed | Add a persistent control-plane round controller so AIOS continuation does not depend on a chat turn staying open. |
| ASC-0030 | capabilityos-web-research-route | closed | Add a recommendation-only CapabilityOS web research route so AIOS can deliberately use broad internet search with source and privacy guardrails. |
| ASC-0031 | web-evidence-execution-loop | closed | Dogfood CapabilityOS web-route by producing and validating a cited web evidence receipt for AIOS capability routing. |
| ASC-0032 | uri-repo-isolation-setup | closed | Create an isolated Uri child repository and private `uri-v3` remote without mixing product artifacts into the MyWorld control plane. |
| ASC-0033 | sovereign-ai-governance-readiness | closed | Define and validate the next AIOS readiness layer for accountable enterprise-scale and sovereign-AI governance. |
| ASC-0034 | governance-action-policy-engine | closed | Add a machine-checkable AIOS action policy engine that gates proposed actions by authority, risk, privacy, resource use, and checkpoint requirements. |
| ASC-0035 | policy-gated-dispatch | closed | Wire the action policy into dispatch creation and sending so checkpoint-required packets are blocked before inbox delivery. |
| ASC-0036 | cross-repo-semantic-alignment | closed | Teach every lower-repo agent the AIOS shared language and require semantic handshakes before cross-repo work. |
| ASC-0037 | child-watcher-locale-aware-fallback | closed | Make child-watcher provider-fallback recognize Korean codex CLI access-denied messages so localized provider failures trigger fallback. |
| ASC-0038 | self-resonant-repo-loop | closed | Let lower repos submit goals or friction to myworld, receive MemoryOS/CapabilityOS/Hive route packets, and turn returned friction into AIOS improvement candidates. |
| ASC-0039 | visual-control-application | closed | Create the first local visualization-first AIOS control surface from generated myworld state snapshots. |
| ASC-0040 | on-prem-evolving-application | closed | Package the local AIOS control app, snapshot refresh, monitor write, static server, and round-controller status into one repeatable local command. |
| ASC-0041 | web-evidence-memory-review | closed | Turn validated web evidence receipts into MemoryOS draft review candidates without auto-accepting web-derived facts. |
| ASC-0042 | capability-observation-memory-import | closed | Convert CapabilityOS observations into MemoryOS draft review candidates without auto-accepting capability claims. |
| ASC-0043 | contract-autodraft-from-goal-plan | closed | Turn an unblocked goal evolution recommendation into a proposed smart contract draft without relying on chat memory. |
| ASC-0044 | desktop-control-application | closed | Provide a non-web native desktop AIOS control app for local monitor, contract, dispatch, repo, and route state. |
| ASC-0045 | hive-handoff-compat-import | closed | Add a Hive HANDOFF.json/shared-folder compatibility import so old MemoryOS pingpong loops can replay into Hive run artifacts. |
| ASC-0046 | goal-evolution-concrete-hive-todo | closed | Make goal evolution refine the recurring Hive radar-gap recommendation into a concrete unchecked Hive TODO so the loop does not repeat closed subitems. |
| ASC-0047 | hive-evaluate-subagents-review | closed | Add a first-class Hive evaluation command that runs verifier, product evaluator, and actual-user persona checks into durable run artifacts. |
| ASC-0048 | goal-evolution-semantic-verifier-refinement | closed | Refine the recurring Hive radar-gap recommendation to the concrete semantic-verifier TODO instead of returning a broad RADAR_GAP_TRIAGE source. |
| ASC-0049 | hive-semantic-verifier-review | closed | Add a Hive semantic verifier review surface for high-risk runs without automatic provider execution. |
| ASC-0050 | aios-primitive-surface | closed | Reverse-engineer Claude CLI operator primitives into a substrate-independent AIOS primitive surface for Codex and local LLM workers. |
| ASC-0051 | aios-coevolution-heartbeat | closed | Arm MemoryOS, CapabilityOS, and Hive co-evolution pulse loops through the AIOS primitive monitor surface. |
| ASC-0052 | aios-native-runtime-entrypoint | closed | Provide one AIOS-native runtime entrypoint so Claude/Codex CLIs become replaceable substrates behind the AIOS loop. |
| ASC-0053 | hive-provider-loop-runner | closed | Add a Hive-owned provider loop runner for Claude CLI, Codex CLI, and local LLM workers with shared tick/status/stop receipts. |
| ASC-0054 | global-aios-launcher | closed | Add a thin global `aios` launcher candidate that resolves the active MyWorld control plane while keeping AIOS state workspace-local. |
| ASC-0055 | absorb-ollama-qwen25-7b | closed | Demonstrate provider absorption by adding recommendation-only CapabilityOS and Hive declarations for Ollama Qwen 2.5 7B. |
| ASC-0056 | memoryos-draft-pipeline-closure | closed | Close MemoryOS draft pipeline gaps: pulse ingest, review proposals, and accepted-memory context surfacing. |
| ASC-0057 | pulse-heartbeat-persistence | closed | Keep MemoryOS, CapabilityOS, and Hive co-evolution pulse monitors alive from each round-controller tick. |
| ASC-0058 | goal-inbox-processor | closed | Process repo-originated goal/friction packets into proposed contracts, operator queue notes, or capability gaps. |
| ASC-0059 | watcher-race-resolution | closed | Detect related dirty work before child-agent spawn and surface orphan work left after failed watcher attempts. |
| ASC-0060 | action-policy-scope-aware | closed | Stop myworld-only operator-script dispatches from false-escalating as private remote data while preserving raw/private path checkpoints. |
| ASC-0061 | dispatch-escalate-recovery | closed | Make operator release of an escalated dispatch write an audited override inbox packet instead of leaving the dispatch stuck. |
| ASC-0062 | peer-share-privacy-projection | closed | Define and verify the first Sovereign Swarm privacy projection layer before peer identity or remote sync exists. |
| ASC-0063 | uri-content-relevance-filter | closed | Filter Uri-originated markdown so AIOS absorbs cross-OS-relevant insights without ingesting product-internal noise. |
| ASC-0064 | live-dashboard-websocket | closed | Add a local WebSocket stream and simple/operator modes to the AIOS control dashboard. |
| ASC-0065 | genesisos-bootstrap | closed | Create GenesisOS as the AIOS divergence layer that generates non-obvious candidate directions before verification. |
| ASC-0066 | provider-backpressure-role-distillation | closed | Classify provider rate limits and failures, then preserve role capsules for fallback providers instead of stalling. |
| ASC-0067 | unified-os-invocation-pipeline | closed | Route one incoming goal through GenesisOS, MemoryOS, CapabilityOS, Hive, and MyWorld as explicit role artifacts before dispatch. |
| ASC-0068 | global-project-agent-discovery | closed | Discover project-local agent specifications across a workspace and emit ASC-0067-compatible invocation envelopes under strict authority boundaries. |
| ASC-0069 | genesis-prompt-prison-critic | closed | Add a deterministic GenesisOS critic that detects prompt-prison signatures and surfaces escape vectors. |
| ASC-0070 | genesis-assumption-mutator | closed | Generate deterministic GenesisOS assumption mutation seeds for operator review without mutating source records. |
| ASC-0071 | genesis-multi-universe-branches | closed | Fork, list, and explicitly collapse speculative GenesisOS branches before contract convergence. |
| ASC-0072 | genesis-multi-modal-reasoning | closed | Translate contract text into deterministic non-language modalities for advisory prompt-prison escape. |
| ASC-0073 | genesis-cross-domain-analogy | closed | Match AIOS problems against curated distant-domain patterns and write advisory analogy artifacts. |
| ASC-0074 | genesis-pre-close-challenge | closed | Run GenesisOS challenge reports before in-registry accepted contract releases and soft-block high-risk closeouts unless explicitly overridden. |
| ASC-0075 | genesis-seed-library | closed | Preserve speculative GenesisOS seeds in an append-only library with MyWorld operator capture receipts. |
| ASC-0076 | contract-closeout-reconciliation | closed | Reconcile accepted-but-unclosed contracts from ASC-0056 through ASC-0068 into an explicit execution queue. |
| ASC-0077 | genesisos-semantic-alignment-kernel | closed | Extend GenesisOS into a shared-meaning kernel that normalizes local/project/agent language onto canonical AIOS terms. |
| ASC-0078 | aios-work-visibility-layer | closed | Expose current AIOS work, blocked dispatches, changed files, receipts, and next actions through one redacted work-view surface. |
| ASC-0079 | hivemind-public-alpha-hardening | closed | Convert external GitHub evaluation of hivemind into a bounded public-alpha hardening packet owned by the Hive repo. |
| ASC-0080 | aios-native-installation | closed | Make AIOS feel built-in through a reversible user-space global command, user service, and optional desktop entry. |
| ASC-0081 | provider-fallback-execution-binding | closed | Bind provider backpressure role capsules to a verified fallback execution path for Claude, Codex, Gemini, or local LLM workers. |
| ASC-0082 | product-repo-sprint-driver | proposed | Turn product-repo goals into AIOS-owned sprint packets with Genesis, MemoryOS, CapabilityOS, Hive, verification, and feedback. |
| ASC-0083 | research-to-sprint-context-primitive | proposed | Convert public research receipts into sprint context, MemoryOS drafts, CapabilityOS route notes, and Hive execution hints. |
| ASC-0084 | hive-debate-aios-dna | closed | Run a long-round Hive Mind deliberation on the proposed AIOS DNA before writing the DNA spec. |
| ASC-0085 | codex-cli-aios-absorption | closed | Record Codex CLI self-observation and install global Codex guidance so AIOS can absorb Codex as a provider substrate. |
| ASC-0086 | capability-genesis-autonomy-envelope | proposed | Give CapabilityOS and GenesisOS higher freedom inside explicit non-destructive autonomy envelopes. |
| ASC-0087 | provider-prompt-bootstrap | closed | Bootstrap provider-specific AIOS prompt files with marker-scoped safe merge and user-space templates. |
| ASC-0089 | hive-debate-asc0088-alternatives | closed | Use Hive deliberation to choose the correct AIOS Universal Agent Interface shape before releasing ASC-0088. |
| ASC-0090 | agent-identity-registry | closed | Replace ad-hoc agent strings with a stable per-agent identity registry. |
| ASC-0091 | memoryos-auto-writeback | closed | Generate MemoryOS drafts automatically from contract closeouts. |
| ASC-0093 | aios-agent-interface-tiny-spec | closed | Supersede held ASC-0088 with the Hive-selected B1 tiny substrate-neutral agent interface spec. |
| ASC-0094 | provider-fallback-verifier | closed | Add a Hive-owned verifier that decides whether fallback provider output can be promoted from draft/attempt to completed work. |
| ASC-0095 | provider-output-projection | closed | Add a redacted Hive provider-output projection receipt so future semantic quality checks can reason over provider results without raw output bodies. |
| ASC-0096 | control-plane-pingpong-provider-fallback | closed | Prevent myworld pingpong from stopping on provider access denial by falling back to the paired provider with event receipts. |
| ASC-0096 | goal-bar-natural-input | closed | Add a natural-language Goal Bar to the control app that classifies common AIOS questions, shows the routed command, and executes locally only after confirmation. |
| ASC-0097 | hive-unified-explore-tui | closed | Add a unified Hive TUI explore screen for Agents, Runs, Inspect, Events, and Ask without adding dependencies. |
| ASC-0105 | aios-dna-canonical-spec | closed | Convert ASC-0084 Hive verdict into the canonical AIOS DNA specification at docs/AIOS_DNA.md. |
| ASC-0106 | aios-governance-audit | closed | Measure whether closed AIOS contracts carry real verification, DNA, Hive, dogfood, and cross-OS evidence. |
| ASC-0107 | citizenship-implementation | closed | Implement agent citizenship classes and V1 authority checks over the ASC-0090 registry. |
| ASC-0109 | end-user-ask-surface | closed | Raise the AIOS control app from operator dashboard to end-user intake with plan-only ask artifacts and contract seeds. |
| ASC-0110 | memoryos-retrieval-broken | closed | Repair MemoryOS founder/context retrieval so accepted memories surface reliably while drafts remain review candidates. |
| ASC-0111 | founder-behavior-ingestion | closed | Capture founder directives, reframes, and decision patterns as first-class MemoryOS draft memories with explicit review. |
| ASC-0112 | aios-chat-wrapper | closed | Add the persistent AIOS chat surface with router-first substrate selection, history, cost, MemoryOS-compatible drafts, CLI, launcher, and WebSocket chat. |
| ASC-0113 | user-pattern-few-shot | closed | Extract draft founder/user behavior patterns and inject provenance-bound few-shot hints into chat and invocation plans. |
| ASC-0114 | living-organism-hive-deliberation | closed | Run Hive deliberation on founder role substitution and converge on leased routine substitution only. |
| ASC-0115 | goal-inbox-per-citizen-response | closed | Stop goal-inbox processing from silently collapsing citizen packets into one generic theme. |
| ASC-0118 | readiness-reconciliation-binding | closed | Bind readiness L6 pending-packet checks to monitor reconciliations and current running packets. |
| ASC-0119 | os-activity-evidence | closed | Count invocation role artifacts as OS activity so self-check does not ghost GenesisOS when it is active through `aios_invoke`. |
| ASC-0120 | verifier-priority-precedence | closed | Prioritize verifier-issued accepted contracts over codex-auto work after the verifier wait threshold while keeping founder GO highest. |
| ASC-0121 | strict-close-condition | closed | Forbid contract closure when stated goal is verifiably unmet by adding a close-condition evaluator, strict release classifications, and a retro close baseline. |
| ASC-0122 | policy-actually-binding | closed | Make the round controller consume loop-policy ordering before dispatch and record policy-followed or explicit skip reasons. |
| ASC-0123 | self-check-dispatch-health-scalar | closed | Keep AIOS self-check output machine-scalar by preventing dispatch health from emitting multi-line values under pipefail. |
| ASC-0124 | hive-debate-ecosystem-substrate | closed | Debate the ecosystem substrate choices for AIOS and converge on protocol-core substrate with optional packaging. |
| ASC-0125 | genesisos-dispatch-surface | closed | Add GenesisOS to the dispatch repo surface so Philosophy work can receive first-class packets. |
| ASC-0126 | memoryos-retrieval-real-fix | closed | Fix MemoryOS retrieval signal coverage so Agent(Retriever) returns relevant accepted memories. |
| ASC-0127 | 5-persona-cognitive-architecture-axis | closed | Evaluate AIOS as Hive/Memory/Capability/Genesis/MyWorld cognitive personas rather than pure governance paperwork. |
| ASC-0143 | aios-session-envelope-runtime-binding | closed | Bind AIOS invocation artifacts into a session envelope that dispatch packets and watcher results must cite before Codex execution. |
| ASC-0144 | end-user-session-interface | closed | Make the local AIOS control app start from an end-user goal and create a plan-only AIOS session envelope before any executor work. |
| ASC-0145 | reviewed-envelope-to-dispatch-promotion | closed | Let the end-user AIOS session UI promote a reviewed session envelope into a governed contract seed or dispatch packet without chat-only operator prompts. |
| ASC-0146 | end-user-agent-work-visibility | closed | Make the end-user control app show how AIOS agents performed work and what artifacts they produced. |
| ASC-0147 | control-center-mockup-alignment | closed | Align the AIOS end-user control application with the generated final interface mockup. |
| ASC-0148 | inline-aios-conversation-surface | closed | Add a direct AIOS conversation window to the Control Center. |
| ASC-0149 | conversational-response-engine | closed | Replace the fixed AIOS chat receipt sentence with conversational responses that reflect intent, route, MemoryOS context, session status, and next action. |
| ASC-0150 | genesis-friction-radar-quick-actions | closed | Use GenesisOS critique to expose Control Center discomfort as quick actions and a Friction Radar so end users can reach AIOS capabilities without internal command knowledge. |
| ASC-0151 | promotion-review-queue | closed | Show reviewed session promotions and generated contract seeds in the Control Center so users do not have to search `.aios/promotions`. |
| ASC-0152 | aios-identity-chat-response | closed | Make the Control Center chat answer identity questions as AIOS before showing route receipts. |
| ASC-0152 | paper5-p20-law-flow-genesis-gate | closed | Turn the Paper 4/P20 result into a bounded Paper 5 architecture gate using GenesisOS divergence before any claim promotion or new experiment launch. |
| ASC-0153 | os-observatory-visual-interface | closed | Show MemoryOS, CapabilityOS, GenesisOS, Hive Mind, and MyWorld operating activity as visual OS surfaces in the Control Center instead of raw logs. |
| ASC-0154 | aios-chat-gate-agent | closed | Add an explicit AIOS Gate/Chair Agent layer to chat so provider chatbots and CLIs are routed as substrates and current-info questions are held for source-aware routing. |
| ASC-0155 | memoryos-gate-sleep-consolidation | closed | Reverse-engineer prompt-Agent execution loop pairs from AIOS/MemoryOS traces and consolidate them into a personalized Gate few-shot/policy pack before any fine-tuning. |
| ASC-0156 | install-state-control-center | closed | Show AIOS install, service, local UI, and loop reachability in the Control Center with simple end-user wording. |
| ASC-0157 | contract-seed-os-evidence-slots | closed | Make AIOS-generated contract seeds carry explicit MemoryOS, CapabilityOS, GenesisOS, and Hive evidence slots by default. |
| ASC-0158 | release-authority-hard-block | closed | Prevent AIOS dispatch release from proceeding when authority verification returns a hard denial. |
| ASC-0159 | aios-operating-layer-paper-draft | closed | Draft the AIOS paper around provider CLI wrapped by a contract-bound operating layer, including evaluation axes and refinement loop. |
| ASC-0160 | paper-refinement-loop | closed | Refine the AIOS operating-layer paper through AIOS role artifacts, reviewer attacks, and evidence tightening. |
| ASC-0161 | paper-related-work-source-evidence | closed | Add source-grounded related work evidence to the AIOS operating-layer paper. |
| ASC-0162 | direct-cli-vs-aios-benchmark-protocol | closed | Define the matched-run benchmark protocol for direct provider CLI versus AIOS-wrapped provider CLI. |
| ASC-0163 | negative-evidence-combinatorial-creativity | closed | Make negative evidence and GenesisOS combinatorial creativity first-class AIOS learning signals. |
| ASC-0164 | genesisos-child-watcher-surface | closed | Make GenesisOS visible to the AIOS child watcher and monitor surfaces so GenesisOS implementation packets can actually run. |
| ASC-0165 | memory-genesis-provider-blindspot-reinforcement | closed | Reinforce MemoryOS and GenesisOS where provider CLIs are weakest: failure memory, retrieval of blind spots, discomfort sensing, and invention candidates. |
| ASC-0166 | provider-pin-required-classification | closed | Classify provider PIN/auth unlock failures without storing secrets, so AIOS watchers can route or checkpoint instead of treating PIN-gated providers as generic access denied. |
| ASC-0167 | capabilityos-permissioned-constraint-break-route | closed | Add a CapabilityOS route that proposes high-freedom constraint-breaking options, asks the user for permission, and assigns actual execution to Hive Mind. |
| ASC-0168 | hivemind-permission-preflight | closed | Let Hive Mind consume CapabilityOS constraint-break routes as operator permission preflights before execution. |
| ASC-0169 | hivemind-aios-packet-runner | closed | Let Hive Mind consume AIOS hivemind inbox packets through its own provider-loop runner instead of relying only on the MyWorld shell child watcher. |
| ASC-0170 | hivemind-scoped-writable-provider-execution | closed | Open Hive Mind writable provider execution only behind AIOS packet scope, explicit execution request, and operator grant. |
| ASC-0171 | hivemind-permissioned-dangerous-provider-execution | closed | Allow Hive Mind to represent Codex dangerous full-access provider execution only as an explicit AIOS danger route with operator grant, irreversible authority, and proof receipts. |
| ASC-0187 | capabilityos-browser-visual-verification-route | closed | Add a recommendation-only CapabilityOS route for browser visual verification after Firefox screenshot timeout exposed a routing gap. |
| ASC-0188 | gate-chair-conversational-activation-policy | closed | Let external Gate Chair candidates become operator-promotable when they match or beat the internal baseline with no runtime failures, while preserving timeout evidence as MemoryOS drafts. |
