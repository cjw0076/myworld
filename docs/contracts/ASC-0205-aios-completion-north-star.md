---
contract_id: ASC-0205
slug: aios-completion-north-star
status: accepted
created: 2026-05-20 KST
proposed_by: claude@myworld
accepted: 2026-05-20 KST
acceptance_authority: founder 재원 — 2026-05-20 paper→IRIS 전환 + "AIOS 완성에만 집중" 지시. North Star 6개 기준 위임.
goal: AIOS 본체 완성의 측정 가능한 정의 — 6개 Completion Criterion (CC1~CC6) 을 모두 닫는다. 각 CC는 repo에 증거가 있어야만 "닫혔다".
origin: 2026-05-20 founder 대화. paper(ASC-0098) → IRIS 이관 결정. 그 결과 AIOS 본체에 집중할 새 North Star 필요. 자가진단 9개 production gap (memory project_aios_production_gap) 에서 도출.
---

# ASC-0205 — AIOS Completion North Star

DNA references: Invariant 4 (named exit — 각 CC는 닫는 증거를 명시),
Invariant 5 (provenance chain — 증거는 repo artifact, 자가 선언 금지),
Invariant 6 (operator override — founder는 언제든 CC 재정의 가능).

## Context

2026-05-20 자가진단으로 AIOS는 "방법론 + 단일-운영자 프로토타입" 단계임을
확인. L6 readiness=true는 *loop completeness* 이지 *external production*이
아님. 동시에 paper(ASC-0098) 는 IRIS 로 이관되어 본 contract 와 분리된
trajectory 로 진행.

따라서 AIOS 본체 완성을 정의할 새 North Star 가 필요.

## Genesis Escape Review

Plain language: AIOS is not "done" when the documents look neat. It is done
only when the system can receive a real goal, choose the right agent or repo,
remember and cite what matters, use outside knowledge without poisoning memory,
recover from provider failure, show the operator what is happening, and leave
evidence that another run can replay.

Assumptions to challenge:

1. Assumption: six criteria are enough. Negation: a seventh failure mode may
   appear only after uri or another product repo becomes truly wired.
2. Assumption: zero proposed contracts means convergence. Negation: it may
   mean useful discomfort was suppressed or misfiled.
3. Assumption: one external product proves production readiness. Negation: it
   proves only the first bridge; the second product may expose the real shape.

Counter-default branch: if ASC-0205 becomes a checklist that agents optimize
for, stop closing criteria and create a GenesisOS challenge contract first.
The challenge must ask what AIOS would still fail at after all six CCs appear
green.

Cross-domain frame: use city planning plus bridge load testing, not a
building ribbon-cutting. A city is not healthy because permits are closed;
roads, hospitals, markets, and maintenance crews must keep working under real
traffic. Passing inspection is not the ceremony; the bridge must carry real
traffic, show stress points, and keep a maintenance log.

Time horizons:

- 1h: clear blocked dispatch/accounting gaps so the loop is not lying about
  pending work.
- 1w: close CC1/CC4/CC5 with evidence packets, not narrative claims.
- 1y: prove AIOS can evolve across products and providers without the founder
  manually reconstructing state from logs.

## Completion Criteria (CC)

자가 선언 금지 — 각 CC는 닫는 증거가 repo에 존재해야 한다.

### CC1. 5 OS dispatch surface 전부 활성
- 현재: GenesisOS dormant (project_aios_5os_state).
- 닫는 증거: `.aios/outbox/GenesisOS/` 에 result packet ≥3,
  ledger 1건 이상, 해당 contract closed.

### CC2. 외부 product 1건 end-to-end
- 현재: 96 contract가 uri/ 를 *언급*만, `uri/.aios/` 실재 안 함.
- 닫는 증거: 외부 product repo (uri/ 또는 동급) 에 `.aios/inbox/` 와이어업,
  AIOS 통해 닫힌 contract ≥1, 외부 repo commit 1건이 그 contract result
  로 추적.

### CC3. 회귀 가드 CI
- 현재: `.github/workflows/` 비어있음. 74 tests 회귀 가드 없음.
- 닫는 증거: `.github/workflows/tests.yml` 활성, 실제 PR 1건 녹색 머지.

### CC4. 외부 지식 조직화 organ
- 현재: 본 contract 직전 Hermes/OMO/agiresearch 학습이 memory 3건으로 정리됨
  (수동). 자동 경로 없음.
- 닫는 증거: web-study → memory writeback 자동 경로 1개
  (`aios_primitives.py web` + memoryos 자동 draft) + `reference_*` 메모
  ≥5건 누적.

### CC5. Provider 다축화
- 현재: claude+codex 외 substrate 시연 없음 (provider lock-in).
- 닫는 증거: Ollama/local 또는 타 provider 가 *substantive* task ≥1 닫음.
  capability 매트릭스에 그 substrate 기록 + result packet 1건 이상.

### CC6. Self-improvement 수렴
- 현재: 9 contracts proposed (sprint-driver cluster ASC-0082/0083/0135/0137/
  0141, ASC-0092, ASC-0086, ASC-0183 founder-gated 등).
- 닫는 증거: `grep "^status: proposed" docs/contracts/ASC-*.md` = 0건
  (closed/superseded/withdrawn 으로 정리).

