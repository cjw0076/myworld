---
contract_id: ASC-0209
slug: aios-production-readiness-deliberation
status: closed
created: 2026-05-20T17:53:00+09:00
accepted: 2026-05-20T17:53:00+09:00
closed: 2026-05-20T17:59:00+09:00
accepted_by: codex_delegated_operator
human_approved: true
goal: Decide whether current AIOS is immediately production-ready for real users, using dispatch-style external web evidence and LLM-agent deliberation, then set the next organism goal.
origin: founder request — "외부 web researcher는 Dispatch로 서핑 보내고, llm agent 토론해봐. 지금의 AIOS를 Production으로 실제 사용자가 바로 사용 가능한가? 시스템 설계부터 천천히 뜯어보자. 그리고 최종 Goal을 정해야해. 어떤 유기체를 만들건지."
---

# ASC-0209 AIOS Production Readiness Deliberation

DNA references: Invariant 1 (decide before acting), Invariant 5
(provenance chain), Invariant 6 (operator override), Invariant 7
(private-gated data stays out of dispatch and prompt artifacts).

This contract deliberates; it does not deploy. It produces only deliberation
artifacts, a web evidence receipt, and an offline-user-agent protocol. No
deployment code, provider credential path, or external production endpoint is
authorized.

## Decision

Current AIOS is **not yet production-ready for immediate general real-user
use**.

It is better classified as:

```text
operator-grade body complete
  -> production-alpha candidate
  -> not yet real-user production
```

ASC-0205 closed the AIOS body-completion checklist. It proved a repeatable
control-plane loop, packaging smoke, dispatch result packets, provider
diversification evidence, GenesisOS challenge, and monitor-backed closeout. It
did not prove clean-user onboarding, release operations, supportability,
upgrade/rollback, external product traffic, or a user-facing approval/recovery
experience.

## Genesis Escape Review

Plain language: do not let "production" mean "the founder can operate the
system from this workspace." Production means a new real user can install it,
understand what it is allowed to do, recover from failures, and trust the
evidence without reading the source tree.

Assumptions to challenge:

1. Assumption: ASC-0205 completion implies user readiness. Negation: ASC-0205
   proves body completion, not onboarding, release operations, or support.
2. Assumption: more internal contracts will make AIOS production-ready.
   Negation: the next proof must involve real external product traffic.
3. Assumption: local-first means single-user only forever. Negation: local-first
   can still later support a relay or hosted topology if a trust contract
   explicitly approves it.

Counter-default branch: if the operator wants to ship immediately, define the
release as **Founder Production / Real-User Alpha Blocked** rather than
general production. The allowed claim is: "AIOS is ready for founder-operated
production-alpha experiments." The blocked claim is: "AIOS is ready for normal
users without operator guidance."

Time horizons:

- 1h: record this production-readiness decision, receipt, and dispatch result.
- 1w: run one Real User Alpha Loop through `uri` or another consumer repo.
- 1y: make AIOS a durable personal control plane that can survive upgrades,
  provider failures, product feedback, and repeated non-founder use.

## Final Organism Goal

Build AIOS into a **local-first, installable agent operating organism** that
turns a user's goal into routed, verified, remembered work across multiple
repos and products, with explicit authority boundaries, privacy-preserving
memory, provider fallback, GenesisOS challenge, operator-visible state, and
repeatable release, upgrade, rollback, recovery paths, and a governed
`user@offline` loop that lets AIOS ask the embodied user for observations no
model, web search, or repo context can safely infer.

Short form:

```text
AIOS is the personal control plane for trustworthy autonomous software work.
```

## Offline User Agent

The founder's follow-up requirement changes the production goal: AIOS must
think beyond the user's current knowledge and beyond the agent's system or
training limits.

The system answer is recorded in:

- `docs/AIOS_OFFLINE_USER_AGENT_PROTOCOL.md`

Design rule:

```text
AIOS does not pretend to know beyond its boundary.
AIOS names the boundary, routes for outside evidence, and can ask
user@offline for bounded field observations.
```

The offline user is an agent, not just an input box:

- embodied sensor for the world AIOS cannot inspect;
- taste and meaning judge for product direction;
- private-context holder who can summarize without leaking raw data;
- field executor for small real-world tests;
- sovereign authority over which unknowns matter.

This preserves local-first privacy while expanding AIOS beyond both model
training and the user's already-articulated knowledge.

## System Design Read

AIOS already has a real organism shape:

- `myworld`: control tower / brainstem. Owns contracts, dispatch, global
  ledger, monitor state, and operator checkpoints.
- `hivemind`: motor system. Owns execution, scheduling, provider wrapping,
  proofs, and verification.
- `memoryOS`: hippocampus plus provenance immune memory. Owns memory, context
  packs, review lifecycle, and retrieval traces.
- `CapabilityOS`: sensory-routing cortex. Owns capability maps, provider and
  tool recommendations, and fallback plans.
- `GenesisOS`: divergence cortex. Owns assumption mutation, semantic
  alignment, prompt-prison critique, and pre-close challenge surfaces.
- Control Center / CLI / installer: skin and hands. Makes the organism usable
  by the operator.

The current weak point is not conceptual anatomy. The weak point is real
traffic and release survival: a fresh user must be able to install AIOS,
submit a bounded goal, approve risky actions, watch progress, understand
failures, verify the result, and resume later without reconstructing truth from
repo logs or chat history.

## Deliberation Evidence

### Web Researcher Dispatch

The external web pass is recorded as:

