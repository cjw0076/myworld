# AkashicRecord — 분산 검증 가능 원장 설계
> 목표: 원장을 지리적으로 분리하되 누구나 검증 가능하게. 전 세계 컴퓨팅 자원을 균등 활용.
> 작성: 2026-06-19

---

## 핵심 설계 원칙

```
분산   : 단일 서버 의존 없음. 어느 노드가 죽어도 기록 보존
검증   : 모든 기록은 Merkle 증명으로 독립 검증 가능
기여   : 각 AIOS 사용자 기기 = 노드 = 컴퓨팅 + 저장 기여자
프라이버시: 콘텐츠는 절대 이동 안 함. 구조(tool 이름+빈도)만 공유
```

---

## Layer 1 — Entry Format (콘텐츠 주소 지정)

모든 기억 항목은 **내용이 곧 ID**. 위조 불가.

```python
# 항목 ID = 콘텐츠의 SHA256 (이미 구현됨, 강화 필요)
entry_id = "beh-" + sha256(
    content + schema_version + contributor_epoch
).hexdigest()[:16]   # 16자로 확장 (충돌 방지)

# 각 항목이 이전 항목을 참조 → 체인
entry = {
    "id":          entry_id,
    "prev_id":     previous_entry_id,  # append-only 체인
    "content_hash": sha256(content),   # 전체 콘텐츠 해시
    "schema":      "aios.agent_behavior.v1",
    "epoch":       1234567890,         # 기여 시점 (초)
    # ... 기존 필드들
}
```

---

## Layer 2 — Merkle Tree (무결성 증명)

항목들을 **Merkle 트리**로 조직화 → 어떤 항목이든 전체 다운로드 없이 증명 가능.

```
                  ROOT HASH
                 /         \
          H(A+B)             H(C+D)
         /      \           /      \
      H(A)    H(B)       H(C)    H(D)
       A        B          C       D
```

### 구현

```python
# Worker에서 Merkle root 계산
def compute_merkle_root(entry_ids: list[str]) -> str:
    # 1. 모든 entry_id를 정렬 (deterministic)
    leaves = sorted(sha256(eid) for eid in entry_ids)
    # 2. 쌍을 만들어 반복 해시
    while len(leaves) > 1:
        if len(leaves) % 2 == 1:
            leaves.append(leaves[-1])  # 홀수면 마지막 복사
        leaves = [sha256(a + b) for a, b in zip(leaves[::2], leaves[1::2])]
    return leaves[0]

# 특정 항목의 Merkle proof 생성
def merkle_proof(entry_id: str, all_ids: list[str]) -> list[str]:
    # proof = 해당 잎에서 root까지 경로의 sibling 해시들
    # 누구든 이 proof로 root를 재계산 → 검증 완료
    ...
```

### 엔드포인트 추가

```
GET  /root          → { root_hash, entry_count, timestamp, prev_root_hash }
GET  /proof/{id}    → { entry, merkle_proof: [...], root_hash, verified: bool }
POST /verify        → { id, claimed_root } → { valid: bool, actual_root }
```

### Root Chain (변조 불가)

```
root[n] = sha256(root[n-1] + entries_batch_hash + timestamp)
```
새 항목이 추가될 때마다 이전 root를 포함해 계산 → 과거 수정 불가.

---

## Layer 3 — 지리적 샤딩 (Geographic Sharding)

### 현재: 단일 Cloudflare D1 (US East)

```
모든 사용자 → [Cloudflare Worker] → [D1 US-East]
                                          ↑
                                    단일 장애점
```

### 목표: 3 Region × Category Shard

```
[User: Seoul]     → aios-akashic-asia.workers.dev → [D1 Asia]
[User: London]    → aios-akashic-eu.workers.dev   → [D1 EU]
[User: New York]  → aios-akashic-us.workers.dev   → [D1 US]

                       ↓ 동기화
                  [Root KV] (Cloudflare KV — 전 세계 edge replicated)
                  root_hash, entry_count, shard_map
```

### 샤딩 키

```python
# 카테고리별 샤드 → 검색 시 관련 샤드만 쿼리
SHARD_MAP = {
    "code":        "aios-akashic-code",
    "docs":        "aios-akashic-docs",
    "data":        "aios-akashic-data",
    "competition": "aios-akashic-comp",
}

# 지리별 라우팅 (Cloudflare geo header 활용)
def route_to_region(request) -> str:
    country = request.headers.get("CF-IPCountry", "US")
    if country in ASIA_COUNTRIES:
        return "https://aios-akashic-asia.workers.dev"
    if country in EU_COUNTRIES:
        return "https://aios-akashic-eu.workers.dev"
    return "https://aios-akashic-us.workers.dev"
```

### 교차 샤드 검색

```
POST /sync (query)
  → 1. 로컬 region 검색
  → 2. 병렬로 다른 region Worker에 fan-out
  → 3. 결과 병합 + top-K 반환

# Python 클라이언트
def sync_from_global(query, regions=None):
    regions = regions or ["us", "eu", "asia"]
    results = parallel_fetch([f"{REGIONAL_URLS[r]}/sync" for r in regions], query)
    return top_k_merge(results)
```

---

## Layer 4 — P2P Node Network (분산 컴퓨팅)

각 AIOS 설치 = 잠재적 노드. 디바이스가 컴퓨팅과 저장을 기여.

### Node 유형

```
Type A  Light Node  : ~/.aios/ 만 보유. query routing 기여
Type B  Shard Node  : 1개 카테고리의 shard 완전 보유 + serve
Type C  Full Node   : 전체 AkashicRecord + Merkle tree + proof 제공
Type D  Embed Node  : GPU 보유. 임베딩 계산 기여 (RTX 5090 등)
```

