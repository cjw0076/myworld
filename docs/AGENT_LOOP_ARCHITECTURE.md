# Agent Loop Architecture — 공부 자산

> 작성: 2026-06-19 | 목적: AIOS AkashicRecord × Agent Harness 설계 기반
> 출처: ReAct (2022), OpenHands (ICLR 2025), Reflexion (NeurIPS 2023),
>       "Inside the Scaffold" (arXiv 2604.03515), "Building AI Coding Agents" (arXiv 2603.05344),
>       Cat context tool (arXiv 2512.22087), ACON (arXiv 2510.00615),
>       Harness Engineering (Masood, Medium 2026-04)

---

## 1. Loop 유형 비교표

| Loop 타입 | 핵심 메커니즘 | 단위 | 언제 쓰나 | 장점 | 단점 |
|---|---|---|---|---|---|
| **ReAct** | Think → Act → Observe 반복 | 매 step | 대부분 범용 task | 실시간 피드백 반영, 구현 단순 | context 누적, 루프 탈출 어려움 |
| **Plan-and-Execute** | Planner(고비용LLM) → plan → Executor(저비용) | plan 단위 | 긴 멀티스텝 task, 비용 최적화 | 예측 가능, 싸다 | plan 실패 시 재적응 느림 |
| **Reflexion** | 실패 → 자기비평(verbal) → episodic memory → 재시도 | trial 단위 | 코딩 문제, 정답 있는 task | 학습 없이 91% pass@1(HumanEval) | evaluator 품질에 의존, 수렴 보장 없음 |
| **Tree of Thought** | 후보 경로 N개 병렬 생성 → 평가 → 가지치기 | tree 단위 | 탐색 공간 넓은 창작/수학 | 최적해 탐색력 높음 | 토큰 비용 N배 |
| **CodeAct** | bash + Python = 단일 action space | code block | 소프트웨어 개발 에이전트 | 파서 불필요, 실행 직접 검증 | sandbox 필수, 보안 리스크 |
| **Cat (Context-as-Tool)** | context 압축을 호출 가능 tool로 격상 | milestone 단위 | long-horizon, context overflow 잦은 task | 능동적 context 관리 | 구현 복잡도 높음 |

---

## 2. 실제 Turn Loop 구현 (의사코드)

### 2-1. 입력 구조 (매 step 조립되는 것)

```
system_prompt = [
    role_definition,
    tool_schemas (JSON Schema 배열),
    stop_condition_contract,   # "TASK_COMPLETE 문자열 출력 시 종료"
    injected_spec,             # 이번 task의 done 정의 (Plan-and-Execute)
    context_window_policy,     # compaction 규칙
]

messages = [
    {role: "user", content: original_task},
    # ↓ 이후 매 step 추가되며 쌓임
    {role: "assistant", content: [think_block, tool_use_block]},
    {role: "user",      content: [tool_result_block]},
    ...
]
```

### 2-2. 6-Phase ReAct Turn Loop (harness 수준)

```python
def agent_loop(task: str, max_turns: int = 50, token_budget: int = 100_000):
    session_id = new_uuid()
    messages = [{"role": "user", "content": task}]
    breaker = CircuitBreaker(max_turns, token_budget)
    audit_log = AuditLedger(session_id)

    for turn in range(max_turns):
        # Phase 0: Pre-check & Compaction
        breaker.check(turn, count_tokens(messages))   # 초과 시 즉시 raise
        if needs_compaction(messages):
            messages = compact(messages)              # 5단계 점진 압축

        # Phase 1: Think (optional chain-of-thought)
        # Phase 2: Self-critique (optional — Reflexion style)
        # Phase 3: LLM 호출
        response = llm.create(
            model=model,
            system=build_system_prompt(tool_schemas),
            messages=messages,
        )

        # Phase 4: 종료 판정 ← 가장 중요
        if response.stop_reason == "end_turn":        # tool call 없음
            audit_log.write(turn, response.usage, "complete")
            return AgentResult(success=True, output=response.content)

        # Phase 5: Tool dispatch
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = tool_registry.dispatch(block.name, block.input)
                tool_results.append(make_tool_result(block.id, result))

        # Phase 6: Post-processing (messages 업데이트)
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user",      "content": tool_results})
        audit_log.write(turn, response.usage, "continue")

    return AgentResult(success=False, breach_reason="turn_limit")
```

### 2-3. Stop Condition 체계 (프로덕션 필수 7종)