- `docs/evidence/ASC-0209-production-readiness-web-evidence.json`

Public evidence synthesis:

- Current agent production guidance emphasizes tracing, observability,
  guardrails, human approval, persistence, identity and auth scopes,
  credentials, sandboxes, async durability, monitoring, cost/failure metrics,
  and evaluation transparency.
- AIOS has several internal analogues: contracts, dispatch receipts, monitor
  findings, result packets, provider routing, and GenesisOS challenge.
- AIOS has not yet proven real-user production primitives: first-run
  onboarding, external consumer workflow, release topology, upgrade/rollback,
  durable approval/resume UX, supportable failure taxonomy, and public
  accountability boundaries.

### LLM Agent Debate

Three bounded LLM debaters were used as advisory reviewers:

- Production Skeptic: current evidence proves L6/operator readiness, not
  production fitness. Top blockers are missing external product proof, dirty
  release state, inconsistent load-bearing MemoryOS retrieval, immature
  fallback regime, and missing upgrade/rollback/support packaging.
- System Architect: the organism goal should be a local-first control plane
  for trustworthy autonomous software work. Next contracts should activate a
  consumer testbed, close hosting/trust topology, and add release supervisor
  plus upgrade loop.
- Real User / UX Operator: production-ready means a real user can install,
  submit a goal, approve risky actions, watch progress, understand failures,
  verify output, and resume without reading source docs.

## Production Readiness Bar

AIOS may claim **real-user alpha** only after one narrow workflow proves:

```text
fresh install/start
  -> first-run setup
  -> user goal intake
  -> plan preview
  -> explicit approval for risky actions
  -> dispatch/watch/collect
  -> result evidence
  -> user accept/reject
  -> MemoryOS/CapabilityOS writeback
  -> restart/resume proof
```

AIOS may claim **production for real users** only after alpha also has:

- versioned release artifact;
- clean install from outside the founder workspace;
- upgrade and rollback path;
- `aios doctor` or equivalent repair/diagnostic command;
- user-facing failure taxonomy and recovery controls;
- privacy and credential boundaries surfaced in product UI;
- at least one external product repo completing repeated real work cycles;
- support boundary and release notes;
- monitor/receipt evidence that can be understood without chat context.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-0209-aios-production-readiness-deliberation.md`
- `docs/AIOS_OFFLINE_USER_AGENT_PROTOCOL.md`
- `docs/evidence/ASC-0209-production-readiness-web-evidence.json`
- `docs/AGENT_WORKLOG.md`
- `.aios/inbox/myworld/asc-0209.myworld.json`
- `.aios/outbox/myworld/asc-0209.myworld.result.json`

forbidden_files:

- `.env`
- provider auth files
- raw exports
- private history stores
- child repo implementation files
- production credentials

## AIOS Role Evidence

### 5-Persona Use

- Hive / Wrapper: this contract uses dispatch/watch/collect as verification
  wrapper; no child implementation execution is authorized.
- MemoryOS / Retriever: no accepted memory write in this contract; the output
  is a draft strategic decision and web receipt for future review.
- CapabilityOS / Router: web research follows
  `capabilityos.web_research_route.v1`; CapabilityOS did not execute network.
- GenesisOS / Philosophy: LLM debate explicitly challenged ASC-0205 completion
  framing before accepting any production claim.
- MyWorld / Sovereign: founder requested the deliberation; final production
  label remains operator-overridable.

## Verification Gate

```bash
python scripts/aios_web_research_receipt.py validate docs/evidence/ASC-0209-production-readiness-web-evidence.json --json
python scripts/aios_local_app.py status --json --assert-live
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `production_overclaim`: any artifact says AIOS is ready for general real
  users now without the alpha/release evidence above.
- `uncited_web_claim`: external production guidance is summarized without a
  source URL in the receipt.
- `private_data_leak`: receipt or contract includes secrets, raw exports, or
  private provider logs.
- `child_repo_bypass`: this deliberation turns into implementation in a child
  repo without a follow-on contract.
- `goal_ambiguous`: the next organism goal is not stated as a named exit.

## Work Packets

### WP-0209-A — Codex@myworld production-readiness deliberation

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-20
- accepted: 2026-05-20
- closed: 2026-05-20
- depends_on: ASC-0205
- brief: |
    Perform one dispatch-style external web research pass, run bounded LLM
    agent debate, decide whether AIOS is immediately production-ready for real
    users, and record the next organism goal. Do not edit child repo
    implementation. Do not store private data in evidence artifacts.
- result: `.aios/outbox/myworld/asc-0209.myworld.result.json`

## Receipts

- web evidence receipt:
  `docs/evidence/ASC-0209-production-readiness-web-evidence.json`
- offline user agent protocol:
  `docs/AIOS_OFFLINE_USER_AGENT_PROTOCOL.md`
- dispatch packet:
  `.aios/inbox/myworld/asc-0209.myworld.json`
- result packet:
  `.aios/outbox/myworld/asc-0209.myworld.result.json`
- policy checkpoint:
  initial send escalated on external-effect/credential-keyword heuristics;
  founder-requested web research was released with reason
  `founder_requested_external_web_research_dispatch_after_policy_checkpoint`.
- verification:
  `python scripts/aios_web_research_receipt.py validate docs/evidence/ASC-0209-production-readiness-web-evidence.json --json`
  passed; `python scripts/aios_local_app.py status --json --assert-live`
  passed; `python scripts/aios_monitor.py assess --json` returned
  `health=watch` with only `persona_axis_advisory` info finding.
