# Agent Behavior Patterns — 벤치마크 자산화

> 작성: 2026-06-19 | 출처: SWE-bench Pro, τ-bench, TOUCAN, AgentBench, GAIA, WebArena, OpenDev 논문 직접 독해

---

## 1. 벤치마크 비교표

| 벤치마크 | task 유형 | action space | 주요 tool | SOTA (2026) | 특징 |
|----------|-----------|--------------|-----------|-------------|------|
| **SWE-bench Verified** | GitHub 이슈 패치 | 코드 생성/편집 | grep, edit, bash, git | ~80%+ (Claude Code) | trajectory 단계: Localize → Edit → Verify |
| **τ-bench (Tau-bench)** | 고객 서비스 멀티턴 | domain API 호출 | 도메인 전용 API | GPT-4o < 50%, pass^8 < 25% | 신뢰성 지표 pass^k; multi-turn 상태 추적 |
| **AgentBench** | OS/DB/웹/게임 8종 | 환경별 다양 | bash, SQL, browser | 환경마다 극단적 격차 | 진단 도구; aggregate 점수 무의미 |
| **GAIA** | 실제 assistant 태스크 | 웹/멀티모달/추론 | WebSearch, API | Sonnet 4.5: 74.6% | 인간에게 쉬움, 모델에게 어려움 |
| **WebArena** | 812 웹 네비게이션 | DOM 상호작용 | click, fill, search | 61.7% (IBM CUGA) | 인간 78.24%; 브라우저 자동화 |
| **OSWorld** | 369 cross-app GUI | 키보드/마우스 | file I/O, GUI | 12.24% (SOTA) | 인간 72.36%; 컴퓨터 제어 |
| **TOUCAN** | 495 MCP 서버, 2000+ tool | 멀티스텝 도구 호출 | 모든 MCP 도구 | SFT 소형 모델이 대형 초과 | 1.5M 트레젝토리; 최대 3-tool 체인 |

---

## 2. 실제 Tool 사용 패턴 (SWE-bench Pro 실측값)

### Claude Sonnet 4.5 vs GPT-5 비교 (코딩 에이전트)

| tool 행동 | Claude Sonnet 4.5 | GPT-5 |
|-----------|-------------------|-------|
| keyword search | 7,002 회 | 6,499 회 |
| test 실행 | **5,942 회** | 585 회 |
| 소스 편집 | 5,217 회 | 4,983 회 |
| file range view | 5,974 회 | 5,997 회 |
| search 실패 | **46 회** | 2,748 회 |
| script 실행 실패 | **47 회** | 759 회 |
| read 실패 | **23 회** | 994 회 |
| 편집 시작 시점 | 트레젝토리 35% 지점 | 50% 지점 |
| 편집 완료 시점 | 62% 지점 | — |
| 편집 당 verify 횟수 | **3회** | 1회 |
| cleanup (git 등) 비율 | 6.2% | ~0% |
| verify 없는 트레젝토리 | 드묾 | **~40%** |

**핵심 인사이트:**
- Claude는 "탐색-편집-검증-정리" 루프를 완전히 돌린다
- GPT-5는 컨텍스트 수집 후 편집, 검증 생략 → tool call 실패율 20%
- 실패 수가 성공 전략의 핵심 시그널: 낮을수록 더 안정적인 에이전트

### 전형적인 성공 sequence (코딩 에이전트)
```
[Search] 관련 파일/함수 찾기
    ↓
[Read] 파일 내용 확인 (range view)
    ↓
[Search] 버그/패턴 확인
    ↓
[Edit] 수정 (패치 생성)
    ↓
[Bash: test] 검증 (3회 반복 허용)
    ↓
[Bash: git] 정리
```

### 전형적인 실패 sequence
```
[Search] (실패 2,748회 → 잘못된 쿼리 반복)
    ↓
[Edit] 컨텍스트 불충분한 상태에서 편집
    ↓
[Bash: test] 없거나 1회만
    ↓
종료 (검증 미완)
```

---

