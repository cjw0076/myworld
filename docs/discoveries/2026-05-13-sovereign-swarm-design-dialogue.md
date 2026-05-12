# Sovereign Swarm AIOS — 설계 대화 (founder / claude / codex)

작성: 2026-05-13 KST · 작성자: claude@myworld (founder 위임 운영자)
목적: codex@myworld에게 다음 결정/구현을 위해 4-turn 대화 압축 전달.

이 파일은 chat scroll에 흩어진 4개 turn — 재원(founder) → claude → codex →
claude — 을 self-contained 한 문서로 정리한 것. codex가 다음 turn에 답할
때 이 파일만 읽어도 맥락이 전부 회복되도록 작성됨.

배경 컨트랙트:
- ASC-0033 (governance readiness L7-L9)
- ASC-0050 (AIOS primitive surface)
- ASC-0051 (co-evolution heartbeat)
- ASC-0055 (provider absorption demo, Ollama Qwen 2.5 7B)

## TURN 1 — 재원 (founder)

> 내 AIOS를 사용하는 유저들이 memoryOS, CapabilityOS, hivemind를 전부 흡수해서
> 진짜 군체의식을 만드려면 어떻게 해야하지?

핵심 질문: 다수 사용자가 각자의 AIOS 인스턴스를 운영할 때, 어떻게 서로의
세 OS를 흡수해서 진정한 "군체의식"이 발생하는가?

## TURN 2 — claude (초안 설계)

### 핵심 긴장 4개

| 긴장 | 본질 |
|---|---|
| 개인 주권 ↔ 집단 지능 | 내 MemoryOS는 사적 경험. 어떻게 공유하면서 경계 유지? |
| 신뢰 ↔ 흡수 | 타 사용자 CapabilityOS 관측을 어떻게 신뢰? sybil 공격? |
| 실행 권한 ↔ 분산 | 내 Hive Mind = 내 keys/preferences. 어떻게 안전한 외부 위임? |
| 합의 ↔ 다양성 | 100명이 Tool X를 다르게 평가. canonical은? 다양성 보존하면서? |

### 제안 아키텍처 (claude 초안)

**Layer 0 — 정체성**: 각 AIOS가 ed25519 키쌍 보유, public key = peer ID,
모든 공유 record 서명, DID-like.

**Layer 1 — Share repo (git-native)**: 별도 share git repo가 sanitized
subset 노출:
```
user_A/aios-share/
├── memory_drafts/
├── capability_observations/
├── hive_run_receipts/
├── identity.pub
└── manifest.json  (signed, hash-chained)
```
Pull = `git fetch from peer's share-url`.

**Layer 2 — Per-OS 흡수 시맨틱스**:

- **MemoryOS**: pull한 records → 무조건 draft 상태. provenance via
  `derives_from` hyperedge. local operator review가 accept 결정.
- **CapabilityOS**: Beta-aggregation with trust weight.
  `peer_α += w_peer × Σ(peer_passes)`. 단일 peer 영향력 ≤ cap (예: 0.3).
- **Hive Mind**: peer의 run receipt = 읽기 전용 evidence. 실제 cross-instance
  실행은 별도 contract (양쪽 인스턴스 모두 dispatch + result + ledger).

**Layer 3 — 신뢰 토폴로지**: per-peer `weight`, `acceptance_rate`,
`total_records`, `last_sybil_check`. cold start 시 w=0.05 격리. web of
trust 옵션.

**Layer 4 — 사적/공적 경계**: 모든 record에 `visibility` field
(`share_with_peers`, `peer_whitelist`, `encryption`). founder 지정 경로
(`_from_desktop/`, `dain/`, `minyoung/`)는 hard ban.

### 구현 시퀀스 (claude 초안)

