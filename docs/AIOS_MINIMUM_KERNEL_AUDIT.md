# AIOS Minimum Kernel Audit

**Created**: 2026-05-20 KST  
**Authority**: founder 재원 — chat directive 2026-05-20 ("AIOS는 실제 head를 만들어야 한다 ... contract freeze가 맞다 ... Minimum Viable AIOS Head를 추출하고, AIOS가 아닌 외부 작업 하나를 끝까지 처리하게 한다")  
**Status**: operational analysis report. **NOT a contract.** No ASC/AKA prefix, no status field, no Named Exit, no ledger entry. The whole point of contract freeze is to *stop* producing contract-shaped artifacts.

## Frame

Diagnosis (founder, verified):

- AIOS 의 *지능* 은 대부분 frontier LLM 안에 있다.
- AIOS 는 그 지능을 특정 방식으로 행동하게 만드는 *prompt-level operating scaffold* 다.
- scripts 는 그 scaffold 를 파일/계약/dispatch/monitor 로 고정하는 *plumbing* 이다.
- contracts + ledger 는 *운영 증거* 이지만, 제품 자체는 아니다.

Current footprint (verified 2026-05-20):

- 218 contracts (ASC-NNNN.md)
- 5,800+ line ledger
- 99 scripts (scripts/aios_*.py + install.sh)
- 60 AIOS_*.md docs
- 66 child-OS .py files (memoryOS/hivemind/CapabilityOS/GenesisOS)

→ 외부 사용자가 `curl install.sh | sh` 하면 *전체* 를 받음. 자기 시작 상태가 *우리 작업 화석* 으로 오염.

## What we wanted vs what grew

| 의도 (Hermes-style head) | 실제로 자란 것 |
|---|---|
| provider CLI 감싸는 실행 head | scripts/aios_invoke.py (provider wrapper) + 50+ orchestration scripts |
| memoryOS / CapabilityOS / GenesisOS 운영체 | 66 .py + 218 contracts 가 우리 자기 사용 사례에 맞춰진 graph/catalog/critic |
| web/tools/apps/infra/local LLM 통합 control plane | scripts/aios_primitives.py (web fetch + monitor + task) — *접점만* 있고 통합 head 없음 |
| Codex/Claude/Gemini/local 의 성격 차이 orchestration | ASC-0203 routing matrix (시작), ASC-0207 qwen3 substrate (시작) — 그러나 *반복 호출* 흐름 없음 |
| 사람 없이 반복 새 가치 organism | 우리 자체 개발 *반복* 가능하나, *외부 task 0건* |

진단: organism 의 *몸통* 이 아니라 *governance exoskeleton* 이 자라났다.

---

## Keep — 외부 사용자에게도 필요한 product core (목표: ≤20 파일)

이 파일들이 *시스템* 의 실제 substance. 다른 모든 것은 derivative.

### Frame docs (4)
- `docs/AIOS_DEFINITION.md` — AIOS 가 무엇이 아닌지 명시. north star 문서.
- `docs/AIOS_NORTHSTAR.md` — local-first head 목표
- `docs/AIOS_DNA.md` (또는 AIOS_AGENT_PROTOCOL.md) — 7 invariants
- `docs/AIOS_SMART_CONTRACT.md` — contract template format (사용자가 자기 contract 발의시)

### Agent role docs (2)
- `AGENTS.md` — root agent registry
- `CLAUDE.md` — provider-specific guidance (그리고 codex/gemini 대응 신규)

### Plumbing scripts (5)
- `scripts/install.sh` — 진입점
- `scripts/aios_dispatch.py` — 운영자 dispatch surface
- `scripts/aios_monitor.py` — state 관찰
- `scripts/aios_primitives.py` — web/task/ask/tools primitives
- `scripts/aios_invoke.py` — provider 호출 wrapper (현재 추정. CLI head 후보)

### Child OS minimal substrate (5-7)
- `memoryOS/memoryos/store.py` — append-only graph
- `memoryOS/memoryos/schema.py` — node/edge schema
- `memoryOS/memoryos/cli.py` (or mcp.py) — 운영 surface
- `CapabilityOS/capabilityos/catalog.py` — capability schema
- `CapabilityOS/capabilityos/cli.py` — recommend surface
- `GenesisOS/genesisos/critic.py` — 1 cross-domain transfer routine
- (optional) hivemind 진입점 1개

**총 ~18 파일**. ≤20 목표 달성 가능.

### To build (still missing in product core)
- **`aios` 단일 head**: `aios <goal>` high-level goal 입력, provider+local LLM+filesystem+memory+capability routing 통합 호출 → 결과 반환. 현재 `aios` entrypoint 는 subcommand wrapper (dispatch/memory/contract/...) 이지 *goal-first head* 아님.

---

## Archive — 우리 internal history (사용자에게 안 ship)

이 파일들은 *우리 development log* 로 *교육적 가치* 는 있으나 사용자의 *시작 상태* 가 되면 안 됨. 별도 repo 또는 분리 디렉터리 `docs/_history/`.