## 3. 실패 모드 TOP 5

### F1. Step Repetition (17.14%)
동일 tool call을 반복. 탈출 조건 없이 무한 루프 진입.
- **대응:** doom-loop detection: N회 동일 호출 시 컨텍스트 재구성 또는 사용자 에스컬레이션

### F2. Reasoning-Action Mismatch (13.98%)
생각은 "파일 A를 편집해야 한다"지만 실제로 파일 B를 편집하거나 아무것도 안 함.
- **대응:** action 전후 의도-행동 일치 검증; structured output으로 강제

### F3. Tool Call Failure Cascade
tool 실패 후 fallback 없이 오류 상태 누적. 특히 apply_patch 실패(GPT-5: 20%).
- **대응:** 각 tool에 fuzzy retry (file edit: 9-pass fuzzy matching), 실패 시 대안 경로

### F4. Verification Skip (~40% in GPT-5)
편집 후 테스트 없이 완료 선언. 실제로 패치가 broken.
- **대응:** post-edit mandatory verify step; hooks로 강제

### F5. Context Rot / Instruction Fade
긴 세션에서 초기 지시 망각 → 목표 drift.
- **대응:** event-driven system reminder injection; adaptive compaction 5단계; dual-memory (episodic + working)

---

## 4. 성공 패턴 TOP 5

### S1. Localize → Edit → Verify 3단계 완전 루프
성공 에이전트의 공통: 탐색 충분히 → 편집 → 즉시 검증. 단계 생략 없음.

### S2. 조기 편집 시작 (35% 시점)
Claude 패턴: 충분한 파악 후 빠르게 편집 → 검증 시간 확보.
GPT는 50% 이후 편집 시작 → 검증 시간 부족.

### S3. 반복 검증 (편집 당 3회)
1회 verify로 통과 안 되면 포기하지 않고 재수정 → 재검증 루프.

### S4. 실패 허용 + 복구
검색 실패 46회(Claude) vs 2748회(GPT): Claude는 실패 후 다른 쿼리로 전환.
GPT는 같은 실패 반복.

### S5. 정리 단계 (cleanup, 6.2%)
작업 완료 후 git, 불필요 파일 제거. 환경 상태 정상화.
장기 세션에서 누적 오염 방지.

---

## 5. Agent Harness 시스템 설계 — 핵심 컴포넌트

### 5-1. 하네스 구조 (6-phase per iteration)

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT HARNESS                              │
│                                                                 │
│  ① pre-check + compaction   → 메모리 압력 관리                   │
│  ② thinking (optional)      → chain-of-thought                  │
│  ③ self-critique (optional) → 행동 전 반성                       │
│  ④ action                   → LLM call (full tool access)        │
│  ⑤ tool execution           → registry dispatch + safety check   │
│  ⑥ post-processing          → state persist + continuation 결정  │
│                                                                 │
│  [Plan Mode: read-only subagent] ↔ [Normal Mode: full access]   │
└─────────────────────────────────────────────────────────────────┘
```

### 5-2. Tool Registry 설계 원칙
- **최적 tool 수: ~10개** (50개 → 모델 혼란, context 낭비)
- Lazy MCP tool 등록 (런타임 확장) + Eager agent 초기화
- 각 tool에 명확한 schema + description (모델이 언제 쓸지 판단)
- Tool offloading: 2000줄+ 출력 → filesystem, on-demand 접근

### 5-3. 컨텍스트 관리 5전략

| 전략 | 설명 |
|------|------|
| **Compaction** | 5단계 progressive summarization (context 70% 도달 시) |
| **Tool-call offloading** | 대용량 결과 filesystem 저장 |
| **Progressive disclosure** | 관련 시점에만 tool/instruction 노출 |
| **Dual-memory** | episodic (전체 세션) + working (현재 반복) |
| **Event-driven reminder** | 반복 실패 시 타깃 guidance inject |

### 5-4. Safety 5중 방어

```
① 프롬프트 가드레일       (soft, 무시될 수 있음)
② schema 제한            (Plan Mode: read-only tool만)
③ 런타임 approval gate   (위험 명령 사전 확인)
④ tool-level validation  (rm -rf, DROP TABLE 패턴 감지)
⑤ user lifecycle hooks   (pre-tool-call, post-edit, pre-commit)
```

### 5-5. 복구 패턴

| 패턴 | 구현 |
|------|------|
| **Doom-loop detection** | 동일 tool call N회 → 재구성 or 에스컬레이션 |
| **Stale-read detection** | 파일 외부 수정 감지 → 재로드 강제 |
| **Fuzzy file edit** | 9-pass 점진적 매칭 (정확한 라인 번호 불필요) |
| **Ralph loop** | 세션 종료 시 원본 프롬프트 재주입 → 연속성 |
| **Subagent isolation** | toggle 대신 분리된 schema로 별도 에이전트 |

---

## 6. Multi-Agent 아키텍처 패턴

### 6-1. 주요 패턴 3종

```
[Orchestrator-Worker]          [Pipeline]              [Debate]
    Orchestrator               A → B → C → D           Agent1
    /    |    \                (직렬 처리)              Agent2  → Judge
  W1    W2    W3                                       Agent3