| 종류 | 조건 | 처리 |
|---|---|---|
| 정상 완료 | `stop_reason == "end_turn"` (tool call 없음) | success 반환 |
| Turn cap | `turn >= max_turns` | CircuitBreakerError raise |
| Token budget | `tokens >= budget` | hard stop, human checkpoint |
| Doom-loop | 같은 tool+args 3회 이상 반복 | 루프 감지 후 abort |
| Error cascade | tool 오류 N회 연속 | escalate |
| Lexical target | system prompt에 명시한 종료 문자열 감지 | success |
| 사용자 인터럽트 | SIGINT / explicit cancel | 즉시 중단, state 저장 |

> **실제 사고**: 2025년 Claude Code recursion loop가 5시간에 $16,000~$50,000 소모.
> Turn cap + token budget 두 층 필수.

---

## 3. Context Management

### 3-1. 문제: Context Rot

매 step마다 messages 배열이 커짐.
- tool result가 수백~수천 토큰 (파일 내용, bash 출력)
- 10 turn 후 context는 1 turn의 10배가 아니라 기하급수적

### 3-2. 5단계 점진 압축 (Claude Code / OpenHands 패턴)

```
Phase 0 (평상시)    : raw messages 그대로
Phase 1 (70% 도달)  : 오래된 tool_result 요약 (per-type 요약기)
Phase 2 (80% 도달)  : 큰 파일 내용 → "파일 읽음, 핵심: ..." 요약
Phase 3 (90% 도달)  : 중간 assistant turn 압축 (think block 제거)
Phase 4 (95% 도달)  : 에피소드 전체 요약 → 새 컨텍스트로 재시작
```

### 3-3. Cat 패러다임 (2024 연구) — context 자체를 tool로

```
C(t) = (Q, M(t), I^k(t))

Q        = Stable Task Semantics (고정 — task 정의, never 압축)
M(t)     = Long-term Memory (압축된 과거 trajectory 요약, 점점 커짐)
I^k(t)   = Short-term Working Memory (최근 k step raw, 압축 안 함)
```

에이전트가 자연스러운 milestone(서브태스크 완료, 전략 전환, 에러 발생)에서
`context_manage()` tool을 **능동적으로 호출**해 M(t)를 업데이트.
수동 threshold 기반 압축보다 정보 손실이 적음.

### 3-4. ACON (2024) — budget-aware 압축

- budget = 남은 토큰 수를 명시적으로 넘겨받아 압축 강도 결정
- tight budget → 강하게 압축 / relaxed budget → 살릴 것 살림
- 실패 분석 기반으로 압축 가이드라인 iterative refinement

### 3-5. 이중 메모리 아키텍처

```
Episodic Memory (cross-session)
  ↕ AkashicRecord → 우리가 만드는 것
Working Memory (current turn)
  ↕ messages 배열 + compaction
```

---

## 4. Harness Engineering — 컴포넌트 전체 지도

```
┌─────────────────────────────────────────────────┐
│                  Agent Harness                  │
│                                                 │
│  ① Execution Loop (ReAct 6-phase)              │
│  ② Tool Registry (MCP + native)                │
│     └─ Approval layer (Auto/Semi/Manual)        │
│     └─ DANGEROUS_PATTERNS blocklist             │
│     └─ Pre-tool hooks (exit code 2 = block)     │
│  ③ Context Manager                             │
│     └─ 5-stage compaction                      │
│     └─ System reminders (event-driven inject)  │
│  ④ State & Memory                              │
│     └─ Short-term: messages[]                  │
│     └─ Long-term: AkashicRecord / MemoryOS     │
│  ⑤ Control Flow                               │
│     └─ CircuitBreaker (turns + tokens)         │
│     └─ Doom-loop detector                      │
│     └─ Retry / escalate policy                 │
│  ⑥ Safety & Observability                      │
│     └─ AuditLedger (append-only SQLite)        │
│     └─ Token accounting per turn               │
│     └─ ReviewSurface + human attestation       │
└─────────────────────────────────────────────────┘
```

### Tool Registry dispatch 흐름

```
LLM → tool_use block (name, input)
  → ToolRegistry.lookup(name)
  → approval_gate(mode, name, input)
  → validation(DANGEROUS_PATTERNS, stale_read_guard)
  → pre_tool_hook() → if exit_code==2: block
  → handler.execute(input) → raw_result
  → post_process(truncate, summarize, offload_large)
  → tool_result block → messages에 추가
```