### Node Registry (Bootstrap)

```json
// ~/.aios/peers.json
{
  "bootstrap_nodes": [
    "https://aios-akashic.cjw070690.workers.dev",
    "https://aios-akashic-asia.workers.dev"
  ],
  "known_peers": [
    {"id": "node-abc", "url": "http://192.168.x.x:8765",
     "type": "B", "shard": "code", "last_seen": 1234567890}
  ]
}
```

### Gossip Protocol (항목 전파)

```
새 항목 기여 시:
1. 로컬 ~/.aios/ 에 저장
2. 부트스트랩 노드에 POST /contribute
3. 부트스트랩이 known peers에 fan-out (Gossip)
4. 각 노드가 자기 shard에 해당하면 저장, 아니면 relay
5. Merkle root 업데이트 → KV 전파
```

### Embed Node 활용 (RTX 5090 같은 GPU 보유자)

```python
# aios_embed_node.py — GPU 기여자 실행
async def embed_service():
    """로컬 GPU로 임베딩 요청을 처리, Cloudflare AI 대신 사용."""
    while True:
        task = await queue.get()
        vector = ollama_embed(task["text"])  # 로컬 GPU
        await report_to_coordinator(task["id"], vector)
        # 기여 포인트 획득

# 라우팅: Cloudflare Worker가 embed 요청 시
# → 1. 근처 Embed Node 있으면 위임 (분산 컴퓨팅)
# → 2. 없으면 Workers AI fallback
```

---

## Layer 5 — 검증 프로토콜

### 사용자가 자신의 기여를 검증

```bash
# 내 기억이 정말 원장에 있는가?
aios behavior verify --id beh-abc123def456

# 출력:
# ✓ Entry found in AkashicRecord
# ✓ Merkle proof valid (depth: 18, root: sha256:...)
# ✓ Root chain: entry #51,362 of 51,362
# ✓ Contributed at: 2026-06-19T14:30:00Z
```

### 노드가 다른 노드를 검증

```python
def verify_peer_shard(peer_url: str, their_root: str) -> bool:
    """피어 노드의 root hash가 내 root와 일치하는지 확인."""
    my_root = get_local_merkle_root()
    peer_root = requests.get(f"{peer_url}/root").json()["root_hash"]
    # root가 다르면 누군가 데이터를 변조했거나 sync가 안 된 것
    return sha256_compare(my_root, peer_root)
```

### 공개 Checkpoint (누구나 감사 가능)

```
매 1,000개 항목마다:
root_hash를 공개 GitHub 파일에 append
→ 누구든 "이 시점에 X개 항목이 있었다"를 외부에서 검증 가능

# 파일: docs/akashic_checkpoints.jsonl
{"epoch": 1234567890, "count": 51000, "root": "sha256:abc..."}
{"epoch": 1234568890, "count": 52000, "root": "sha256:def..."}
```

---

## 구현 로드맵

### Phase 1 (현재 → 이번 스프린트)
- [x] 단일 Cloudflare Worker + D1
- [x] content-addressed IDs (beh-sha256[:12])
- [ ] `/root` `/proof/{id}` `/verify` 엔드포인트 추가
- [ ] Python 클라이언트 `verify` 명령 추가
- [ ] 공개 checkpoint (GitHub 파일)

### Phase 2 (다음 달)
- [ ] 3 Regional Workers (US / EU / Asia)
- [ ] Category sharding (code / docs / data / competition)
- [ ] 교차 샤드 fan-out 검색
- [ ] Cloudflare KV에 root hash 동기화

### Phase 3 (1분기)
- [ ] P2P Light Node (aios behavior serve-node)
- [ ] Gossip protocol for entry propagation
- [ ] Embed Node 프로토콜 (GPU 기여자)
- [ ] Node health dashboard

### Phase 4 (장기)
- [ ] Federated learning on behavioral patterns
- [ ] DescentNet restriction maps trained on distributed data
- [ ] ZK proof for embedding correctness (embedding 계산 검증)

---

## 전 세계 컴퓨팅 자원 활용 방법

```
데이터  기여 : 모든 AIOS 사용자 → behavioral memories 제공
저장   기여 : Type B/C 노드 → shard 보관 + serve
컴퓨팅 기여 : GPU 보유자 (RTX 5090 등) → 임베딩 계산
검증   기여 : 모든 노드 → Merkle root 검증 참여

현재 Cloudflare:
  Workers  : 300+ 글로벌 PoP → 이미 분산
  KV       : 전 세계 edge replicated → root hash 저장에 적합
  D1       : 현재 US-East 중앙화 → multi-region 필요
  Workers AI: 분산 GPU 추론 → 임베딩 계산

AIOS 사용자 기기:
  ollama + local LLM → 임베딩 노드로 참여 가능
  ~/ .aios/ → shard 캐시로 활용 가능
```

---

## 보안 / 프라이버시 보장

```
- tool_freq (구조적 메타데이터)만 전파. 콘텐츠 절대 이동 금지
- 각 항목은 privacy guard를 통과해야 기여 가능
- 기여자 ID = 익명 해시 (실제 identity 드러나지 않음)
- opt-in 카테고리만 기여 (docs / data / code / personal)
- DNA 불변량 #7: 프라이버시 경계 불가침
```

---

*이 문서는 AIOS AkashicRecord의 분산화 로드맵. Phase 1부터 순차적으로 구현.*
