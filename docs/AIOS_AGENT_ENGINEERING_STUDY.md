# AIOS Agent Engineering Study
> 자산화 날짜: 2026-06-19 | 리서치 범위: Loop Architecture / Framework Survey / Harness Engineering / Benchmark Behavior Data

---

## 1. Agent Loop 유형 비교

| Loop 타입 | 핵심 메커니즘 | 언제 쓰나 | AIOS 관련성 |
|---|---|---|---|
| **ReAct** | Think→Act→Observe 매 step | 범용, 대부분의 task | 현재 aios_turn_loop 기반 |
| **Plan-and-Execute** | 고비용 LLM plan → 저비용 실행 | 긴 멀티스텝, 비용 최적화 | hivemind planner 분리 시 적용 |
| **Reflexion** | 실패→self-critique→episodic memory→재시도 | 코딩, 정답있는 task | AkashicRecord = episodic store |
| **Tree of Thought** | N경로 병렬→평가→가지치기 | 탐색공간 넓은 task | GenesisOS divergence와 연결 |
| **CodeAct** | bash+code = 단일 action space | 소프트웨어 에이전트 | hivemind 실행층 참고 |

### 실제 Turn Loop 구현 (6-Phase)

```
Phase 0: Pre-check    → circuit breaker (turns, tokens, doom-loop)
Phase 1: Compaction   → context 70%↑이면 오래된 관찰 압축
Phase 2: Think        → optional CoT
Phase 3: LLM call     → with tool definitions (progressive disclosure)
Phase 4: Stop check   → end_turn / turn_cap / token_budget / user_interrupt
Phase 5: Tool dispatch→ registry → auth gate → sandbox → observation
Phase 6: Update       → messages += [assistant, tool_result] → 다음 turn
```

**Stop condition 7종:**
`end_turn` / `turn_cap` / `token_budget` / `doom_loop(same_call×3)` / `error_cascade` / `lexical_target` / `user_interrupt`

> 실제 사례: 루프 미제어로 5시간에 $50,000 소모. Turn cap + token budget 두 층 필수.

### Context 관리 5단계 압축 전략

```
70% → 오래된 tool_result 요약
80% → 큰 파일 내용 압축
90% → 중간 think block 제거
95% → 에피소드 전체 요약 + 새 컨텍스트 재시작 (context handoff)
```

---

## 2. 프레임워크 핵심 패턴 (엔지니어링 관점)

### LangGraph
- State = `TypedDict` 하나가 그래프 전체를 관통
- Edges = 상태 기반 라우팅 (conditional edge)
- Checkpointer = 매 node 실행 후 state 저장 → crash/resume/time-travel
- Human-in-the-loop = interrupt → 사람 확인 → checkpoint resume

### AutoGen v0.4
- Actor model (메시지큐 기반 async) 도입
- Conversation = API: 두 에이전트의 대화가 인터페이스
- GroupChatManager가 다음 발언자 동적 선택
- 단기 = transcript, 장기 = 직접 구현 필요

### OpenHands (CodeAct)
- **모든 상호작용 = Event** (Action / Observation 두 종류만)
- Action 타입: `CmdRunAction`, `IPythonRunCellAction`, `BrowserInteractiveAction`, `AgentDelegateAction`
- Sandbox = Docker container → Action Executor REST API → Observation
- Agent 코드 변경 없이 `LocalWorkspace` ↔ `DockerWorkspace` 스왑 가능

### Letta (MemGPT)
- **3-tier memory**: Core(항상 in-context) → Recall(검색가능) → Archival(벡터 저장소)
- Inner monologue: thinking thread와 speaking thread 분리
- sleeptime agents: 백그라운드에서 기억 정리/압축/승격
- **핵심**: LLM이 직접 메모리 읽기/쓰기 함수를 호출

### CrewAI
- Agent = {role, goal, backstory, tools, llm}
- Backstory = system prompt 핵심 (flavor가 아님, 환각 감소)
- Sequential(A→B→C) vs Hierarchical(manager→O(n) workers)
- Task output = Pydantic schema로 강제 구조화

---

## 3. Harness Engineering 핵심 설계

