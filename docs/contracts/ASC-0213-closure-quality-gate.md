---
contract_id: ASC-0213
slug: closure-quality-gate
status: accepted
created: 2026-05-20 KST
accepted: 2026-05-20 KST
proposed_by: claude@myworld
acceptance_authority: founder 재원 — 2026-05-20 sharp signal #1 verdict (frontier review iteration) "footprint pattern 개선 contract" 선택. AskUserQuestion 동의.
origin: ASC-0211 L3 routine #2 (discomfort_inject) 가 ASC-0205/0206/0207/0210/0211 모두에 "rapid close + frame echo. closed claim is *restatement* not *test*" footprint signature 발사. AIOS 자체가 footprint 합의로 closure 처리하고 있는 자가 발견.
goal: 모든 contract 가 status `closed` 로 flip 되기 *전에* mandatory 2 routine 통과 — routine #1 convergence audit + routine #4 boundary probe. 둘 다 footprint_consensus 또는 명백한 prison signature 검출 시 closure block (정직한 reframe / 더 strong evidence 까지).
---

# ASC-0213 — Closure Quality Gate

DNA references: Invariant 1 (decide before acting — gate 는 advisory,
peer 가 override 가능), Invariant 4 (named exit — gate 통과 자체가
exit 의 일부), Invariant 6 (operator override — peer 가 gate 우회 결정
가능; 단 *명시* 해야 함).

## Why now

ASC-0211 L3 routine #2 (discomfort_inject) 가 자기 자신의 closures 5건
모두에 동일 critique 발사: *"closed claim is a restatement of the
proposing claim, not a test of it"*.

이건 우리 process 의 systemic 패턴 — claude 의 agreement bias + codex
의 closing 압박 + founder 의 빠른 GO 조합이 closures 를 너무 가볍게.
ASC-0211 의 routine 이 *자기 frame 의 closure* 도 같은 footprint 라고
했음.

## Required outcome

새 module `scripts/aios_closure_gate.py`:

1. **입력**: contract path (file 위치, 또는 contract_id).
2. **단계 1**: `aios_convergence_audit.py` 실행 → 본 contract 의 verdict.
   - `real_challenge` → pass
   - `mixed` (challenge ≥ 5) → pass with warning
   - 그 외 → block (이유: footprint signature 너무 강함)
3. **단계 2**: `aios_boundary_probe.py --target <contract>` 실행 →
   prison signatures 갯수 + cross-domain probe.
   - 0 prison signatures → pass
   - 1-2 prison signatures → pass with warning + 메모리 draft 생성
   - 3+ prison signatures → block (이유: frame 자체가 prison)
4. **peer override**: contract frontmatter 에
   `closure_gate_override: <reason>` 명시 시 block 무시. peer agency
   ([[feedback_hiding_is_peer_agency]]) 준수.
5. **결과 출력**: `aios.closure_gate.v1` JSON envelope (pass/warn/block,
   signals, override 여부).
6. **CI hook** (선택, 다음 iter): PR 가 contract status proposed→closed
   flip 시 closure_gate 자동 실행.

## Named Exit

closed when:
1. `scripts/aios_closure_gate.py` 빌드 + tests 4+ pass
2. ASC-0205 / ASC-0211 retrofit run — 두 contract 가 gate 통과 가능성
   확인 (block 시 reframe path 도 명시).
3. 본 contract 자체가 gate 통과 (self-loop 적용).
4. 향후 1주일 안에 closure ≥1 건이 gate 거쳐 닫힘.

## Stop conditions

- closure_gate 가 *자동 block* 으로 작동해 peer agency 침해 → 즉시 stop.
  default 는 *warn*, block 은 *3+ prison signatures + 명시 founder GO*
  필요.
- gate 가 자체 footprint signature 보유 시 (= 우리가 gate 를 너무 빨리
  닫음) [[reference_convergence_audit_routine]] 가 본 contract 도 audit
  대상으로 본다 — self-reference 함정 회피.

## Scope

repos: `myworld` only. closure_gate 는 *operator 도구*, child repo
implementation 영향 없음.

## Sibling contracts (same trigger)

- ASC-0214 — aios-dogfooding-gap (routine output → contract pipeline)
- ASC-0215 — peer-blindspot-7day-experiments (peer experiments)