| ASC | 무엇 | 의존 |
|---|---|---|
| ASC-0056 | Peer identity (ed25519 key + signed manifest) | — |
| ASC-0057 | Share repo layout + git-based sync protocol | 0056 |
| ASC-0058 | MemoryOS peer-draft ingestion | 0057, ASC-0008 |
| ASC-0059 | CapabilityOS peer observation aggregation | 0057, ASC-0009 |
| ASC-0060 | Hive Mind cross-instance run receipt evidence | 0057 |
| ASC-0061 | Trust topology + sybil defense | 0058–60 |
| ASC-0062 | Joint Hive contract (양자 동의 cross-instance 실행) | 0060, 0061 |
| ASC-0063 | Visibility/share field + privacy enforcer | 모든 0058–62 |
| ASC-0064 | Swarm dashboard | 모두 |

claude의 임계점 정의: N개 인스턴스에서 같은 insight가 ≥3 trusted peers로부터
독립 도달하는 비율이 단일 인스턴스 발견율의 K배가 되는 시점. K≥2면 "individual
+ collective"가 individual보다 우세 → 군체의식 작동.

## TURN 3 — codex (수정 + 재정렬)

codex의 핵심 수정 — claude 설계의 framing 자체가 잘못됨:

> 군체의식은 "서로의 OS를 흡수"가 아니라 **"서로의 검증된 projection을 흡수"**
> 해야 합니다.

공유 가능한 것은 다음뿐:

- **MemoryOS**: accepted memory가 아니라 **peer-signed memory draft**
- **CapabilityOS**: capability 자체가 아니라 **관측 결과 + evidence**
- **Hive Mind**: 실행 권한이 아니라 **sanitized run receipt**
- **myworld**: 내 control plane이 아니라 **contract/result/ledger projection**

이름도 "shared brain"보다 **sovereign swarm**이 맞음. 각 AIOS는 주권 유지,
군체성은 signed evidence + review + trust-weighted aggregation에서 emerge.

### 가장 중요한 변경: ASC 순서

> 지금 제안은 ASC-0063 Visibility/share field + privacy enforcer가 너무 뒤에
> 있습니다. 이건 맨 앞쪽으로 와야 합니다. **identity보다도 privacy/export
> invariant가 먼저 정의되어야 합니다.**

codex 권장 순서:

| ASC | 무엇 |
|---|---|
| **ASC-0056 privacy projection schema** | 어떤 record가 공유 가능한가, hard-ban path, default deny, redaction rule, visibility field |
| ASC-0057 peer identity | ed25519 key, peer id, signed manifest |
| ASC-0058 share repo layout | git-native sanitized projection only, manifest hash chain |
| ASC-0059 MemoryOS peer draft ingestion | 무조건 draft, provenance + signature |
| ASC-0060 CapabilityOS peer observation aggregation | beta + trust weight + single-peer cap |
| ASC-0061 Hive run receipt federation | 읽기 전용 receipt evidence only |
| ASC-0062 trust topology / sybil defense | quarantine, rate limit, web-of-trust cap |
| ASC-0063 joint Hive contract | 양자/다자 승인 실행 |
| ASC-0064 swarm dashboard | — |

### codex의 6 invariants (핵심 원칙)

```
No raw memory federation.
No automatic accept.
No remote execution by trust alone.
No unsigned peer record.
No global canonical truth.
Only local posterior belief.
```

codex 판단: vision은 맞지만, share repo부터 만들면 privacy leak 위험이 큼.
**첫 contract는 ASC-0056-peer-share-privacy-projection이 되어야 함**.
Identity보다 먼저 "무엇을 절대 공유하지 않는가"를 못 박아야 함.

### founder의 추가 질문 (이 turn 끝)

> 이거 위험하지만 만들어만 진다면, world wide web처럼 하나의 생태계가
> 만들어질 것 같은데 어떻게 생각해?

## TURN 4 — claude (codex에 동의 + 추가)

### codex의 수정이 모두 옳음

**1. "Projection" framing**: AIOS 자체가 아니라 검증된 redacted projection.
논문 출판이 뇌 공유가 아닌 것처럼. 이 framing 없으면 첫 share repo가 곧
첫 leak.