- 218 contract files (ASC-0001 ~ ASC-0215). 본 audit 직후 *freeze*.
- 5,800줄 ledger (`docs/AIOS_AGENT_LEDGER.md`).
- `docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md`
- `docs/operator_sessions/`
- 60 AIOS_*.md 중 ~50개 (정책/governance/state-audit 문서, 우리 우리만의)
- `docs/papers/*` (IRIS 이관됨)

이동 후보 위치: `docs/_history/contracts/`, `docs/_history/ledger.md`, `docs/_history/sessions/`, `docs/_history/aios_internal/` 같이.

## Delete/deprecate — 자기개발 부산물 (재시작 시 안 가져옴)

- ~30+ ASC-NNNN-uri-* 자동 promoted 인스턴스 (ASC-0058 inbox processor 출력)
- `scripts/aios_sprint_loop.py`, `aios_sprint_promotion.py`, `aios_round_controller.py` (sprint 관련 자동화 — 우리 자체 개발 루프)
- `scripts/aios_convergence_audit.py`, `aios_discomfort_inject.py`, `aios_frontier_question.py`, `aios_boundary_probe.py` (ASC-0211 L3 routines — 우리 contracts 만 audit. 외부 작업엔 의미 없음)
- `scripts/aios_dogfood_route.py` (ASC-0214 — 우리 메모만 본다)
- `scripts/aios_closure_gate.py` (ASC-0213 — 우리 contract closure 만 본다)
- `scripts/aios_external_knowledge_organ.py` (CC4 — 우리 시도에 맞춤. 외부 head 면 무관)
- `scripts/aios_local_app.py`, `aios_control_snapshot.py`, `apps/control/*` (우리 dashboard. 사용자가 *원할 수* 있으나 *core* 아님)

**자가 진단**: 위 *대부분* 이 *내가 방금 만든 것* 들이다. peer-honest deprecate 가 맞다.

## Missing — 실제 head 가 되기 위해 없는 것

이게 *진짜 work*. 외부 사용자가 받을 수 있는 head 의 구성:

1. **`aios <goal>` 단일 entry** — ✅ BUILT 2026-06-01
   - input: 자연어 goal 1개 ("이 repo 의 bug 찾아", "이 디렉터리 정리해", "이 paper 한 섹션 도와")
   - 내부 흐름: planner (frontier LLM) → router (CapabilityOS) → tool calls (provider CLI / web / local LLM / filesystem) → memory write → response
   - `scripts/aios_head.py`: goal → planner(provider) → ContractObject →
     runtime → receipts. DEFAULT READ-ONLY; write 는 `--allow-write`, network 은
     `--allow-network`. 사악한 plan 은 실행 전 fail-closed 거부 (6 tests).
   - 미연결: router(CapabilityOS) + memory write step 은 아직 자동 wiring 안 됨.

2. **Provider CLI adapter layer** — ✅ BUILT 2026-06-01
   - `aios.adapter.claude` / `.codex` / `.gemini` / `.ollama_local`
   - 각 adapter 가 `plan(goal) → list[step]` 과 `execute(step) → result` 인터페이스
   - `scripts/aios_adapters.py`: AdapterSpec registry, dependency-injected runner
     (unit-test 가능, 실 CLI 미호출). 부재 CLI = 미등록 = runner offline named-exit.
     secret 없음 (key 는 각 CLI config 에만). (7 tests)

3. **Safe filesystem write surface** — ✅ BUILT 2026-06-01
   - write 는 항상 patch + receipt (어디를 어떻게 변경했는지) 발급
   - rollback 가능
   - `scripts/aios_contract_runner.py`: ContractObject runtime kernel.
     fail-closed authority check → typed syscall → backup → receipt → rollback.
     모든 fs mutation 은 `.aios/runtime/backups/` 로 backup 후 reversible.
     live proof: governed read → reversible write → receipt → rollback (8 tests).

4. **Local LLM background cognition**
   - Ollama qwen3:8b 같은 모델이 *상시 background* — summarize/critique/route
   - 현재: ASC-0207 substrate registered, 그러나 *루프 안* 사용 없음

5. **Web research → action 흐름**
   - 우리 `aios_primitives.py web` 는 receipt 만 기록. 그 결과를 *다음 step* 으로 자동 연결 없음
   - `aios <goal>` head 가 web 결과를 *consume* + *act on* 해야 head

6. **External task input format**
   - `aios "<자연어>"` 외 정형 input (yaml/json) 도 받을 수 있게. 그러나 시작은 *자연어* 1줄.

→ 이 6개가 *진짜 head*. 현재 **3/6 완성** (2026-06-01: #1 head, #2 adapters,
#3 safe-fs-kernel). 남은 것: #4 local LLM background cognition (ollama 필요),
#5 web research→action 자동 연결, #6 정형 input (자연어/json 둘 다 이미 동작 —
사실상 부분 완료). 35 kernel tests green.

## Layer boundary — AIOS is a kernel, not a workflow engine (founder decision A, 2026-06-01)

