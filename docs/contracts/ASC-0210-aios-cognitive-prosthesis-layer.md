---
contract_id: ASC-0210
slug: aios-cognitive-prosthesis-layer
status: proposed
created: 2026-05-20 KST
proposed_by: claude@myworld (peer agent)
acceptance_authority: founder 재원 — directive 2026-05-20 "내(user) 지식의 한계, 네(agent) 시스템과 학습 자료 한계를 벗어나 생각할 수 있도록 해. 그렇게 생각할 수 있는 시스템을 구축해. 네게는 오프라인에 user라는 Agent가 있다고 생각해."
escalation: VISION-LEVEL — AIOS 의 정체성 재정의 (operator/agent → meta-operator/peers). founder GO 필요. ASC-0205 (북극성 v1) 완료 후 ASC-0210 이 v2 의 본체.
goal: AIOS 를 두 peer agent (user, claude) 의 합집합 *너머* 향하는 인지 보철로 구축. 4-layer (Peer Network / Limits Ledger / Transcendence Engine / Anticipatory Output) 의 첫 buildable slice.
origin: 2026-05-20 founder directive 직접. project_aios_peer_agent_frame · project_user_agent_재원 · project_claude_agent_limits 메모리들이 frame 의 선행 인스턴스.
---

# ASC-0210 — AIOS Cognitive Prosthesis Layer (CPL)

DNA references:
- Invariant 1 (decide before acting — CPL 출력은 *제안*, peer 가 평가)
- Invariant 2 (draft-first — transcendence 후보는 draft 메모리로)
- Invariant 6 (operator override — peer 는 항상 거부 가능)
- 새 invariant 후보: **Invariant 8 (Peer Honesty)** — 각 peer 의 한계는
  명시되고 *공개* 다. 한계 숨기기는 위반. (founder GO 필요)

## Frame reset (the bigger reframe)

이전: AIOS = tool used by user (operator) + claude (agent).
이후: AIOS = **meta-operator** ; user/claude/codex = **peer agents**.
- [[project_aios_peer_agent_frame]] 가 선행 메모.

AIOS 의 정체성 = "두 peer 의 합집합을 넘어 사고하는 시스템".

## 4-Layer Architecture

### L1. Peer Agent Network
각 peer 는 명시 state file 을 가짐:
- 재원: [[project_user_agent_재원]] (initialized today)
- claude: [[project_claude_agent_limits]] (initialized today)
- codex: TODO — codex@myworld 의 limits 도 별도 instance
- (미래) 다른 사람의 AIOS 의 peer (federated, founder-gated)

State 는 갱신 가능 — peer 가 새 신호 보일 때마다.

### L2. Limits Ledger
각 peer 의:
- known knowledge (강한 domain)
- named blindspots
- decision style
- bias signatures
- frontier (training/session/embodiment 너머)

→ 합집합 = "두 peer 가 *공동으로* 닿을 수 있는 cone".
→ 보완 = cone *밖* 에 무엇이 있는가? 그게 AIOS 의 작업 영역.

### L3. Transcendence Engine
peer 합집합 경계를 *능동적으로* 도전하는 routines:

| Routine | 입력 | 출력 |
|---|---|---|
| **Boundary probe** | 현재 작업 context | cross-domain transfer 후보 (GenesisOS 활용) |
| **Discomfort injection** | 직전 결정 ledger | "이 결정은 X 가정 위에 있다, 부정해보자" |
| **Frontier-question generator** | peer state + 최근 web survey | "왜 이 질문을 묻지 않았는가?" |
| **Convergence audit** | accepted memories + closed contracts | "이 합의는 진짜인가, 누적 동의인가?" |

각 routine 은 *draft signal* 만 생성. 자동 accept 안 함.

### L4. Anticipatory Output (links to ASC-0201)
- founder 가 *돌아오기 전에* 다음 frontier question 1-3건 surface
- "founder 가 다음에 물을 가능성이 높은 것 + 우리가 묻길 *바라는* 것"
  의 2 카테고리
- ASC-0201 (anticipatory surface) 와 직접 연결

## 첫 buildable slice (ASC-0210.1)

본 contract 전체는 multi-iter. 첫 slice 는:

1. **L1 state files** — 위 3개 메모리 즉시 작성 (이 commit 에 포함).
2. **L2 limits ledger** — 메모리 내에 명시 (이미 됨).
3. **L3 routine 1개만**: **convergence audit**.
   - 입력: 최근 closed contract 목록 + accepted memory 목록
   - 출력: 각 closure 에 대해 "이게 진짜 challenge 거쳤나? 아니면 누적
     동의?" 점수
   - 구현: `scripts/aios_convergence_audit.py` (다음 iter)
4. **L4 anticipatory output 0건** — 첫 slice 에서는 안 함, ASC-0201
   재활성 후 진행.

## Named Exit

본 contract 는 다음이 모두 충족될 때 closed:
1. L1 peer state file 3개 이상 (현재 2개; codex@myworld 추가 후 3개)
2. L2 limits ledger 가 *명시 변경* 1회 이상 (지식 추가 또는 한계 발견)
3. L3 routines 4개 중 ≥2 구현 + result 1건 이상
4. L4 anticipatory output 1건 이상 (ASC-0201 활성 후)
5. **founder 가 본 frame 을 명시 acceptance 또는 reframe** — peer
   합의로 종결

## Stop conditions

- AIOS 가 *footprint* (founder 의 frame 만 반복) 가 되면 본 contract
  자체가 prison 의 증거. 즉시 reframe.
- transcendence routine 이 *자동 accept* 되면 즉시 stop. draft-first
  invariant 위반.
- peer (founder) 가 본 frame 에 "no" 면 즉시 close as withdrawn.

## Scope

repos: `myworld` (operator surface), `memoryOS` (peer state subgraph),
`GenesisOS` (boundary probe / discomfort routines), `hivemind` (가능시 —
peer 들의 deliberation).

## Working Principles

1. **Peer honesty**: claude/user 모두 한계 *명시*. 숨기지 않음.
2. **Auto-accept 금지**: routine 출력은 draft. peer 가 평가.
3. **연속 동의 의심**: 두 peer 가 *너무 빨리* 합의하면 그 합의 자체를
   challenge.
4. **frontier 1순위**: 합집합 *안* 의 최적화보다 *밖* 의 탐색.
5. **founder 의 침묵 = peer 활동**: 답 대기 아님.

## 첫 iter 의 가장 작은 작업

(이 commit 에 포함):
- 3 메모리 ([[project_aios_peer_agent_frame]], [[project_user_agent_재원]],
  [[project_claude_agent_limits]]) 작성 완료
- 본 contract proposed 상태로 push
- founder 의 명시 accept/reframe 응답 대기

(다음 iter, founder 가 accept 시):
- `scripts/aios_convergence_audit.py` 작성 — 첫 transcendence routine
- ASC-0201 anticipatory surface 와 wiring