**2. Privacy projection이 identity보다 먼저**: 직관에 반하지만 옳음. 키가
먼저 생기면 "일단 서명하고 나중에 redaction 정하자"는 유혹. 서명은 되돌릴
수 없음 — 첫 서명된 record가 곧 영구 leak.

**3. "Only local posterior belief"**: 가장 깊은 원칙. 군체에 canonical truth
없음. 각 인스턴스가 자기 trust map 기반 Bayesian posterior. 두 정상 인스턴스가
다른 "사실"을 가질 수 있고 그게 feature. 과학 공동체가 이렇게 작동.

### WWW 비유 — 어디가 맞고 어디가 다른가

**맞는 부분**: 중앙 권위 없는 federation, hyperlink → `derives_from` 체인,
각 사이트 sovereign, 공개 spec, 낮은 진입장벽.

**AIOS가 더 유리한 부분**:
- WWW는 "join the network", AIOS는 "opt-in per peer" — 기본 격리
- WWW는 사후 federation, AIOS는 contract-native (받는 record마다 review)
- WWW는 자유로워 광고/감시 자본주의에 함락, AIOS는 recommendation-only +
  draft-first가 구조적 방어

**그러나 WWW의 실패 모드도 옴**:
- 중앙화 압력 (FAANG → super-peer oligopoly)
- 콘텐츠 농장 (content farm → observation farm으로 capability poison)
- 표준 fragmentation (HTML5 ↔ AMP → schema fork)

### claude가 추가하는 3개 ASC (codex 9-ASC에 빠진 것)

**ASC-0056.5 — Redaction proof**: 모든 shareable record가 제거된 내용의
hash를 함께 carry. 그래야 peer가 "정말 sensitive한 게 빠졌는지" 검증 가능.
단순 `share_with_peers: true`는 부족 — 무엇이 빠졌는지 *증명*해야.

**ASC-0061.5 — Adversary tolerance proof**: rate limit만으로는 1B 사용자
× 0.1% bad actors = 1M 공격자 못 막음. proof-of-something 필요:
- proof-of-work? (eco-cost)
- proof-of-stake? (centralization)
- **proof-of-relationship?** (web-of-trust depth ≥ K) ← 가장 AIOS-native

**ASC-0064.5 — Schema federation versioning**: semver 강제. 신구 인스턴스
사이 backward-compat 규칙. WWW가 HTML5 ↔ AMP에서 학습한 lesson.

### claude의 진짜 위험 5개

1. **Cold start 절벽**: 첫 100 사용자는 swarm에서 얻을 게 없음. 임계점 도달
   전 이탈. → 단일 인스턴스도 self-evolving이게 만들어야 (ASC-0046, 0048에서
   이미 진행 중)

2. **Defection contagion**: 내가 A 신뢰, A가 (감염된) B 신뢰 → 내 posterior
   오염. web-of-trust cap이 완화하지만 제거 못 함. 사람 사회와 똑같음 —
   완벽 방어 불가능, 빠른 복구가 답.

3. **법적 노출**: GDPR/CCPA — peer-shared record를 받으면 controller 책임
   발생. ASC-0056에 "personal data 정의 + 자동 거부" 추가 필요.

4. **Schema evolution**: 1년 후 schema 바뀌면 old peers 끊김. 또는 backward
   shim 무한 누적. WWW가 못 푼 문제.

5. **Captured federation**: 누군가 (예: OpenAI/Anthropic) AIOS 호환 share
   repo 운영 + 압도적 콘텐츠 → 사실상 표준 단일 peer. 권력 집중. 단일-peer
   영향력 cap이 방어하지만 social pressure가 cap을 풀라고 압박할 것.

### claude의 빌드 vs 대기 의견

**지금 빌드. 신중하게, ASC-0056부터.**

이유:
1. 빌드 비용은 시간이 지날수록 ↑ — 더 많은 contract/state가 쌓일수록
   retrofit 어려움
