---
contract_id: ASC-0208
slug: uri-testbed-first-integration
status: proposed
created: 2026-05-20 KST
proposed_by: claude@myworld
escalation: founder direction 2026-05-20 — "AIOS는 Production으로 (sh, npm으로 packaging) 나와야하는 거고, Uri는 AIOS를 사용하여 개발해보는 테스트베드야. AIOS 관점에서는 별개인 것 알지 ?"
origin: ASC-0205 CC2 reframe (외부 product → AIOS sh installer). 분리된 uri testbed 작업이 본 contract로 옮겨짐.
goal: uri repository에 AIOS를 *소비자*로서 통합 — uri/.aios/ 와이어업, AIOS sh installer (ASC-0205 CC2') 가 끝난 후 첫 testbed 실증. AIOS 본체 완성의 후속이지 AIOS 본체의 일부가 아니다.
---

# ASC-0208 uri Testbed First Integration

DNA references: Invariant 6 (operator override — testbed는 본체와 분리),
Invariant 7 (privacy boundary — uri는 외부 product, 본 contract 가 uri 측
implementation 의 owner 가 아님).

## Frame

founder 2026-05-20 분리 명시:

| 개념 | 정체 |
|---|---|
| **AIOS** | sh/npm 으로 설치 가능한 *제품* (운영자 도구 패키지) |
| **uri** | AIOS를 *써서* 개발하는 testbed (소비자) |

따라서 본 contract는 *AIOS 본체 완성* 의 일부가 아니다. AIOS 본체 완성
(ASC-0205 CC1~CC6, 특히 CC2 sh installer) *완료 후* 의 첫 testbed 실증
이다.

## 사전 조건

- ASC-0205 CC2 (sh installer) closed — uri 가 표준 install 경로로 AIOS 를
  설치할 수 있어야 함.
- 또는 dev-mode 임시 wiring: uri 가 myworld 를 submodule 처럼 참조
  (sh installer 보다 먼저 가능, 그러나 testbed 가치는 동일).

## Required outcome

1. `uri/.aios/inbox/`, `uri/.aios/outbox/` 디렉터리 생성.
2. uri 가 AIOS 운영자 surface (`aios dispatch ...` 또는 `python scripts/aios_dispatch.py ...`) 를 호출해서 본 contract 의 sub-task 1건을 AIOS 의 5 OS 중 1곳에 발사.
3. result packet 이 outbox 에 떨어지고, uri 측 commit 1건이 그 result 를
   가져다 적용 (uri 코드 변경 1건 추적).
4. AIOS 측에서 ledger 1건 (cross-repo, repo: uri + myworld).

## Stop conditions

- 본 contract 는 uri 측 implementation 의 owner 가 아니다. uri 측 변경은
  uri 측 PR / contract 가 owner.
- uri 가 AIOS 본체를 *수정* 하려고 하면 멈춰라. testbed 가 본체를
  바꾸는 건 frame 위반. 본체 개선 사항은 ASC-NNNN 으로 새로 발의.

## Named Exit

closed when:
- `uri/.aios/inbox/` + `uri/.aios/outbox/` 존재,
- AIOS 5 OS 중 1곳에 발사된 sub-task result packet 1건 outbox,
- uri 측 commit 1건이 그 result 를 적용,
- ledger 1건 추가.

## Scope

repos: `uri` (consumer side, owner: codex@uri 또는 founder),
`myworld` (control plane operator surface — 호출되는 쪽).

## Notes

- 본 contract 는 sh installer (ASC-0205 CC2) 의 *후속* 이다. installer 가
  먼저 닫혀야 testbed 가 깨끗하게 실증된다.
- 이전 우리가 우연히 발견한 4 withdrawn auto-promoted contracts
  (ASC-0135/0137/0141 ...) 가 uri testbed 의 미래 발의 후보지만, *지금* 부터는
  본 contract 가 그것들의 자리를 차지한다. CC2' 이 closed 가 되기 전엔 본
  contract 도 proposed 상태로 대기.
