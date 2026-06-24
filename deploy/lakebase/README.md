# AIOS AkashicRecord — Lakebase (Postgres) schema

Canonical data store for the SaaS pivot (2026-06-25). Lakebase = source of truth;
knowledge graph is an async projection (see `docs/AIOS_SAAS_LAKEBASE_PLAN.md`).

## Apply

```bash
# against a Lakebase branch (dev first, copy-on-write — never test on production)
for f in migrations/0*.sql; do psql "$LAKEBASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```
Files are idempotent (`IF NOT EXISTS`) and ordered `0001 → 0006`. Use a DIRECT
connection (not the PgBouncer transaction-mode pooler) for migrations — `DO` blocks,
`CREATE EXTENSION`, and session settings don't survive transaction pooling.

## Layout

| file | schema | what |
|---|---|---|
| 0001 | extensions, `tenancy` | pgvector/pg_trgm, `tenants`, `aios_app` role, `current_tenant()` GUC helper |
| 0002 | `ledger` `control` `jobs` | immutable `events`, `run_state` (optimistic version), transactional `outbox` |
| 0003 | `graph` | entities/aliases/claims/evidence/relations + `edges_current` (disposable projection) |
| 0004 | `memory` | episodes/candidates/memories + `embeddings` (vector 768, HNSW) + retrievals/feedback |
| 0005 | `behavior` | CLS corpus (patterns/transitions/outcomes/provider_stats) + `global_corpus` (consent-gated, cross-tenant) |
| 0006 | (all) | RLS ENABLE+FORCE + `tenant_isolation` policy on every tenant table; append-only grant on `ledger.events` |

## Invariants enforced here

- **Tenant isolation by the DB, not app code.** Every tenant table has `tenant_id` in its
  PK and an RLS policy `tenant_id = tenancy.current_tenant()`. The app connects as
  `aios_app` (NOLOGIN/NOBYPASSRLS); set `app.tenant_id` per request (tx-local).
- **Append-only ledger** (DNA #3): `aios_app` has no UPDATE/DELETE on `ledger.events`.
- **Draft-first** (DNA #2): claims/candidates/memories carry a `status` (draft→accepted).
- **Privacy** (DNA #7): no raw bodies in any column — the edge privacy gate writes only
  structural/redacted payloads; `global_corpus` is tool-names + structural-summary
  embedding only, and is the ONLY cross-tenant table.
- **Provenance** (DNA #5): claims cite `source_event_id` + evidence rows into `ledger.events`.

## Check (no Postgres needed)

```bash
python3 validate_schema.py
```
Verifies parens/`$$` balance and — the one that matters — that **every** `tenant_id`
table is covered by an RLS policy in 0006 (a table added without RLS is a cross-tenant
leak; the check fails loudly). Real validation is `psql -f` on a Lakebase branch.

## Status

Schema designed and structure-validated. Pending founder Lakebase/Databricks creds to
apply on a branch, then the D1→Lakebase dual-write migration (plan §Migration).