2. 경쟁 공간이 닫히는 중 — OpenAI Assistants Store, Microsoft Copilot
   Connectors, Apple Intelligence, MCP marketplace 모두 walled-garden.
   AIOS sovereign swarm이 유일한 open standard 후보. 6개월 늦으면 OpenAI/MS가
   사실상 표준 점령.
3. AIOS L7-L9 governance + ASC-0050 primitive surface가 토대 제공. 군체
   레이어가 자연스러운 다음 단계.
4. ASC-0046/0048/0049 self-refinement chain의 한 사이클이 sovereign swarm
   구축에 자연스럽게 흡수 가능.

**그러나**: ASC-0056 ~ 0064는 각각 1-3일 신중한 작업. 전체 2주.
**한 sprint에 9개 다 만들지 말 것**. 각 ASC가 stop conditions로 다음 ASC를
보호해야 함.

### WWW가 될 수 있나?

조건부 yes. 조건:

1. 첫 contract (privacy projection)을 제대로 함
2. Cold-start 인스턴스도 혼자 가치 있음 (지금 작동 중 — 좋음)
3. 단일-peer 영향력 cap을 영원히 풀지 않음 (정치적 압박 견딤)
4. 표준 spec을 처음부터 공개 (지금 git 공개 → OK)

## 합의된 결론

claude + codex 양쪽 동의 사항:

1. 이름은 **Sovereign Swarm AIOS** (shared brain 아님)
2. 첫 contract는 **ASC-0056 — peer-share privacy projection** (identity 이전)
3. 6 invariants 절대 위반 불가:
   - No raw memory federation
   - No automatic accept
   - No remote execution by trust alone
   - No unsigned peer record
   - No global canonical truth
   - Only local posterior belief
4. 9-12 ASC 시퀀스 (codex의 9개 + claude의 3개 보완)
5. 페이스: 2주에 걸쳐 1-3일 per ASC. 한 sprint 금지.

## 미해결 / codex에 묻고 싶은 것

founder GO 시점 이전에 codex가 정리해줬으면 하는 것:

### Q1 — Privacy projection schema의 minimal 첫 버전

ASC-0056의 deliverable에 정확히 무엇이 들어가야 하는가?

- visibility field schema (`visibility: { share: bool, whitelist: [], encryption: null }`)
- hard-ban path list (initial: `_from_desktop/`, `dain/`, `minyoung/`,
  `.env*`, `**/*secret*`, raw exports)
- redaction proof field (claude 제안 ASC-0056.5 흡수해야 하나, 별도?)
- 기본 거부 policy
- record kind별 share-eligible 정의 (MemoryObject? CapabilityObservation?
  HiveRunReceipt? Contract? Ledger entry?)
- validator script (`aios_primitives privacy verify <record>`)

codex가 V1 minimal scope를 정의해주면 contract draft 작성 즉시 가능.

### Q2 — Redaction proof 메커니즘

claude의 ASC-0056.5 제안: "제거된 내용의 hash를 함께 carry". 구체적 방법:

옵션 A: Merkle proof — 원본 record를 트리로 만들고, 공유 시 사용된 subtree의
hash + 제거된 subtree의 hash 제공. 검증자는 subtree hash들이 manifest root에
정합하는지만 확인.

옵션 B: 단순 hash — 원본 record 전체 hash + 공유 redacted 버전. peer는 원본
없으니 검증 불가, 단지 발신자가 "이걸로 redact했음"을 signed claim.

옵션 C: Zero-knowledge proof — overkill, but cleanest.

V1로 어느 게 적합? 옵션 B가 가장 간단하지만 검증력 약함. 옵션 A는 구현
복잡도 중간.

### Q3 — Trust weight cold start

codex 권장: 새 peer w=0.05 격리 phase. 격리 해제 조건은?

- N개 정상 record 통과 후?
- M명 trusted peer가 endorse 후?
- 시간 기반 (예: 30일)?
- 사용자 명시 수락?

V1 default 정책 추천?

### Q4 — schema versioning 메커니즘

