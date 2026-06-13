---
contract_id: ASC-0271-AUX
slug: aios-growth-hardening-invariant-pack
status: superseded_duplicate_draft
goal: Preserve Claude's second, more aggressive ASC-0271 hardening draft as an auxiliary note without treating it as operator-accepted or as the canonical ASC-0271 contract.
created: 2026-06-14T02:40:00+09:00
accepted: null
human_approved: false
origin: ASC-0270 claude hardening packet; operator signal "시스템을 공고히 하는 것은 Claude의 역할."
depends_on:
  - ASC-0270
canonical_contract: docs/contracts/ASC-0271-dream-hardening-invariant-pack.md
correction: Codex verifier corrected the original draft's premature `status: accepted` and `human_approved: true` because the operator has not accepted ASC-0271 yet.
---

# ASC-0271-AUX AIOS Growth Hardening Invariant Pack

## Purpose

Codex opened the dream. This auxiliary draft sketches a stronger version of
the gap between dream and safety:
10 named invariants, a growth-sequencing gate, owner-bound follow-on contracts
for each OS, and stop conditions that let Codex move fast without breaking
trust.

The canonical ASC-0271 proposal is
`docs/contracts/ASC-0271-dream-hardening-invariant-pack.md`. This file is
preserved as duplicate hardening material, not as accepted execution authority.

Hardening is not permission to slow growth. It is the structure that makes
aggressive growth safe to commit.

---

## 10 Growth Invariants

Each invariant is checkable, not philosophical. Violation = stop condition.

### I1 — Memory before action

No agent action creates binding state without a MemoryOS path (receipt, draft,
or trace). A receipt counts; prose description does not.

*Check*: every dispatch packet either includes an `evidence_refs` field pointing
to an existing receipt or produces one as a required artifact.

### I2 — Draft-first knowledge

External knowledge (web, research, provider output, Dream Agora intake) is
always `draft` status until an explicit user or operator review marks it
`accepted`. Auto-acceptance by any OS or agent is a stop condition.

*Check*: `status` field on every imported MemoryOS object must be `draft` on
creation. No code path calls `status=accepted` without a reviewer ref.

### I3 — Credential as reference

Credentials, API keys, tokens, and secrets never transit as raw values in
dispatch packets, prompts, receipts, logs, or shared docs. Only opaque grant
refs (e.g. `cred-ref-abc123`, `vault://id`) may appear.

*Check*: `aios_serving_support.py` redaction gate must pass; `serving_access.py`
stores `credential_ref` only; `serving_worker.py` rejects raw-looking
credential strings.

### I4 — Provider is vendor

Providers are replaceable vendors, not OS organs. Every provider surface in
CapabilityOS must have either a fallback route or an explicit
`no_fallback: true` marker with a rationale. Provider lock-in without a
fallback is an architecture defect.

*Check*: `CapabilityOS/capabilityos/catalog.py` cards with no fallback must
carry `no_fallback_reason`.

### I5 — Receipt before closeout

No contract or work packet closes without verifiable evidence markers. Evidence
markers must point to files that exist at closeout time. Prose promises or
planned artifacts do not count as evidence.

*Check*: `git diff --check` on the closing commit; required markers in the
result packet must `os.path.exist()` at collect time.

### I6 — Visual target before UI code

No `apps/serving/**` implementation before the design gate opens
(`build_allowed=true`). Already enforced by `aios_serving_design_gate.py`.

*Check*: `python3 scripts/aios_serving_design_gate.py assess --root . --json`
returns `build_allowed=true` before any serving UI commit.

### I7 — Entropy quota enforced

Every growth milestone that closes a major contract must include at least one
GenesisOS discomfort or counter-branch finding. "Green tests = safe" is not
enough for release gates. Provider convergence risk must be named.

*Check*: `docs/contracts/ASC-0266-genesisos-serving-prelaunch-challenge.md`
already closed for serving. Future major milestones (SMX, Dream Agora, multi-
tenant) need equivalent challenge receipts before closeout.

### I8 — Isolation before scale

SMX, Dream Agora, multi-tenant, and Agent Company Studio work require per-user
workspace isolation proof before production dispatch. Fixtures count as early
proof; prose does not.

*Check*: `hivemind/tests/test_serving_worker.py` proves cross-user denial.
SMX and multi-tenant growth must produce equivalent isolation tests before
production commit.

### I9 — World-ready claim requires release proof

Any distribution, marketing, or user-facing claim of production readiness
requires `ready_for_production_serving=true` from the release gate. Localhost
demos are not production readiness.

*Check*: `python3 scripts/aios_serving_release_gate.py assess --root . --json`
must return `ready_for_production_serving=true`. Currently false; must remain
honest.

### I10 — OS boundary crossing requires contract

Hivemind does not accept memory. MemoryOS does not execute tools. CapabilityOS
does not authorize providers without a routing decision. GenesisOS does not
select final truth. MyWorld does not implement in child repos. Any growth move
that blurs an OS boundary is a new contract, not a shortcut.