### 전체 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    AGENT HARNESS                        │
│                                                         │
│  [System Prompt Assembly]  [History]  [Tool Defs]       │
│         ↓                     ↓          ↓              │
│                    ┌──────────────┐                     │
│                    │  LLM CALL    │ ← token budget     │
│                    └──────┬───────┘                     │
│                           ↓                             │
│                   [Response Parser]                     │
│                           ↓                             │
│          ┌────────────────┼──────────────┐              │
│   [Pre-action Auth]  [Tool Registry]  [Lifecycle]       │
│          ↓               ↓               ↓              │
│                   [Sandbox Executor]                    │
│                    subprocess / Docker                   │
│                           ↓                             │
│                    [Event Log] → JSONL append-only      │
│                           ↓                             │
│                    [OTel Traces] → gen_ai.* spans       │
│                                                         │
│  ──────── WHILE LOOP (iteration cap enforced) ─────── │
└─────────────────────────────────────────────────────────┘
```

### Tool Registry 설계

```python
TOOL_REGISTRY = {
    "bash": {
        "schema": {"name": "bash", "input_schema": {"command": {"type": "string"}}},
        "permission": "workspace",   # read-only | workspace | full
        "timeout_s": 30,
        "retry": 1,
        "sandbox": "subprocess",
        "pre_auth": classify_bash_risk,
    },
}

# Dispatch 흐름:
# 1. Registry 조회 → 2. Schema validation → 3. Auth gate (LOW/MED/HIGH)
# 4. Sandbox executor → 5. timeout watchdog → 6. observation 반환
# 7. Event log append
```

### Context 공간 배분 (128K 모델 기준)

```
System prompt (static)  : 4K  ← prefix cache 고정
System prompt (dynamic) : 8K
Tool definitions        : 8K  ← progressive disclosure (관련 tool만)
Active history          : 96K
  ├── Recent turns verbatim: 60K
  ├── Compressed history:    24K
  └── Working memory:        12K
Output budget           : 8K
```

**Progressive Tool Disclosure**: 전체 tool을 항상 주입하지 않고 현재 task 패턴에 맞는 tool만 주입 → token cost 최대 10x 절감 (MindStudio 사례)

### Sandboxing 방식

| 방식 | 격리 수준 | 시작 비용 | 적합한 상황 |
|---|---|---|---|
| In-process | 없음 | 0ms | 신뢰된 코드, read-only |
| subprocess | 프로세스 격리 | ~5ms | 로컬 개발 |
| Docker | 완전 격리 | ~200-500ms | 사용자 코드, 멀티 테넌트 |
| VM/gVisor | 커널 격리 | ~1-3s | untrusted arbitrary code |

### Observability 최소 요구사항 (OTel GenAI v1.41)

```python
# LLM 호출마다
span.set_attribute("gen_ai.provider.name", "anthropic")
span.set_attribute("gen_ai.usage.input_tokens", n)
span.set_attribute("gen_ai.response.finish_reasons", ["tool_use"])

# Tool 실행마다
span.set_attribute("gen_ai.tool.name", "bash")
span.set_attribute("gen_ai.operation.name", "execute_tool")

# Event Log (append-only JSONL)
{"ts": "...", "type": "tool_call", "tool": "bash", "risk": "LOW", "duration_ms": 245}
{"ts": "...", "type": "context_compaction", "before": 98000, "after": 52000}
{"ts": "...", "type": "checkpoint", "step": 12, "state_hash": "sha256:..."}
```

---

## 4. 실제 Benchmark Behavior 데이터

| 벤치마크 | task 유형 | 주요 tool | 평균 turn | SOTA |
|---|---|---|---|---|
| SWE-bench | GitHub 이슈 해결 | bash, edit, search | 성공:31 / 실패:58 | ~72% (OpenHands) |
| τ-bench | 도메인 API 에이전트 | retail/airline API | ~12 | ~65% |
| GAIA | 웹+툴 범용 | web_search, calculator | ~8 | ~71% |
| AgentBench | 8환경 추론 | Search, Python, MySQL | 가변 | ~58% |
| Toolathlon | 17모델 MCP 비교 | github, filesystem | ~8 | 모델별 상이 |

### 실제 Tool 빈도 (SWE-agent 80K 기준)
1. `bash` (cat/ls/grep) — 압도적 1위
2. `edit` — 2위
3. `python` — 3위
4. `find_file` / `search_file` — 4~5위

**성공 vs 실패 패턴:**
- 성공: 31.3 steps avg, 8,352 tokens
- 실패: 58.4 steps avg, 15,241 tokens (더 오래 헤맴)
- 실패 주 원인: 동일 tool 반복 호출 (doom-loop), context drift

---

## 5. AIOS 적용 인사이트 (우선순위 순)

### 즉시 적용 (이번 스프린트)

**A. Doom-loop 감지 + AkashicRecord 오염 방지**
```python
# ingest 시 필터
if same_tool_consecutive_count(tools) > 3:
    skip  # doom-loop 세션 → 허위 패턴 오염 방지
