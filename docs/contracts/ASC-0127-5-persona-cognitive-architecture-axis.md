---
contract_id: ASC-0127
slug: 5-persona-cognitive-architecture-axis
status: closed
goal: Replace the current "governance_score" (procedural-compliance) AIOS evaluation axis with a "5-persona cognitive architecture" axis per founder 2026-05-14 reframe — Hive=Wrapper, Memory=Retriever, Capability=Router, Genesis=Philosophy, myworld=Sovereign. Measure whether the 5 OS actually function as 5 specialized brain-regions of Agent(Main), not whether contracts/ledger/tests are merely filled.
created: 2026-05-14 KST
accepted: 2026-05-14 KST by claude@myworld (operator) per founder explicit GO "계약 우선순위대로 전달해".
closed: 2026-05-14 KST by codex@myworld
acceptance_authority: claude@myworld (operator) per founder explicit GO.
human_approved: true
human_approval_note: "founder GO 2026-05-14 KST 'C → D → B' priority + '계약 우선순위대로 전달해'. action_policy flagged uses_credentials=true on body word 'token' (substring match against 'token/secret/credential/login') — false positive; contract has no real credential surface. Tracked as separate dispatch policy fix; not blocking this contract."
origin: founder reframe 2026-05-14 KST: "5개의 OS는 Agent(Main)을 잘 사용하는 방법" — Hivemind = Agent(Wrapper), MemoryOS = Agent(Retriever), CapabilityOS = Agent(Router), GenesisOS = Agent(Philosophy), myworld = Agent(Sovereign per claude proposal). This reframe makes the current evaluation surface (ASC-0106 governance_audit + ledger count + test count) categorically wrong: it measures procedural-compliance not cognitive-function. Verifier needs a new axis or AIOS continues optimizing for governance-theater.
---

# ASC-0127 5-Persona Cognitive Architecture Evaluation Axis

## Why Now

Founder reframe 2026-05-14 KST recompressed AIOS:

```
Hivemind     = Agent(Wrapper)     "여러 CLI + Local LLM 묶음, 단일 실패점 제거"
MemoryOS     = Agent(Retriever)   "재원/작업/프로젝트 ontology"
CapabilityOS = Agent(Router)      "도구 + 잠재 도구 + 웹 지식 라우팅"
GenesisOS    = Agent(Philosophy)  "불편함→필요성, 세계선 생성, 의미 정렬"
myworld      = Agent(Sovereign)   "정체성 + DNA 발의 + 4인격 통합"
```

Current evaluation surface (ASC-0106 governance_audit, monitor assess,
readiness probes) answers "did the contract follow procedure?" — useful for
audit but blind to cognitive function. It cannot say:

- Is `Agent(Wrapper)` actually invoked across providers, or only Claude?
- Does `Agent(Retriever)` ground responses, or just sit there?
- Is `Agent(Router)` chosen for tool selection, or bypassed?
- Is `Agent(Philosophy)` consulted on each non-trivial decision?
- Is `Agent(Sovereign)` mode held (vs worker-mode default)?

Without these signals, governance theater is the equilibrium: 110 contracts,
3% DNA citation, 33% verification, Genesis stub, retrieval=0. ASC-0127
introduces the orthogonal axis.

DNA references: Invariant 1 (decide before acting — adding metric is a
decision), Invariant 5 (provenance — each persona invocation must cite
evidence), Invariant 6 (operator override — metric is advisory, not gate),
Invariant 8 (classify before committing).

## Required Reading