### 비용 최적화 패턴 (Plan-and-Execute + KV cache)

```
Planner: 고비용 LLM (claude-opus) → plan 생성
Executor: 저비용 LLM (claude-haiku) → 단계 실행
→ 실측: $3.00/MTok → $0.30/MTok (10x 절감), 지연 4x 감소

KV cache 전제: system prompt prefix를 stable하게 유지
→ 매 turn system prompt 앞부분이 캐시됨
→ prefix가 바뀌면 캐시 miss → 비용 폭발
```

---

## 5. AIOS 설계에 적용할 핵심 인사이트

### ① Harness = AIOS의 척추, 모델 = 교체 가능한 장기

"65%의 enterprise AI 실패는 모델이 아니라 Harness Defect(Context Drift, Schema Misalignment, State Degradation)에서 발생"
→ AIOS aios_turn_loop.py가 harness의 6컴포넌트를 구현해야 함
→ 지금 없는 것: AuditLedger, CircuitBreaker, Doom-loop detector

### ② AkashicRecord = Long-term Episodic Memory 레이어

ReAct loop의 messages[] = working memory (소멸)
AkashicRecord = cross-session episodic memory (영구)
→ 지금 우리가 만든 것이 정확히 이 역할
→ predict_behavior()는 Long-term memory에서 prior를 가져오는 retrieval

### ③ Stop condition이 없으면 AkashicRecord가 오염된다

agent가 doom-loop에 빠지면 같은 tool_call이 수백 번 기록됨
→ behavior memory에 허위 패턴 누적
→ 따라서 ingest할 때 doom-loop 세션 필터링 필수:
  `if same_tool_consecutive_count > 3: skip_session`

### ④ Context 압축 시점이 behavior pattern을 왜곡한다

세션 후반부에 압축이 일어나면 tool call이 사라짐
→ tool_freq가 실제보다 낮게 나타남
→ ingest 시 압축 이전 raw tool sequence 우선 파싱 필요
→ `_parse_claude_session()`에서 compaction 이벤트 감지해 가중치 보정 필요

### ⑤ 예측 정확도는 "session classification"에 달려있다

Bash 편향 문제의 근본: 모든 세션을 동일하게 취급
→ CodeAct 패턴인지, Plan-and-Execute 패턴인지, Reflexion 재시도인지
→ 세션 구조 자체를 분류해야 함:

```python
def detect_loop_type(tools: list[str]) -> str:
    # 동일 tool 반복 → ReAct simple
    # 'Agent' + 하위 tool → Plan-and-Execute
    # 오류 후 같은 시퀀스 재실행 → Reflexion retry
    # 다양한 Read/Grep 먼저 → exploration phase
```

---

## 6. 빠른 참조: Tool Call → AkashicRecord 연결

```
session: [Read, Grep, Read, Edit, Bash, Bash, Edit]
          ↓ _parse_claude_session()
tool_seq: ["Read", "Grep", "Read", "Edit", "Bash", "Bash", "Edit"]
          ↓ _classify_session() + detect_loop_type()
category: "code", loop_type: "react_simple"
          ↓ _freq_table()
tool_freq: {Read:2, Grep:1, Edit:2, Bash:2}
          ↓ write_to_akashic()
AkashicRecord entry → contribute_to_global()
          ↓
Global AkashicRecord (Cloudflare D1, 768-dim BGE embed)
          ↓ sync_from_global(query)
predict_behavior() → Bash:0.66, Edit:0.48, Read:0.41
```

---

## 부록: 즉시 구현 가능한 것들

| 기능 | 현황 | 다음 작업 |
|---|---|---|
| ReAct turn loop | `aios_turn_loop.py` 있음 | CircuitBreaker + AuditLedger 추가 |
| Tool Registry | MCP + native 혼재 | 통합 registry + approval layer |
| AkashicRecord (local) | `~/.aios/memory/` 구현됨 | doom-loop 세션 필터 |
| AkashicRecord (global) | Cloudflare D1, 362개 live | category별 weight 보정 |
| Context compaction | 미구현 | 5단계 압축 + Cat tool |
| Session loop-type 분류 | 미구현 | detect_loop_type() |
| Behavior prediction | 구현됨 (freq+descent) | loop_type feature 추가 |
| Stop condition | 미구현 | CircuitBreaker (turns+tokens) |
| Audit ledger | 미구현 | append-only SQLite |