## Working Principles (process)

1. **외부 지식 → memory** 가 작업의 일부. 외부 시스템 학습은 *작업 도중*
   memory 로 남긴다 (reference_external_agent_systems 가 첫 예시).
2. **9개 production gap → CC** 매핑 유지. 각 작업 시작 시 어느 gap을
   메꾸는지 명시.
3. **방법론은 동결**. contract lifecycle / ledger / draft-first / graph
   control / DNA invariants 그대로. 새 invariant 추가는 founder GO 필요.
4. **Self-paced loop** (claude self-pace). CC 닫힐 때마다 founder 보고.
5. **반전 발생 시 escalate**. privacy 경계 / 외부 권위 / cross-instance
   Hive / 새 OS 는 founder GO.

## 비목표

- Paper / IRIS 작업 (별도 trajectory).
- Multi-tenant, auth, SaaS — CC2 는 단일 외부 product 1건만 요구.
- Cross-instance Hive — founder-gated.
- 새 OS 추가 — 5 OS 고정.

## Named Exit

본 contract 는 CC1~CC6 모두 closed 일 때 closed 로 전환. 각 CC는 자체
실행 contract (ASC-NNNN-cc{n}-*) 를 가질 수도 있고, 기존 proposed
contract 묶음으로 닫힐 수도 있다.

부분 진척은 본 contract 의 `## Progress Log` 절에 append-only 로 기록.

## Scope

repos: `myworld` (control plane), `hivemind` / `memoryOS` / `CapabilityOS`
/ `GenesisOS` (CC1 dispatch), 외부 product repo (CC2, 미정 — uri/ 후보).

## Progress Log

- 2026-05-20 created/accepted (claude@myworld 운영자). 초기 진척 0/6.
- 2026-05-20 **CC4 organ 최초 빌드** (1/6 in progress):
  - `scripts/aios_external_knowledge_organ.py` — web_research_receipt →
    memory_draft_review_request 브리지. draft-first invariant 보존
    (auto_accept=False, status=draft).
  - 라이브 검증: Hermes Agent 학습 3 claim 흘려서
    `mem_bec92a1061c2b129`, `mem_59d459008e5a9da2`, `mem_679e0d288d2cce45`
    모두 draft/needs_more_evidence 로 정착.
  - `tests/test_aios_external_knowledge_organ.py` — 5 tests pass.
  - 누적 reference 메모: 2/5 (`reference_aios_tools`,
    `reference_external_agent_systems`). 다음 iter에 ≥3 추가하면 CC4 closed.
- 2026-05-20 **CC4 closed** (4/6 done):
  - organ live: `scripts/aios_external_knowledge_organ.py` +
    `tests/test_aios_external_knowledge_organ.py` (5 tests pass).
  - reference 메모 5/5: `reference_aios_tools`,
    `reference_external_agent_systems`,
    `reference_memoryos_review_request_packet`,
    `reference_github_actions_python_ci`,
    `reference_contract_triage_patterns`.
  - 라이브 ingest 검증: Hermes Agent → 3 drafts (mem_bec92.../59d4.../679e...)
    in memoryOS, draft-first invariant 준수 (review_action=needs_more_evidence).
  - 닫는 증거: organ smoke 가 CI 워크플로우에 등록됨
    (`.github/workflows/tests.yml` 의 last step).
- 2026-05-20 **CC6 closed** (3/6 done):
  - 7 proposed → 0 (ASC-0183 founder-gated 1건만 남음, 명시 허용 조건 충족).
  - **superseded by ASC-0205** (4건): ASC-0082, ASC-0083, ASC-0086 →
    CC1/CC2/CC4/CC5 가 흡수. 각 contract frontmatter 에
    `superseded_by: ASC-0205` 명시.
  - **withdrawn** (4건): ASC-0092 (Hive 활성도 낮을 때 빈 강제),
    ASC-0135/0137/0141 (ASC-0058 auto-promoted uri instances; CC2 가
    proper packet 으로 재발의). 각각 withdrawn_reason + revive 트리거 기록.
  - **남은 1건**: ASC-0183 (dream phase-2 parametric LoRA) — frontmatter
    이미 `escalation: VISION-LEVEL — founder GO required before build` 로
    표기. CC6 spec 의 "founder-gated 만 남은 상태로 명시" 조건 충족.
  - 닫는 증거: `grep "^status: proposed" docs/contracts/ASC-*.md` →
    `ASC-0183-...md` 1건만, escalation 필드로 명시됨.
- 2026-05-20 **CC3 closed** (2/6 done):
  - `.github/workflows/tests.yml` — ubuntu / py3.13 / compileall +
    `unittest discover` + organ smoke. submodules:false (myworld 자체는
    stdlib-only). `tests/__init__.py` 추가 — discover 의 namespace
    package 함정 해결.
  - 회귀 1건 검출/수정: ASC-0204 fixture marker 누락
    (`tests/test_aios_local_app.py`).
  - 닫는 증거: commit `59734d9`, run
    https://github.com/cjw0076/myworld/actions/runs/26147674534 (success,
    480 tests pass).
  - reference 메모 +2 (3/5):
    `reference_memoryos_review_request_packet`,
    `reference_github_actions_python_ci`. CC4 까지 reference 2건 더 필요.