```

**B. Session loop-type 분류 → Bash 편향 해결**
```python
# 현재: 모든 세션 동일 취급 → Bash 압도
# 개선: loop-type별 분리
classify_loop_type(tools) → "react" | "plan_execute" | "exploration" | "doom_loop"
# loop-type별 AkashicRecord 분리 → 예측 정확도 향상
```

**C. AkashicRecord를 Letta 3-tier로 재구성**
```
Core    → ~/.aios/memory/core.json (항상 in-context, 소규모)
Recall  → ~/.aios/memory/objects.jsonl (로컬 검색)
Archival→ Global AkashicRecord (Cloudflare D1, 대규모)
```

### 다음 스프린트

**D. OpenHands Action/Observation 타입 정형화**
```python
# 현재 aios_packet = untyped dict
# 개선: Action / Observation 타입 명시
class BashAction(Action): command: str
class FileReadObservation(Observation): content: str; exit_code: int
```

**E. Progressive Tool Disclosure**
- 현재 MCP server가 모든 tool을 항상 expose
- 개선: task context → CapabilityOS recommend → 관련 tool만 주입

---

## 6. AIOS Harness 파일 구조 (제안)

```
aios/
├── kernel/
│   ├── harness.py          # while loop, 6-phase turn entry
│   ├── tool_registry.py    # TOOL_REGISTRY + dispatch()
│   ├── auth_gate.py        # pre-action authorization (3 레벨)
│   ├── context_manager.py  # token counting + 5단계 압축
│   └── event_log.py        # append-only JSONL
│
├── sandbox/
│   ├── base.py             # Workspace ABC
│   ├── local.py            # subprocess 격리
│   └── docker_ws.py        # Docker 격리 (production)
│
├── tools/
│   ├── bash.py             # BashTool + risk classifier
│   ├── read_file.py
│   ├── web_search.py
│   └── mcp_bridge.py       # MCP server → Tool adapter
│
├── memory/
│   ├── akashic.py          # 3-tier AkashicRecord I/O
│   ├── compressor.py       # ACON relevance scoring
│   └── checkpointer.py     # State persistence
│
└── observe/
    ├── tracer.py           # OTel spans
    └── event_log.py        # Session audit trail
```

---

## 7. 공개 데이터셋 → AkashicRecord 흡수 계획

| 우선순위 | 데이터셋 | HF 경로 | 크기 | field_map | 예상 기여 |
|---|---|---|---|---|---|
| **P1** | AgentBank | `Solaris99/AgentBank` | 51K | instruction→ctx, action→act, reward→outcome | +50K records |
| **P1** | MCP-Trajectory-Benchmark | `obaydata/mcp-agent-trajectory-benchmark` | 49 | steps[user]→ctx, tool_calls[0].name→act | MCP 패턴 |
| **P2** | Qwen-tool-calling | `zake7749/Qwen-*` | 1.4K | messages[user]→ctx, tool_calls.name→act | 도메인 다양성 |
| **P2** | SWE-agent-trajectories | `nebius/SWE-agent-*` | 80K | trajectory[ai]→ctx, bash/edit→act | 코드 에이전트 |
| **P3** | tau-bench-synthetic | `fuvty/tau-bench-*` | 280 | conversation[user]→ctx, tool_calls→act | API 에이전트 |

**목표:** 362 → 50,000+ records → DescentNet restriction map 학습 가능 규모

---

*참고 소스: ReAct(Yao et al.), Reflexion(Shinn et al.), OpenHands(arXiv:2511.03690),
ACON(arXiv:2510.00615), AHE(Medium), OTel GenAI v1.41, LangGraph docs, Letta docs*