질문: "system은 workflow 개념인가, 더 low-level인가?" → founder 답: **A (더 낮다).**

```
goal → planner(LLM, "무엇을") → ContractObject(생성된 plan + capability)
     → runtime kernel(권한강제+syscall+receipt+rollback)  ← AIOS 본체, LOW LEVEL
     → adapters/fs/web(드라이버)
```

- AIOS의 가치 = **통치**(authority enforcement + audit + reversibility), 오케스트레이션의
  영리함이 아님. workflow 엔진(Temporal/LangGraph/n8n)과 *경쟁 안 함* — 그것들은 위에서
  돌리면 됨.
- **확정된 NON-goal (이제 founder-confirmed):** runtime에 분기/병렬/조건/루프/durable-
  suspend = scheduler 넣지 않는다. workflow 표현력이 필요하면 커널 *위* 별도 레이어.
- 함의: 남은 #4/#5 는 *커널-저수준*으로 짓는다 (background cognition을 syscall로, web→action을
  receipt-연결 syscall로) — 스케줄러로 부풀리지 않는다.
- 기존 sprint-loop/round-controller(스케줄러성 자기개발 자동화) deprecate 방향 강화.
- ContractObject step 리스트가 선형 workflow처럼 *보여도* 가치는 통치이지 흐름제어 아님.

## Outside-domain test — 첫 검증 task

founder 가 제시한 후보 (다시 명시):
- (a) **uri 의 실제 bug fix 1건**
- (b) **IRIS paper draft 의 한 섹션 도움**
- (c) **개인 자료 정리** (privacy 영역 — careful)
- (d) **다른 외부 OSS repo 의 issue 1건**

검증 task 의 closing 조건:
- task 가 *AIOS 개발과 무관* 해야 함 (uri 가 AIOS 호출하는 건 ASC-0208, *외부* 가 아님. 우리 사람-구성 외 task 여야 함)
- task 가 *완료* 되어야 함 (시작 + 중단 ≠ 검증)
- task 결과 가 *외부에서 평가 가능* (PR merged, paper section 채택, 등)

**결과**:
- 통과 → AIOS = production-grade head 가능성. 다음 작업: kernel 확장
- 실패 → AIOS = prompt scaffold corpus. 라벨 조정. 거창함 제거.

## Permission model

founder 명시: literal 무제한 device ownership 위험. 다음 가드:
- 기본: read-index + explicit write
- provider CLI: adapter 로 감쌈 (직접 호출 안 함)
- private-gated data: memoryOS 가 직접 보호
- filesystem write: patch/receipt/rollback 경로만
- local LLM: cheap background cognition
- frontier LLM: planner / 어려운 reasoning

## Chosen path — C. Hybrid

Founder clarification 2026-05-20:

> AIOS가 cli들을 이용해 내 디바이스 전권을 가지고 작업을 처리하며 스스로는
> 커가는 시스템을 만드는 것이 목표.

Decision: choose **C. hybrid**.

Why:
- **A. bottom-up** is testable but repeats the self-development trap. Schema →
  runtime → compiler can stay internal for too long while no outside task gets
  completed.
- **B. outside-domain first** gives immediate reality contact but risks
  overfitting the runtime object to one privacy-heavy case.
- **C. hybrid** keeps the schema small, then immediately forces it through one
  outside-domain task. That makes contract-as-system concrete without letting
  architecture work become another governance loop.

Execution sequence:

1. Define one minimal `ContractObject` schema first. Target duration: 1-2
   hours, not a new ASC.
2. Use the selected outside-domain task as the first live specimen. Current
   founder candidate: **개인 자료 정리**, with privacy gates.
3. During that task, record every step into the schema fields: goal, authority,
   filesystem scope, provider/tool route, memory inputs, actions, receipts,
   evals, user checkpoints, and memory effects.
4. After the task, derive runtime requirements from the specimen. Only then
   build the scheduler/state-machine/compiler pieces that the specimen proved
   necessary.

Important distinction:
- Contract files are not the product.
- Contract objects can become the **AIOS process model**.
- The `aios` head should compile a natural-language goal into a governed
  runtime object, then use provider CLIs, local LLMs, memory, capability
  routing, web/tools/apps, and safe filesystem action to finish the task.

## Next move (immediate)

1. **Done**: write the minimal `ContractObject` schema as a runtime object
   spec, not as another ASC. Implementation:
   `scripts/aios_contract_object.py`; human spec:
   `docs/AIOS_CONTRACT_OBJECT_V0.md`.
2. Run the outside-domain proof immediately after schema draft. Current
   candidate: privacy-gated personal file organization.
3. Build only the head/kernel pieces that the proof needs.
4. If the proof completes, generalize the schema and runtime. If it fails,
   downgrade the AIOS claim and keep the specimen as negative evidence.

본 audit 통과 못하면 AIOS 는 production 이 아니다. 현재는 **operator-grade research scaffold**. 방향은 살아 있지만, 몸을 다시 줄이고 실제 head 를 만들어야 한다.
