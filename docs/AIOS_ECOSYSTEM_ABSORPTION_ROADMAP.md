# AIOS Ecosystem Absorption Roadmap

**날짜**: 2026-06-21  
**결정**: "다른 프로젝트들까지도. 우리는 비전만" — AIOS는 5-OS 비전+DNA invariants만 직접 보유. 구현체는 ecosystem에서 흡수.

---

## 전략 원칙

AIOS가 직접 유지하는 것:
- 5-OS 구조 (myworld/hivemind/memoryOS/CapabilityOS/GenesisOS)
- DNA invariants (authority/audit/reversibility/provenance)
- Contract lifecycle + ledger
- Operator discipline (4 OS query, escalation, mode)

AIOS가 흡수(뜯어서 빌트인)하는 것:
- 검증된 harness/runtime/router/skill 구현체
- 분류: `즉시` / `단기` / `위임` / `제외`

---

## 1. 즉시 흡수 (이미 설치됨 — 오늘 사용)

### 1-A. OMX Skills (31개, `~/.codex/skills/`)

핵심 skills:
- **`ralph`** — self-referential completion loop. AIOS turn-loop의 자기완결 패턴
- **`team`** — plan→prd→exec→verify→fix 파이프라인. hivemind dispatch 원형
- **`deep-interview`** — ambiguity scoring + 질문 전략. GenesisOS critic input
- **`autoresearch`/`autoresearch-goal`** — 목표→웹조사→구조화. MemoryOS absorption probe
- **`multi-agent-workloop`** — 병렬 agent 조율. hive parallel dispatch 원형
- **`ai-slop-cleaner`** — 결과물 품질 필터. AIOS verification gate
- **`ultragoal`/`ultrawork`/`ultraqa`** — 3단계 품질 에스컬레이션

**AIOS 매핑**: `scripts/aios_turn_loop.py`의 round controller에 OMX skill invocation 추가  
**흡수 방법**: `omx <skill>` — 이미 동작

### 1-B. OMC Skills (93개, `~/.claude/skills/`)

핵심 skills:
- **`code-review`/`critic`/`analyst`/`architect`** — 품질 검증 suite
- **`executor`/`planner`/`debugger`/`tracer`** — 실행 계층
- **`genesis-challenger`** — prompt-prison escape (GenesisOS)
- **`memoryos-librarian`** — MemoryOS lifecycle
- **`hivemind-executor`** — execution verification

**AIOS 매핑**: 이미 AIOS agent system의 기반으로 동작 중  
**흡수 방법**: OMC team pipeline으로 조율

### 1-C. wshobson/agents (84 plugins, 192 agents, 156 skills, 102 commands)

멀티-harness single source (Claude/Codex/Cursor/Gemini/Copilot):
- domain agents: architecture, security, ML, infra, docs, business
- 16 orchestrators: full-stack, security, ML, incident response
- 102 slash commands

**AIOS 매핑**: CapabilityOS의 agent routing 카탈로그  
**흡수 방법**: `/plugin marketplace add wshobson/agents` (Claude Code native)  
**즉시 가치**: 192 domain agents → aios_route가 선택 가능한 capability pool

---

## 2. 단기 흡수 (1주일 내)

### 2-A. Ouroboros (Q00) — Agent OS Core

```
Stack: Shell(ourocode) / Apps(plugins) / OS(core)
Core: Seed+Ledger+Runtime+MCP
```

핵심 패턴:
- **Seed**: vague idea → specification contract (interview-first)
- **Ledger**: every action → replayable, auditable event
- **Runtime**: multi-agent execution bound to spec
- **MCP**: tool interface layer

설치: `pip install ouroboros-ai` (0.42.5 가능)  
**AIOS 매핑**:
  - Seed → ASC contract 초안 자동화 (GenesisOS interview)
  - Ledger → AIOS_AGENT_LEDGER.md 패턴 강화
  - Runtime → hivemind execution 검증 gate
  - MCP → AIOS 5-OS MCP server 화