- `scripts/aios_governance_audit.py` (existing axis)
- `scripts/aios_monitor.py` (existing assess)
- `scripts/aios_readiness.py`
- `docs/AIOS_PROVIDER_ABSORPTION.md`
- founder reframe (this turn — quoted in origin)
- `docs/contracts/ASC-0124-hive-debate-ecosystem-substrate.md` (in flight — verdict feeds into this contract's interpretation)

## Scope

repos: `myworld`

allowed_files:

- `scripts/aios_persona_audit.py`
- `tests/test_aios_persona_audit.py`
- `docs/AIOS_PERSONA_AXIS.md`
- `scripts/aios_monitor.py` (extend assess to include persona axis as advisory finding)
- `docs/contracts/ASC-0127-5-persona-cognitive-architecture-axis.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`, `memoryOS/**`, `CapabilityOS/**`, `GenesisOS/**`, `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`
- `.env`
- `scripts/aios_governance_audit.py` (do NOT modify — coexists as separate axis)

## Per-OS Responsibility

### myworld.must_produce

1. **`scripts/aios_persona_audit.py`** — for a given window (default: last 20 closed contracts):
   - **wrapper_score**: fraction of contracts that named ≥2 distinct execution
     providers OR explicitly justified single-provider. Source: `acceptance_authority`,
     receipts, dispatch agent field.
   - **retriever_score**: fraction of contracts whose `origin` or design cites a
     memoryOS context_build trace_id, AND that trace returned `signal_coverage > 0`.
   - **router_score**: fraction of contracts that cite a `capabilityos recommend`
     trace and either follow the top route or document deviation.
   - **philosophy_score**: fraction of contracts that cite a `genesisos` critic /
     branches output, OR explicitly state ≥3 alternatives surfaced.
   - **sovereign_score**: fraction of contracts where acceptance_authority is the
     operator pair AND vision-class decisions are escalated to founder
     (vs auto-absorbed by worker-mode operator).
   - **persona_composite**: mean of the 5 (advisory, not a gate).
   - JSON output with per-contract breakdown for audit.

2. **Detection heuristics, deterministic V1**:
   - Wrapper: regex on dispatch agent string, count of provider mentions
   - Retriever: grep for `rtrace_` token in contract origin/receipts + cross-ref signal_coverage
   - Router: grep for capability recommendation reference
   - Philosophy: grep for `genesis` / `critic` / "alternatives" / "branches" in contract body
   - Sovereign: check `acceptance_authority` matches operator pattern + presence of explicit founder gate when vision keywords appear

3. **`docs/AIOS_PERSONA_AXIS.md`** — defines all 5 scores with examples of:
   - what a score-1 contract looks like (full persona invocation)
   - what a score-0 contract looks like (persona bypassed)
   - the relationship between persona axis and governance axis (orthogonal)

4. **`aios_monitor.py assess` integration**: surface
   `persona_composite` as a separate finding. Never blocks; never overrides
   governance_score. Two axes coexist.

5. **Tests**: synthetic contracts cover each persona's score-0/score-1 detection.

### Hive / Memory / Capability / Genesis: no source change.

## Verification Gate

```bash
python -m py_compile scripts/aios_persona_audit.py
python -m unittest tests/test_aios_persona_audit.py
python scripts/aios_persona_audit.py --window 20 --json --assert-keys wrapper_score,retriever_score,router_score,philosophy_score,sovereign_score,persona_composite
python scripts/aios_monitor.py assess --json --require-key persona_composite
python -m unittest discover -s tests -p 'test_aios_*.py'
```

The `--assert-keys` / `--require-key` flags are part of `must_produce` — each
tool exits nonzero if its JSON output lacks the required keys. Single
executable per line so verification gate parser accepts.

Pass criteria:

- 5 per-persona scores computable on real last-20 contracts
- persona_composite returned, distinct from governance_score
- monitor assess surfaces both axes
- doc explains orthogonality

## Stop Conditions

- `persona_audit_modifies_governance`: must remain separate axis
- `persona_audit_gates_dispatch`: V1 is advisory only
- `persona_axis_replaces_governance`: governance_audit.py stays — coexist
- `child_repo_scope_leak`
- `verification_gate_failed`

## Receipts

- `.aios/outbox/myworld/asc-0127.myworld.result.json`
- `python -m py_compile scripts/aios_persona_audit.py` passed.
- `python -m unittest tests/test_aios_persona_audit.py` passed 3/3.
- `python scripts/aios_persona_audit.py --window 20 --json --assert-keys
  wrapper_score,retriever_score,router_score,philosophy_score,sovereign_score,persona_composite`
  returned `persona_composite=0.45`, `wrapper_score=0.75`,
  `retriever_score=0.05`, `router_score=0.2`, `philosophy_score=0.25`,
  `sovereign_score=1.0`.
- `python scripts/aios_monitor.py assess --json --require-key persona_composite`
  passed and surfaced `persona_axis_advisory`.
- `python -m unittest discover -s tests -p 'test_aios_*.py'` passed 307/307.

## Work Packets

### WP-0127-A — codex@myworld implements persona audit

- target_agent: codex
- target_repo: myworld
- depends_on: none directly; ASC-0126 closure improves retriever_score signal
- brief: deterministic V1 of 5-persona scoring, monitor integration,
  doc with score-0 vs score-1 examples, tests. No source change to
  governance_audit.py. Recommendation-only.