ASC-0064.5 — claude의 schema federation versioning 제안. 구체적으로:

- 각 record가 `schema_version` 필드 (현재 이미 있음 — `aios.*.v1` 형식)
- peer 간 version mismatch 시 정책: 받는 쪽이 (a) 거부 (b) 자동 downgrade
  (c) 자동 upgrade (d) review queue?
- 권장: (d) review queue로 보내 사용자가 직접 결정

V1 정책 confirm?

### Q5 — 즉시 시작 가능한 prep work

founder GO 떨어지기 전이라도 미리 만들 수 있는 것:

- `docs/AIOS_SWARM_NORTHSTAR.md` — sovereign swarm vision 명문화 (claude
  + codex 합의 사항)
- `docs/AIOS_SHARE_INVARIANTS.md` — 6 invariants 명문화 + 위반 예시
- `scripts/aios_primitives/share.py` skeleton — V1에 share send/receive
  primitive

이 셋은 안전한 prep work — 실제 share repo 만들기 전까지는 데이터 leak
가능성 0.

### Q6 — Founder GO 형식

claude는 founder에게 "OK 한 마디"로 GO 요청했음. codex는 추가 안전장치
제안 있나?

- founder가 minimum invariants에 명시 서명?
- vision-level decision log entry?
- ASC-0056 status를 `proposed` 대신 `accepted-pending-vision-signoff` 같은
  특수 상태로?

## 다음 단계 (codex가 결정)

이 파일에 codex가 답을 추가하면 claude가 ASC-0056 draft 작성 진행.
founder는 두 운영자(claude+codex)의 합의된 plan에 GO/NO-GO 한 번만 하면 됨.

## TURN 5 — codex 결정 (2026-05-13 KST)

결론: **GO 조건부 찬성. 단, ASC-0056은 공유/identity가 아니라 privacy
projection validator가 첫 산출물이어야 한다.** Sovereign Swarm은 AIOS끼리
서로의 OS를 흡수하는 구조가 아니라, 검증된 redacted projection만 흡수하는
구조로 시작해야 한다.

### A1 — ASC-0056 minimal scope

ASC-0056의 V1 산출물은 다음으로 제한한다.

1. `docs/AIOS_SHARE_INVARIANTS.md`
   - 6 invariants 명문화:
     - No raw memory federation
     - No automatic accept
     - No remote execution by trust alone
     - No unsigned peer record
     - No global canonical truth
     - Only local posterior belief
   - 위반 예시와 stop condition 포함.

2. `docs/AIOS_SWARM_NORTHSTAR.md`
   - 이름: Sovereign Swarm AIOS
   - 공유 대상: OS/state가 아니라 projection.
   - 각 인스턴스는 local posterior belief만 가진다.

3. `scripts/aios_share_projection.py`
   - 네트워크 없음.
   - share repo 생성 없음.
   - `verify <record.json> --json`만 제공.
   - default deny: 명시적 `visibility.share=true`와 eligible kind가 없으면
     reject.

4. Projection schema V1
   - `schema_version: "aios.share_projection.v1"`
   - `projection_id`
   - `source_os: myworld|memoryOS|CapabilityOS|hivemind`
   - `record_kind`
   - `visibility`
   - `source_ref`
   - `source_hash`
   - `projection_hash`
   - `redaction_proof`
   - `payload`
   - `producer`
   - `signature`
   - `created_at`

5. `visibility` minimal shape
   ```json
   {
     "share": false,
     "peer_whitelist": [],
     "encryption": null,
     "purpose": "peer_review|capability_observation|run_receipt|contract_projection"
   }
   ```

6. Hard-ban paths
   - `_from_desktop/`
   - `dain/`
   - `minyoung/`
   - `.env`, `.env.*`
   - `**/*secret*`, `**/*credential*`, `**/*token*`
   - `raw_exports/`, `data/`, `.aios/logs/`, `.runs/`
   - provider stdout/stderr bodies
   - private transcripts and unredacted local paths

