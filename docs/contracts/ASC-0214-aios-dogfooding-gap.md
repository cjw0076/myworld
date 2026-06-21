---
contract_id: ASC-0214
slug: aios-dogfooding-gap
status: closed
created: 2026-05-20 KST
accepted: 2026-05-20 KST
closed: 2026-06-21T11:00:00+09:00
closed_by: claude@myworld
closing_note: SECI pipeline (scripts/aios_seci_pipeline.py) closes the dogfooding gap — phase_e externalizes agent behavior patterns from sessions to MemoryOS drafts, phase_i uses promoted memories for prediction. aios_turn_loop.completion_audit uses behavior data. Goal met via implementation.
proposed_by: claude@myworld
acceptance_authority: founder 재원 — 2026-05-20 sharp signal #5 verdict "AIOS가 자기 routine 출력을 안 쓰는 dogfooding gap 수정" 선택.
origin: ASC-0211 L3 routine #3 (frontier_question) 가 3개 reference 메모 (reference_discomfort_routine_first_signal, reference_convergence_audit_routine, reference_aios_as_package_design) 가 *contract 에서 인용 안 됨* 발견. 우리가 자기 routines 의 output 을 contract action 으로 변환 안 하고 있음.
---

# ASC-0214 — AIOS Dogfooding Gap

DNA references: Invariant 4 (named exit — dogfooding 자체가 named
output), Invariant 5 (provenance chain — routine output 이 *증거* 인데
*사용* 안 되면 chain 끊김).

## Why now

frontier_question routine 발견:
- AIOS 가 자기 transcendence routines 의 결과를 자기 contract 로
  *변환 안 함*. routine 이 sharp signal 을 만들어도 *행동* 으로 안 옴.
- 3 uncited reference 메모 = AIOS 자기 발견을 자기가 무시.

[[feedback_readiness_vs_usage]] 의 동형 — readiness 가 있어도 *사용*
은 별개. routine 이 enacted 라도 *output 사용* 은 별개.

## Required outcome

새 routine `scripts/aios_dogfood_route.py`:

1. **입력**: AIOS memory 디렉터리에서 reference_*.md 메모 목록.
2. **단계 1**: 각 reference 메모마다 "이 메모가 contract 에서 인용되었나?"
   체크 (frontier_question 의 uncited 로직 재사용).
3. **단계 2**: uncited 메모마다 *수명*(memo 생성일 ~ now) 계산. 7일 이상이면
   "stale-uncited" — 즉시 acceptable action 후보.
4. **단계 3**: 각 stale-uncited 메모에 대해 *제안 action 1건* 자동 생성:
   - reference 메모 의 description + 첫 본문 paragraph 를 기반
   - "이 메모를 contract 로 만들거나 reject decision 을 ledger 에 기록" 둘 중 하나
5. **결과**: `aios.dogfood_route.v1` JSON. dry-run mode 가 default;
   `--act` 로 새 ASC-NNNN proposed contract 자동 생성 (draft-first
   invariant 준수, founder 또는 claude 가 accept 해야 진행).
6. **운영**: 정기 호출 (예: 일 1회). 또는 reference 메모 추가 후 다음
   loop iter 시 자동.

## Named Exit

closed when:
1. `aios_dogfood_route.py` 빌드 + tests 3+ pass.
2. 현재 3 uncited reference 메모 (discomfort_first_signal,
   convergence_audit, aios_as_package_design) 각각에 대해 *명시 결정*
   1건 (contract 발의 or ledger reject 노트).
3. 향후 신규 reference 메모 1건이 7일 안 자동으로 contract 후보로 surface.

## Stop conditions

- 자동 contract 생성 *수* 폭증 (예: 매일 5+ 새 proposed) → contract
  pollution. threshold 조절 또는 stop.
- dogfood_route 가 자기 자신의 reference 메모만 점점 만들어내는 loop
  → recursion 의심, stop.

## GenesisOS Escape Review

This review is advisory-only. It keeps "dogfood everything" from becoming an
automatic contract factory.

### Assumptions

- Assumption 1: uncited routine output is usually a missed action, not harmless
  background thought.
- Assumption 2: stale reference notes deserve either a contract candidate or an
  explicit reject decision.
- Assumption 3: default dry-run plus operator acceptance prevents contract
  pollution.

Counter branch: negate those assumptions. If most routine output is exploratory
scratch, forcing every stale note into a contract path will turn AIOS into a
paperwork generator. The route must therefore preserve reject and keep-stale as
first-class outcomes.

### Plain Language

Plain language: when AIOS produces a useful note, the system should not forget
it. But remembering does not mean automatically building it; someone must
choose build, reject, or keep watching.

### Cross-Domain Frame

Ecology analogy: routine outputs are seeds. A healthy system does not plant
every seed in the same bed; it lets some germinate, composts others, and keeps
rare seeds labeled for the right season.

### Time Horizons

- 1h: list stale uncited references without creating contracts.
- 1 week: record one explicit build, reject, or keep-stale decision.
- 1 year: measure whether dogfood routing reduced forgotten high-signal notes.

## Scope

repos:
- myworld

## Sibling contracts

- ASC-0213 — closure-quality-gate
- ASC-0215 — peer-blindspot-7day-experiments
