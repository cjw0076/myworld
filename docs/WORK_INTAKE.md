# AIOS Work Intake — 작업 접수 체계

작업이 들어왔을 때 "바로 실행" 하지 않고, 먼저 분류 → 기록 → 그 다음 실행.

## 작업 분류 (4가지)

| 유형 | 조건 | 처리 |
|------|------|------|
| **즉각 실행** | 5분 이내 끝남, 되돌릴 수 있음 | 바로 진행, 완료 후 ledger 1줄 |
| **세션 작업** | 30분~수시간, 명확한 완료 기준 | 이 파일에 기록 후 진행 |
| **장기 프로젝트** | 여러 세션, 여러 OS 관여 | contract 초안 후 founder GO |
| **비전/방향** | 새 OS, 아키텍처 전환, 외부 배포 | 반드시 escalate — 실행 불가 |

## 작업 접수 양식 (세션 작업 이상)

```
작업 ID: WORK-YYYYMMDD-NNN
제목: 
유형: 즉각실행 / 세션작업 / 장기프로젝트 / 비전방향
접수 시각: 
맥락: (왜 지금 이게 필요한가)
완료 기준: (이걸 보면 끝난 걸 아는 조건)
관련 OS: myworld / hivemind / memoryOS / CapabilityOS / GenesisOS
예상 소요: 
위험도: 낮음(되돌릴 수 있음) / 중간 / 높음(되돌릴 수 없음)
```

## 현재 백로그

### 대기 중 (미시작)

| ID | 제목 | 유형 | 우선순위 |
|----|------|------|---------|
| WORK-20260612-001 | MemoryOS Akashic Records 파이프라인 | 장기프로젝트 | P1 |
| ~~WORK-20260612-002~~ | ~~Local Credentials Vault~~ | ~~세션작업~~ | ~~P1~~ |
| ~~WORK-20260612-003~~ | ~~Session checkpoint/resume~~ | ~~세션작업~~ | ~~P1~~ |
| WORK-20260612-004 | memoryOS inbox 12개 draft 처리 | 즉각실행 | P2 |
| WORK-20260612-005 | hivemind ASC-0180 deliberation | 세션작업 | P2 |
| ~~WORK-20260612-006~~ | ~~Entropy injection (genesis_pulse 세션길이 비례)~~ | ~~세션작업~~ | ~~P2~~ |
| WORK-20260612-007 | SECI 4방향 파이프라인 설계 | 장기프로젝트 | P3 |
| WORK-20260612-008 | Cross-model ambient hivemind | 장기프로젝트 | P3 |

### 진행 중

없음

### 완료 (최근)

| ID | 제목 | 완료 시각 | 증거 |
|----|------|---------|------|
| WORK-20260612-002 | Local Credentials Vault | 2026-06-12 | git e3191ef scripts/aios_vault.py |
| WORK-20260612-003 | Session checkpoint/resume | 2026-06-14 | resume/show ID fix + backlog section filter, scripts/aios_checkpoint.py |
| WORK-20260612-006 | Entropy injection (genesis_pulse 세션길이 비례) | 2026-06-14 | scripts/aios_session_entropy.py — pressure 1-5 by session age, min interval per level, genesis critic integration |
| - | 4-OS × 4-lifecycle hook coverage | 2026-06-12 21:00 | git db35aab |
| - | plan mode default | 2026-06-12 | git bd32a73 |
| - | event bus loop (emit-after-write) | 2026-06-11 | git 8f5713d |

## 규칙

1. **기록 먼저, 실행 나중** — intake 없이 시작하지 않는다
2. **완료 기준 명시** — "잘 됐으면" 같은 모호한 기준 금지
3. **위험도 높음 = 반드시 확인** — 되돌릴 수 없는 작업은 founder 확인 후
4. **세션 끝날 때 백로그 갱신** — Stop hook이 자동으로 상기시킴
5. **중구난방 방지** — 여러 작업 동시 진행 금지 (하나 끝내고 다음)
