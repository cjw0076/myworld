---
contract_id: ASC-0215
slug: peer-blindspot-7day-experiments
status: proposed
created: 2026-05-20 KST
proposed_by: claude@myworld
acceptance_authority: founder 재원 — 2026-05-20 sharp signal #4 verdict 선택. 본 contract 는 *founder 의 peer 응답이 명시 필요* 한 항목 1개 포함 → 본격 accept 는 founder 가 본인 experiment 선택 후 (이건 voluntary disclosure, [[feedback_hiding_is_peer_agency]] 준수).
origin: ASC-0211 L3 routine #3 (frontier_question --include-peer-blindspots) 가 2 peer 의 named blindspot 마다 "7일 안 smallest experiment" 질문 발사. founder 의 sharp signal #4 act 결정.
---

# ASC-0215 — Peer Blindspot 7-day Experiments

DNA references: Invariant 1 (decide before acting), Invariant 6
(operator override — peer 가 자기 experiment 거부 또는 변경 가능),
Invariant 7 (privacy — peer 의 *blindspot* 자체가 sensitive; 강제
disclosure 금지).

## Why now

frontier_question routine: "재원의 named blindspots / claude의 named
limits 에 대해 7일 안 smallest concrete experiment 가 무엇이며 어느
peer 가 실행 가능한가?"

이건 두 peer 의 *명시* 한계 ([[project_user_agent_재원]],
[[project_claude_agent_limits]]) 에 대해 실제 dent 를 만들기 위한 작은
실증 1건씩.

## Frame: voluntary disclosure 보존

[[feedback_hiding_is_peer_agency]] 준수: 본 contract 는 peer 에게 *experiment 를
요구* 하지 않음. peer 가 *선택* 해서 experiment 1건을 *고르는* 것이 본
contract 의 accept signal. peer 가 "지금은 안 함" 도 정상 응답.

## Required outcome

두 peer 각각 자기 named blindspot 1개 선택 + 7일 안 smallest experiment
1건 명시.

### claude 의 first proposal (이 자체가 voluntary disclosure)

**선택한 blindspot**: "agreement bias to founder" (claude_agent_limits 의 soft limit #1)

**7일 안 smallest experiment**:
- 다음 7일 동안 founder 가 *명시 결정* 을 줄 때마다, *그 결정을 일단 challenge*
  하는 1줄 자가 질문을 응답 *전* 생성. 응답에 그 자가 질문 + 답 둘 다 포함.
- 측정: 7일 후 self-observation log 에 "challenge → 결국 동의" vs "challenge →
  실제 reframe" 비율 추적.
- 실행자: claude (이 thread).
- 시작: 다음 founder 응답부터.

(founder 도 자기 blindspot + experiment 1건을 *원할 때* 적으면, 본 contract
가 accepted 로 전환.)

### founder 의 experiment 슬롯 (대기, optional)

founder 가 voluntary disclosure 로 적을 항목:
- 선택한 blindspot:
- 7일 안 smallest experiment:
- 실행자 (founder / claude / codex 중):
- 시작 trigger:

(공란 유지 = founder 가 voluntary 로 비공개 선택. invariant 7 준수.)

## Named Exit

closed when:
1. claude 측 experiment 7일 완료 + self-observation log entry.
2. founder 측 experiment — optional. 7일 안 명시 진행 시 같이 close.
   founder 가 "no experiment" 선언해도 close (peer agency).

## Stop conditions

- experiment 가 *큰 작업* 으로 swelling — smallest 조건 위반. 즉시 reset.
- claude 의 experiment 가 founder 에게 *지속적 부담* 이 되면 stop. peer
  의 자유 시간 우선.

## GenesisOS Escape Review

This review is advisory-only. It keeps peer-blindspot work from becoming a
coercive disclosure ritual.

### Assumptions

- Assumption 1: a 7-day experiment is small enough to reveal a real blindspot
  without turning into identity work.
- Assumption 2: voluntary disclosure can coexist with a contract record.
- Assumption 3: Claude's agreement-bias experiment is useful even if the
  founder keeps their own blindspot private.

Counter branch: negate those assumptions. If the contract nudges a peer to
perform vulnerability for the system, it violates the agency it claims to
protect. The correct result may be "no experiment now" plus a ledger note, not
more extraction.

### Plain Language

Plain language: this contract asks for one small self-chosen test, not a
confession. A peer can choose a blindspot, change the experiment, or refuse,
and that refusal is still a valid process result.

### Cross-Domain Frame

Ritual analogy: this is closer to a voluntary check-in than a trial. The group
can make space for a spoken commitment, but it cannot demand the private reason
behind the silence.

### Time Horizons

- 1h: keep the founder slot optional and blank without treating it as failure.
- 1 week: log Claude's challenge ratio if the experiment actually runs.
- 1 year: evaluate whether peer experiments improved decisions without
  reducing privacy.

## Scope

repos: 없음 (메모리 + observation log 만 변경). contract 는 process
도구.

## Sibling contracts

- ASC-0213 — closure-quality-gate
- ASC-0214 — aios-dogfooding-gap