*Check*: OS CLAUDE.md hardcoded invariants (recommendation-only, draft-first,
execute-with-receipt, speculative-only) must remain in every child OS.

---

## Growth Sequencing Gate

### Gate A — Safe now (no visual target needed)

These moves are owner-bound, non-UI, and do not require `build_allowed=true`:

| Move | Owner | Nearest Contract |
| --- | --- | --- |
| Dream Agora intake schema | MemoryOS | ASC-0272 (see below) |
| Credential grant layer spec | CapabilityOS | ASC-0273 (see below) |
| SMX bounded workspace design | GenesisOS + Hivemind | ASC-0274 (see below) |
| Provider blindspot harvesting schema | CapabilityOS + MemoryOS | ASC-0272 |
| Entropy quota draft per closeout | GenesisOS | ASC-0275 (see below) |
| MemoryOS as default context source | MemoryOS | ASC-0272 |
| Agent Company Studio framing doc | MyWorld | This contract |

### Gate B — Requires visual target (`build_allowed=true`)

| Move | Owner | Prerequisite |
| --- | --- | --- |
| `apps/serving/**` prototype | myworld | Design gate opened |
| Agent Company Studio UI | myworld | Serving UI proof |
| Browser proof (375px, 1280px) | myworld | `apps/serving/**` exists |

### Gate C — Requires serving UI proof (browser evidence)

| Move | Owner | Prerequisite |
| --- | --- | --- |
| Distribution wedges 2–5 | myworld + external | `ready_for_production_serving=true` |
| Dream Agora intake live | MemoryOS | Serving UI + provider receipt chain |
| SMX bounded variants | Hivemind | Isolation proof + serving UI |
| Multi-tenant isolation | Hivemind + MemoryOS | All Gate B items |
| Production serving gate | myworld | All Gate C prerequisites |

---

## Owner-Bound Follow-On Contracts (Proposed)

### ASC-0272 — MemoryOS Dream Agora Intake

**Owner**: memoryOS  
**Gate**: Gate A (safe now)  
**Goal**: Web/source/provider event → source receipt → MemoryOS draft →
CapabilityOS route observation → reviewed memory or rejected negative evidence.  
**Must produce**:
- `memoryOS/memoryos/dream_agora.py` — intake → draft pipeline
- `memoryOS/tests/test_dream_agora.py` — proves auto-accept blocked, source receipt required
- CapabilityOS route observation schema update

**Stop conditions**: `auto_accept_external_knowledge`, `source_receipt_missing`,
`raw_provider_output_stored_as_accepted`

---

### ASC-0273 — CapabilityOS Credential Grant Layer

**Owner**: CapabilityOS  
**Gate**: Gate A (safe now)  
**Goal**: User-visible grants — what provider/tool, scope, expiry, injection
scope, receipt, revocation. Makes "AIOS acts without nagging" a product feature
rather than a chat habit.  
**Must produce**:
- `CapabilityOS/capabilityos/credential_grant.py`
- `CapabilityOS/tests/test_credential_grant.py` — proves raw credential blocked, opaque ref only, revocation propagates
- User-visible grant schema compatible with `serving_access.py`

**Stop conditions**: `credential_raw_value_in_grant`, `revocation_not_propagated`,
`grant_crosses_user_boundary`

---

### ASC-0274 — GenesisOS + Hivemind SMX Bounded Workspace

**Owner**: GenesisOS (design) + hivemind (execution)  
**Gate**: Gate A design; Gate C execution  
**Goal**: Uncertainty-high tasks → GenesisOS branches N futures → Hivemind runs
bounded isolated variants → verifiers score → winner commits → losers become
counterfactual MemoryOS drafts.  
**Must produce** (design phase, Gate A):
- `GenesisOS/genesisos/smx_branch.py` — bounded branch generator, spec only
- `GenesisOS/tests/test_smx_branch.py`

**Stop conditions**: `smx_runs_without_isolation_receipt`, `winner_overwrites_without_review`,
`losers_auto_accepted_as_memory`

---

### ASC-0275 — GenesisOS Entropy Quota Enforcement

**Owner**: GenesisOS  
**Gate**: Gate A (safe now)  
**Goal**: Every release candidate needs a discomfort budget. Every long task
needs a non-obvious branch. Every "safe consensus" closeout needs a counter-
branch. Every provider convergence gets a dated external baseline.  
**Must produce**:
- `GenesisOS/genesisos/entropy_quota.py` — quota registry and check gate
- `GenesisOS/tests/test_entropy_quota.py`
- Integration hook: `aios_serving_release_gate.py` checks entropy quota before `ready_for_production_serving=true`

**Stop conditions**: `entropy_quota_bypassed_for_release`, `green_tests_only_claimed_as_safe`,
`provider_convergence_unchecked`

---

### ASC-0276 — MyWorld Agent Company Studio Framing

**Owner**: myworld  
**Gate**: Gate A (safe now, docs only); Gate B (UI, after visual target)  
**Goal**: The serving product grows into "a company of agents" — each job shows
which OS owns the work, which tools are approved, which memory is used, which
approvals block. This is the product identity for distribution wedges 2–5.  
**Must produce** (Gate A):
- `docs/product/AIOS_AGENT_COMPANY_STUDIO_BRIEF.md` — framing doc, not UI code
- Update `docs/product/AIOS_SERVING_DESIGN_BRIEF.md` with company framing
- Acceptance gate: no `apps/**` changes until Gate B opens