**흡수 방법**: `install+call` — ouroboros-ai 설치 후 `aios_harness.py`에서 `ooo` 워크플로우 호출  
**LiteLLM 우회**: ouroboros는 agent OS지 LLM router 아님 → 충돌 없음  
**DNA 충돌**: Ledger 패턴이 AIOS append-only audit과 호환 (invariant #3 safe)

### 2-B. buildermethods/agent-os — Standards Injection

기능:
- **Discover Standards**: 코드베이스 패턴 추출 → 문서화
- **Deploy Standards**: context-aware inject (what you're building 기반)
- **Shape Spec**: 더 나은 plan → 더 나은 build

**AIOS 매핑**: CapabilityOS의 codebase standards 계층  
**흡수 방법**: agent-os CLI 설치 → `aios_harness` `Standards` tool로 등록  
**즉시 가치**: 현재 AIOS codebase의 패턴을 자동 추출하여 새 contract/code에 주입

### 2-C. spec-kit (github) — Spec-Driven Development

패턴:
- Product scenarios → predictable outcomes
- 역할 기반 bundles (frontend dev / backend dev / PM)
- `specify` CLI로 spec 검증

**AIOS 매핑**: contract template에 spec-kit 포맷 흡수  
**흡수 방법**: `copy-pattern` — CLAUDE.md + contract template에 spec-kit 워크플로우 패턴 주입  
**즉시 가치**: ASC contract 품질 향상 (vague → spec-bound)

---

## 3. 위임 (AIOS가 직접 흡수 불필요 — 도구로 사용)

### 3-A. parallel-code (johannesjo)

- Electron GUI, 10 agents × 10 worktrees 동시 실행
- **위임 이유**: GUI 도구, AIOS CLI head와 레이어 다름
- **사용 방법**: 병렬 prototype sprint 시 직접 실행

### 3-B. OpenHands Agent Canvas

- ACP(Agent Canvas Protocol) 기반 developer control center
- Claude/Codex/Gemini backend 전환 가능
- **위임 이유**: AIOS가 이미 더 세밀한 operator 레이어 보유
- **사용 방법**: 외부 팀 배포 시 frontend로 사용 검토

### 3-C. SWE-agent, aider, Cline

- 각각 code-fixing agent, pair programmer, VS Code extension
- **위임 이유**: hivemind substrate로 활용 (call하면 됨, 흡수 불필요)
- **사용 방법**: `aios_harness` tool로 등록하면 충분

---

## 4. 제외 (DNA invariant 충돌)

| 프로젝트 | 충돌 사유 |
|---------|---------|
| LiteLLM 기반 시스템 | supply chain incident 2026-03-24, 절대 금지 |
| Auto-binding capability tools | invariant #1 (recommendation-only) 위반 |
| Silent memory write | invariant #2 (draft-first) 위반 |
| Ledger-editing tools | invariant #3 (append-only) 위반 |

---

## 실행 순서 (이번 주)

```
Day 1 (오늘):
  [x] ouroboros-ai 설치
  [ ] wshobson/agents plugin 설치 확인
  [ ] OMX team/ralph skill → aios_turn_loop 연결 테스트
  
Day 2-3:
  [ ] ouroboros ooo interview → ASC contract 초안 자동화 POC
  [ ] buildermethods agent-os standards extract → myworld codebase
  
Day 4-7:
  [ ] spec-kit 패턴 → contract template 흡수
  [ ] AkashicRecord에 ecosystem absorption events 기록
```

---

## 흡수 후 AIOS 상태 (목표)

```
AIOS Kernel (직접 보유):
  5-OS 비전 + DNA invariants + operator discipline

Absorbed Layer:
  OMX skills (31) → round controller hooks
  OMC skills (93) → agent dispatch pool
  wshobson/agents (192) → capability catalog
  ouroboros Seed+Ledger → contract lifecycle
  agent-os Standards → codebase-aware injection

Delegated:
  parallel-code → batch sprint tool
  OpenHands Canvas → team frontend
  SWE/aider/Cline → substrate tools
```

**결과**: AIOS가 직접 구현하지 않고도 400+ 전문 agents + spec-first workflow + standards injection + parallel execution을 지휘할 수 있는 구조.