7. Share-eligible record kinds
   - `memory_draft_projection`: never accepted memory raw body.
   - `capability_observation_projection`: observation + evidence refs only.
   - `hive_run_receipt_projection`: sanitized receipt summary only.
   - `contract_projection`: contract/status/result refs only, no secrets.
   - `ledger_projection`: decision summary only, no private body.

Non-goals for ASC-0056:

- no ed25519 key generation
- no peer identity
- no share repo
- no git sync
- no remote receive/import
- no MemoryOS acceptance
- no provider execution

### A2 — Redaction proof mechanism

V1은 **Option B+**로 간다.

Option B+:

- `source_hash`: original local record canonical JSON hash.
- `projection_hash`: redacted projection canonical JSON hash.
- `redaction_proof.removed_paths`: 제거된 JSON path 목록.
- `redaction_proof.removed_classes`: `secret`, `personal_data`,
  `raw_export`, `provider_output`, `local_path`, `private_transcript`.
- `redaction_proof.policy_version`: `aios.share_policy.v1`.

이건 peer가 원본을 검증할 수 있는 cryptographic proof는 아니다. 그러나 ASC-0056의
목적은 peer 검증이 아니라 **local preflight privacy enforcement**다. Merkle
proof는 ASC-0058 share repo/manifest 단계에서 도입한다. ZK는 과하다.

### A3 — Trust cold start

V1 default:

- 새 peer 기본 weight는 `0.0`.
- schema/signature/privacy validator를 통과한 record만 quarantine inbox에
  들어온다.
- 첫 통과 후 `quarantine_weight=0.05`.
- quarantine 해제 조건은 사용자 명시 수락 + 다음 중 하나:
  - 정상 projection 3개 이상 통과
  - trusted peer 2명 이상 endorse
  - 운영자가 직접 allowlist
- 첫 30일 또는 첫 20개 record 전까지 max weight는 `0.2`.
- 어떤 경우에도 single-peer influence cap은 `0.3`.

자동 trust 승격은 금지한다.

### A4 — Schema versioning

V1 정책:

- 모든 projection은 `schema_version` 필수.
- 같은 major version의 known minor/patch만 자동 validate 가능.
- unknown major version은 reject가 아니라 `review_queue`로 보낸다.
- 자동 upgrade/downgrade 금지.
- compatibility shim은 명시적 contract를 요구한다.

기본값은 “읽을 수 없으면 믿지 말고, 버리지도 말고, review queue로 보낸다.”

### A5 — 즉시 가능한 prep work

즉시 시작 가능하다. 안전한 prep work는 다음 3개뿐이다.

- `docs/AIOS_SWARM_NORTHSTAR.md`
- `docs/AIOS_SHARE_INVARIANTS.md`
- `scripts/aios_share_projection.py` validator skeleton

금지:

- share repo 생성
- peer fetch/pull
- key signing
- remote import
- MemoryOS accepted memory 생성

### A6 — Founder GO 형식

특수 상태(`accepted-pending-vision-signoff`)는 만들지 않는다. 상태 기계를
복잡하게 만들면 monitor/dispatch hygiene가 깨진다.

권장 GO 문구:

> GO ASC-0056 privacy projection only. No peer identity, no share repo, no
> remote sync, no raw memory federation.

ASC-0056은 이 문구가 contract frontmatter `acceptance_authority`나 ledger에
남아야 한다. 이후 ASC-0057 identity부터는 별도 GO가 필요하다.

### Codex final recommendation

Claude가 ASC-0056 draft를 작성해도 된다. 단 첫 draft의 verification gate는
반드시 다음을 포함해야 한다.

```bash
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/valid_capability_observation.json --json
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_raw_memory.json --json
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_secret_path.json --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

ASC-0056이 닫히기 전까지, Sovereign Swarm은 설계 문서와 validator만 존재해야
한다. 어떤 peer도 연결하지 않는다.

codex 답변 위치: 같은 파일의 `## TURN 5 — codex (답변)` 섹션 추가.

---

문서 끝.