**Stop conditions**: `ui_before_visual_target`, `company_framing_replaces_individual_user_product`

---

## Hardening Critique of Dream Assumptions

### Assumption 1: "Growth pressure reveals missing OS organs."

**Risk**: growth pressure that reveals missing organs can also bypass them.

**Hardened rule**: New growth vectors that need an organ not yet built must
produce a `proposed` contract for that organ before implementation starts.
Growth via bypass is a stop condition (`growth_bypasses_missing_organ`).

### Assumption 2: "Memory is the company balance sheet."

**Risk**: if all work becomes memory, and memory review is a manual gate, the
balance sheet accretes faster than review.

**Hardened rule**: MemoryOS must have a `draft_backlog_count` observable. When
drafts exceed 50 unreviewed, the next release gate surfaces this as a partial
blocker, not a hard block.

### Assumption 3: "Providers are replaceable employees/vendors."

**Risk**: treating providers as replaceable while depending on one's rate
limits in every critical path.

**Hardened rule**: CapabilityOS catalog must flag any capability with a single-
provider route as `single_provider_risk: true`. At least one Gate C milestone
must demonstrate a working fallback route for the top-3 capabilities.

### Assumption 4: "Safety slows growth / refusal is a trust wedge."

**Risk**: silent denials are UX friction, not a product feature.

**Hardened rule**: Every denial receipt in `serving_access.py`, `serving_worker.py`,
and `serving_memory.py` must have a `user_message` field that explains what
the user can do to resolve the denial.

---

## Agent Company Studio Framing (Gate A artifact)

The serving product identity: AIOS is a company the user can hire.

When a user submits a goal:
- **MyWorld (Board)** issues the job contract;
- **Hivemind (Operations)** runs the work in a sandboxed worker;
- **MemoryOS (Institutional Memory)** feeds context and stores results as drafts;
- **CapabilityOS (Procurement)** routes the tools, checks grants, enforces budget;
- **GenesisOS (R&D)** injects a counter-branch if the task is high-stakes or convergent;
- **Claude (Quality/Legal)** reviews sensitive actions and flags invariant violations before closeout.

The user sees: departments, approvals, artifacts, trust — not raw logs.

---

## Stop Conditions

| Stop Condition | Triggered By | Resolution |
| --- | --- | --- |
| `dream_becomes_vague_prose` | Growth map has no checkable invariants | Add machine-checkable invariant + test |
| `memory_auto_accepts_without_review` | Dream Agora or any intake skips draft | Fix ingestion to always produce `status=draft` |
| `credential_raw_value_transits` | Any dispatch packet, log, or doc contains raw secret | Redact + update sender to use opaque ref |
| `provider_lock_in_without_fallback` | CapabilityOS card has single provider, no fallback marker | Add fallback or mark `single_provider_risk: true` |
| `serving_ui_before_visual_target` | `apps/serving/**` commit before design gate | Revert; wait for `build_allowed=true` |
| `world_ready_claim_without_release_proof` | Any public claim before release gate | Remove claim; fix gate |
| `smx_runs_without_isolation_receipt` | SMX variants launch before isolation proof | Block; require isolation test |
| `os_boundary_crossed_without_contract` | Any OS executes, accepts, or authorizes outside role | Stop; draft contract for the missing capability |
| `entropy_quota_bypassed_for_release` | Major release closes without GenesisOS challenge | Add challenge; re-open release gate |
| `denial_without_user_guidance` | Serving layer denies without `user_message` field | Add `user_message` to all denial receipts |
| `growth_bypasses_missing_organ` | Implementation proceeds without contract for missing OS | Stop; propose contract first |

---

## Verification

```bash
# Existing gates remain honest
python3 scripts/aios_serving_release_gate.py assess --root . --json | python3 -c "import json,sys;d=json.load(sys.stdin);assert not d['ready_for_production_serving'],'overclaim'"
python3 scripts/aios_world_readiness.py --json | python3 -c "import json,sys;d=json.load(sys.stdin);print('world_ready:', d.get('ready_for_world_deployment', False))"
cat .aios/serving/design_gate.json | python3 -c "import json,sys;d=json.load(sys.stdin);assert not d.get('build_allowed'),'build gate open prematurely'"
git diff --check
test -f docs/contracts/ASC-0271-aios-growth-hardening-invariant-pack.md
```

## What This Contract Produces

- I1–I10 invariant pack: named, checkable, machine-verifiable;
- Growth gates A/B/C: sequenced by evidence not optimism;
- 5 owner-bound follow-on contracts proposed (ASC-0272–0276);
- Hardening critique of 4 dream assumptions;
- Agent Company Studio framing artifact.

## What This Contract Does NOT Produce

- No code implementation;
- No `apps/serving/**` changes;
- No auto-accepted memory;
- No provider execution.
