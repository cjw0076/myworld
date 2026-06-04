---
contract_id: ASC-0212
slug: aios-mcp-native
status: accepted
created: 2026-05-20 KST
accepted: 2026-05-20 KST
proposed_by: claude@myworld
acceptance_authority: founder 재원 — 2026-05-20 "Tier 1 중 MCP-native 먼저" (AskUserQuestion 응답) + ASC-0205 closeout 후 8축 #2 leverage 우선.
escalation: routine — ASC-0205 follow-on, ASC-0211 (CPL) 와 Tier 1 병렬.
goal: AIOS 5 OS 중 ≥2개를 MCP server 로 노출 + AIOS 가 외부 MCP server ≥1 의 client 로 연결 + capability 매트릭스에 그 substrate 기록. MCP 10K+ ecosystem 의 ingress/egress 양방향 확보.
origin: 2026-05-20 자료조사 (reference_mcp_ecosystem_2026): Anthropic donated MCP to Linux Foundation, 10K+ servers, MCP Apps SEP-1865. AIOS = operating layer, MCP = 표준 substrate. AIOS 가 *MCP-native* 가 아니면 ecosystem 외부.
---

# ASC-0212 — AIOS MCP-native

DNA references: Invariant 1 (decide before acting — MCP tools 는
recommendation/draft, 자동 실행 없음), Invariant 7 (privacy boundary —
MCP server 가 노출하는 데이터는 _from_desktop/dain/minyoung/.env 제외).

## Why now

ASC-0205 closed 직후 founder 가 Tier 1 의 첫 작업으로 MCP-native 선택.
8축 dream #2 의 leverage 가 가장 크다 — 10K+ ecosystem 자동 연결.

memoryOS 는 *이미* MCP 부분 통합: `memoryOS/memoryos/mcp.py` 가
`TOOL_REGISTRY` 와 11+ tools (memory.search, write_draft, review,
timeline, embed_batch, import_reports, export 등) + `run_server()`
stdio entry. SDK 호출만 막혀있음 (`pip install mcp>=1.0`).

## Required outcome — first buildable slice

1. **memoryOS MCP 활성 검증**: `pip install mcp` + `python -m memoryos
   mcp` runnable. 11+ tools 노출 확인.
2. **CapabilityOS MCP server** (2번째 OS): `CapabilityOS/capabilityos/
   mcp.py` 신규. 최소 3 tools — `capability.recommend`,
   `capability.audit`, `capability.observe`. `TOOL_REGISTRY` 패턴은
   memoryOS 동일.
3. **외부 MCP client 1건**: AIOS 가 client 로 외부 MCP server (예:
   filesystem MCP, github MCP, websearch MCP) 1건 연결. 결과를
   capability 매트릭스 evidence 로 기록.
4. CapabilityOS 매트릭스에 `mcp_server.aios_memory.v1`, `mcp_server.
   aios_capability.v1` cards 추가.

## Named Exit

closed when:
- memoryOS + CapabilityOS 둘 다 MCP server 로 runnable (또는 SDK 부재 시
  TOOL_REGISTRY 형태 검증).
- AIOS 가 외부 MCP server ≥1 client 연결 시도 + 결과 receipt 1건.
- capability 매트릭스에 MCP server cards ≥2 추가.
- ASC-0212 의 closing receipt commit.

## Stop conditions

- MCP server 가 *write* 작업 자동 실행하면 즉시 stop. tools 는
  recommend/draft/observe 등 read-only 또는 draft-write 만.
- 외부 MCP server 가 credentials 요구하면 escalate (privacy 경계).
- 외부 MCP server 가 *우리 repo 외부* (e.g., `_from_desktop/dain/minyoung/`)
  파일에 접근하면 stop.

## Scope

repos: `myworld` (contract + integration tests), `memoryOS` (mcp server
검증), `CapabilityOS` (mcp server 신규), `hivemind` (optional 3rd).

## First slice (this iter)

- 본 contract 발의 + accept
- CapabilityOS MCP module 빌드 (claude@myworld 가 myworld 측에서 진행 —
  capabilityos.cli 와 schema 인터페이스만, write 권한 없음)
- 외부 MCP client 시도는 *다음 iter* (mcp SDK 설치 + sandbox 필요)

다음 slices:
- mcp SDK 설치 검증 + memoryOS MCP stdio run
- hivemind MCP server (3rd OS)
- 외부 MCP server 첫 연결

## GenesisOS Escape Review

This review is advisory-only. It keeps MCP-native work from collapsing into
"connect every tool" just because the ecosystem is large.

### Assumptions

- Assumption 1: MCP is the right external boundary for AIOS because it is a
  widely adopted tool protocol.
- Assumption 2: exposing two OS layers as MCP servers improves AIOS
  interoperability more than it expands attack surface.
- Assumption 3: external MCP client evidence is more useful than another
  internal control-plane demo.

Counter branch: negate those assumptions. If MCP becomes a fashionable
integration sink, AIOS should expose fewer tools, not more, and should prefer a
read-only capability card over a runnable server until privacy and authority
receipts prove the route.

### Plain Language

Plain language: this contract says AIOS should learn to speak the common tool
protocol, but only through narrow, reviewable doors. A door that can write or
read private files without a receipt is not a success.

### Cross-Domain Frame

Legal analogy: MCP servers are public counters in a courthouse, not keys to the
archives. A visitor may request a document or file a draft motion, but the
counter clerk must record authority before any sensitive room opens.

### Time Horizons

- 1h: verify TOOL_REGISTRY shape and keep write tools draft-only.
- 1 week: run one external client receipt with credentials and private paths
  excluded.
- 1 year: treat MCP as a replaceable protocol adapter, not AIOS identity.