(병렬 전문가)                                          (AutoGen 패턴)
```

### 6-2. 프레임워크 선택 기준 (2026)

| 프레임워크 | 강점 | 약점 | 언제 쓰나 |
|-----------|------|------|-----------|
| **LangGraph** | 최대 제어, 그래프 구조, observability | 복잡한 setup | 프로덕션, 복잡한 분기 |
| **CrewAI** | 빠른 프로토타입, role 기반 | 프로덕션 observability 부족 | PoC, 마케팅 자동화 |
| **AutoGen / AG2** | 멀티에이전트 debate, async-first | research 중심 | 검증/비판 루프 |
| **OpenAI Agents SDK** | 공식 지원 | 벤더 종속 | GPT 기반 |

### 6-3. AIOS에 적용할 패턴
- myworld = **Orchestrator** (계약 발행, 상태 추적)
- hivemind worker = **Executor** (실행, 검증)
- GenesisOS = **Debate/Critic** (비판, 발산)
- MemoryOS = **State store** (컨텍스트 지속성)

---

## 7. AkashicRecord에 흡수해야 할 데이터 소스

| 데이터셋 | URL | 크기 | 활용 방법 |
|---------|-----|------|-----------|
| **TOUCAN-1.5M** | `Agent-Ark/Toucan-1.5M` (HuggingFace) | 1.5M trajectories | MCP tool 사용 패턴, 실제 tool-chain 학습 |
| **τ-bench / τ²-bench** | `HuggingFaceH4/tau2-bench-data` | 멀티턴 대화 | 고객서비스 agent 상태추적 패턴 |
| **τ-bench synthetic** | `fuvty/tau-bench-synthetic` | retail 180 + airline 100 | 도메인별 tool sequence |
| **PostTrainBench-Trajectories** | `aisa-group/PostTrainBench-Trajectories` | full trace.txt | bash/edit/search 실제 sequence |
| **SWE-smith** | github.com/SWE-bench/SWE-smith | 대규모 코딩 trajectories | 코딩 에이전트 성공/실패 패턴 |
| **Coding-Agent-Github-2025** | `DeepNLP/Coding-Agent-Github-2025-Feb` | GitHub 실제 이슈 | 코딩 행동 패턴 |

---

## 8. AIOS 예측 모델에 적용할 인사이트

### 8-1. AkashicRecord 분류 개선
현재 분류(code/docs/data/personal)는 너무 거칠다. 벤치마크 분석 결과 필요한 분류:

```python
FINE_CATEGORIES = {
    "code_localize":  ["Grep", "Glob", "Read", "Bash:find"],
    "code_edit":      ["Edit", "Write", "NotebookEdit"],
    "code_verify":    ["Bash:test", "Bash:pytest", "Bash:npm"],
    "code_cleanup":   ["Bash:git", "Bash:rm"],
    "research":       ["WebSearch", "WebFetch", "Read"],
    "orchestrate":    ["Agent", "Task", "Workflow"],
    "user_loop":      ["AskUserQuestion", "Skill"],
}
```

### 8-2. 시퀀스 패턴 예측 (단순 빈도 → 전이 확률)
현재: 개별 tool 빈도만 봄
필요한 것: **tool 전이 행렬** — 이전 tool이 주어졌을 때 다음 tool 확률

```
P(Edit | Search) = 0.42   # Search 후 Edit 가능성
P(Bash | Edit)  = 0.71   # Edit 후 검증 Bash 실행
P(Read | Bash_fail) = 0.38  # Bash 실패 후 재탐색
```

### 8-3. 세션 단계(phase) 인식 추가
예측 시 세션의 어느 단계인지 알면 정확도 상승:
- 초반(0~35%): Search/Read 주도
- 중반(35~62%): Edit/Bash 주도
- 후반(62~100%): Verify/Cleanup 주도

### 8-4. 실패 시그널 → 행동 변화 예측
"tool_fail_count > 3" → 다음 행동이 AskUserQuestion 또는 Read로 전환될 확률 높음
이 패턴을 AkashicRecord에 failure_context로 별도 저장 필요

### 8-5. 공급자(provider) 별 behavioral signature
| provider | 특징 | 예측 시 가중치 조정 |
|----------|------|---------------------|
| claude | 조기 편집, 검증 3회, cleanup | verify 가중치 +30% |
| codex | 실행 중심, test 우선 | bash 가중치 +20% |
| gemini | 검색 우선, 멀티모달 | websearch 가중치 +20% |
| gpt | 늦은 편집, verify 생략 | edit 지연 패턴 반영 |

---

## 9. DescentNet 개선 방향

현재 DescentNet restriction map = identity (학습 없음)
→ 위 데이터로 학습하면 실제 behavioral manifold를 캡처 가능

**학습 목표:**
- node: tool 또는 task_phase
- edge: 전이 관계 (P(next_tool | current_tool, context))
- sheaf section: 현재 세션 상태 벡터
- global_section: 가장 일관된 행동 전략

**데이터 파이프라인:**
```
TOUCAN-1.5M trajectories
    ↓ adapt 커맨드
