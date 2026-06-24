# AIOS SaaS / Lakebase AkashicRecord — production plan

> Founder decision (2026-06-25): leave local-first behind and go SaaS. The intelligence
> layer was always cloud (Claude/Codex CLIs), so data-locality alone was a weak moat and
> an adoption liability. Sovereignty is **re-defined**: not locality, but per-tenant
> isolation + encryption + opt-in + portability (DNA #7 survives the move).
>
> Canonical architecture (founder-as-architect brief, this session):
> **Lakebase (Postgres) = canonical source of truth; the knowledge graph is an
> asynchronous *projection* built by a Graph Compiler, not synchronously on request.
> No separate graph DB (Neo4j) yet.**

This is the ralplan artifact for the OMC head pipeline (deep-interview → ralplan →
ralph → review). The deep-interview was answered by the founder's architecture brief.

## Scale frame

Target ≈ 1,000 DAU. The risk at this scale is **not** Postgres capacity but four
failure modes: mixing private & global memory, synchronous graph generation,
filtered-vector recall degradation, full-Merkle recompute. Separate those four first.

Load envelope (illustrative): 1000 DAU × 3 runs × 25 turns × 3 events ≈ 225k events/day
≈ 6.75M/month. Postgres handles this **iff** write amplification is controlled:
store every event; do NOT embed every event, store every similarity edge, or auto-accept
every claim, synchronously.

## Target topology

```
clients → API Gateway (auth · tenant · consent · rate-limit · privacy gate · idempotency)
        → Command API (Lakebase R/W primary+HA)   Query API (Lakebase R/O replica)
              ledger.events · current projections · transactional outbox
        → Queue/Worker plane: Graph Compiler · Embedding · Consolidator ·
              Capability Aggregator · Merkle · Artifact processor
        → Object storage + Delta/analytics
Cloudflare = public edge (auth, rate-limit, cache, dashboard) — NOT canonical data.
```
Online request never waits on graph extraction or embedding. CQRS + event-sourcing.

## Data model (schemas)

- `ledger.events` — immutable source of truth (the only thing the write path appends).
- `graph.{entities,entity_aliases,claims,claim_evidence,claim_relations,edges_current}`
  — knowledge graph; `edges_current` is a **disposable projection** (recompilable).
- `memory.{episodes,candidates,memories,embeddings,retrievals,feedback}` — long-term.
- `behavior.{patterns,transitions,outcomes,provider_stats}` — behavioral graph (the CLS
  corpus already built: arg-aware capture / cls_gate / cls_train feed this).
Separation: **Event** (happened) → **Claim** (extracted, reviewable) → **Edge-current**
(accepted projection) → **Embedding** (regenerable index).

## Write path (online)

`BEGIN; set_config('app.tenant_id',…,true); INSERT ledger.events; UPDATE run_state
(optimistic version); INSERT jobs.outbox; COMMIT;` — events + projection + outbox in ONE
transaction (no dual-write loss). NO LLM extraction / embedding / Merkle / traversal
online — workers do those after commit, all **idempotent**
(`UNIQUE(tenant_id, source_event_id, compiler_name, compiler_version)`).

## Retrieval

- Tenant-private (small corpus): exact filter on `tenant_id` → exact vector distance →
  top-K (more accurate than forcing ANN under a selective filter — a known pgvector trap).
- Global/shared (large): ANN top-100 → privacy/metadata filter → lexical+graph rerank → top-20.
- Whale tenants: dedicated partition / index / project.
- Stable core: `pgvector 0.8` (HNSW/IVFFlat) + `tsvector+GIN` + `pg_trgm`. Beta
  (`lakebase_vector`, `lakebase_text`) behind feature flags only. Merge via RRF/reranker.

## Tenant isolation

`tenant_id` on every private table (in PK/UNIQUE, FKs, index lead); `RLS ENABLE` +
`FORCE`; runtime role is non-owner, non-`BYPASSRLS`. Normal users → shared project + RLS;
enterprise/regulated → dedicated project.

## Migration (zero-downtime — users already exist)

1 schema → 2 dual-write (D1+Lakebase) → 3 backfill → 4 recompute canonical hashes →
5 shadow-query compare → 6 measure top-K overlap+latency → 7 read cutover → 8 write
cutover → 9 D1 read-only fallback → retire. Dev/staging via Lakebase copy-on-write branches.

## P0 — do now (with status against this repo)

| # | P0 item | Status |
|---|---|---|
| 1 | **Stop sending raw goal in global contribution/queries** | ✅ DONE this session — `aios_agent_system` recall/predict/contribute now send a structural summary only (`_safe_summary`), never the goal. Adversarial test locks it. |
| 2 | Lakebase `tenant_id + RLS + immutable event ledger` | ⏳ needs Lakebase creds — schema designed above |
| 3 | `embedding TEXT` → native vector | ⏳ part of Lakebase migration (worker stores JSON-string vectors today) |
| 4 | Remove embedding/graph extraction from request path | ⏳ worker-plane build |
| 5 | Transactional outbox + worker queue | ⏳ schema designed; build on Lakebase |
| 6 | HA + PgBouncer + read-only path | ⏳ Lakebase provisioning (founder creds) |
| 7 | `/root` `/proof` → incremental Merkle | ⏳ worker-side (deployable now; founder GO) — current full-recompute is unusable at scale |
| 8 | D1 → Lakebase dual-write migration | ⏳ after schema lands |
| 9 | Physically split Private Vault vs Global Aggregate Graph | ⏳ ties to #2; client side already separates (local objects.jsonl vs global D1) |
| 10 | Load-test with real agent event shape | ⏳ after #2–#6 |

**Dependency-gated on founder:** Databricks/Lakebase account + creds (#2,#3,#6,#8), and
any Cloudflare worker redeploy (#7 deploy) is an outward-facing action needing GO.

**Autonomously tractable next (no creds):** #7 incremental-Merkle implementation (code,
not deploy); the SQL schema files (`migrations/`) for #2/#5; the dual-write client shim
design for #8.

## What ships when (head's execution order)

1. ✅ P0 #1 privacy leak — fixed + tested (ralph step 1).
2. Write the canonical SQL schema (ledger/graph/memory/behavior + RLS policies) as
   migration files — reviewable design, no creds.
3. Incremental Merkle (worker code) — replace full-recompute; testable locally.
4. Dual-write client shim (D1 + Lakebase) — behind a flag, off until creds land.
5. Founder provisions Lakebase → migration steps 3–9.
```
Lakebase = canonical · Async Graph Compiler = graph · pgvector+lexical = retrieval ·
edges_current = fast traversal · Delta = history/eval/training · Cloudflare = edge ·
Local agent = device execution
```