AkashicRecord (tool_seq 추가)
    ↓
transition matrix 계산
    ↓
DescentNet restriction map 초기화
    ↓
DescentNet fine-tune
```

---

## 참고 문헌

- [SWE-EVAL Trajectory-Enhanced Evaluation](https://openreview.net/pdf/718d11ac06d7a23ec0e5d83c04712da246fa0434.pdf)
- [Trajectory Shapes — nilenso blog](https://blog.nilenso.com/blog/2026/04/20/trajectory-shapes/)
- [τ-bench Paper](https://arxiv.org/pdf/2406.12045)
- [tau2-bench dataset — HuggingFace](https://huggingface.co/datasets/HuggingFaceH4/tau2-bench-data)
- [TOUCAN 1.5M — HuggingFace](https://huggingface.co/datasets/Agent-Ark/Toucan-1.5M)
- [TOUCAN Paper](https://arxiv.org/html/2510.01179v1)
- [Top 7 Agentic Benchmarks 2026 — MarkTechPost](https://www.marktechpost.com/2026/04/26/top-7-benchmarks-that-actually-matter-for-agentic-reasoning-in-large-language-models/)
- [Agent Harness Engineering — Addy Osmani](https://addyosmani.com/blog/agent-harness-engineering/)
- [Building Terminal AI Agents — arXiv:2603.05344](https://arxiv.org/html/2603.05344v1)
- [Multi-Agent Orchestration Frameworks 2026](https://presenc.ai/research/multi-agent-orchestration-frameworks-2026)
- [Awesome Harness Engineering](https://github.com/ai-boost/awesome-harness-engineering)
- [Holistic Agent Leaderboard](https://arxiv.org/pdf/2510.11977)
