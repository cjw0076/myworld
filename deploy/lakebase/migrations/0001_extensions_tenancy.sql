-- AIOS AkashicRecord on Lakebase (Postgres) — 0001 extensions + tenancy
-- Founder pivot 2026-06-25: Lakebase = canonical source of truth.
-- Apply order: 0001 → 0006. Idempotent (IF NOT EXISTS) — safe to re-run.
-- Core extensions only (pgvector/pg_trgm); lakebase_vector/lakebase_text are Beta and
-- stay behind feature flags, never in the base schema.

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector 0.8 (HNSW/IVFFlat)
CREATE EXTENSION IF NOT EXISTS pg_trgm;      -- lexical / fuzzy
-- tsvector + GIN are built-in.

CREATE SCHEMA IF NOT EXISTS ledger;
CREATE SCHEMA IF NOT EXISTS control;
CREATE SCHEMA IF NOT EXISTS jobs;
CREATE SCHEMA IF NOT EXISTS graph;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS behavior;
CREATE SCHEMA IF NOT EXISTS tenancy;

-- ── Tenants ──────────────────────────────────────────────────────────────────
-- Normal users/teams share this project with RLS isolation; whales get a dedicated
-- Lakebase project (not a row here). consent_global gates whether this tenant's
-- structural (tool-names-only) summaries may join the global aggregate corpus.
CREATE TABLE IF NOT EXISTS tenancy.tenants (
    tenant_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug           text UNIQUE NOT NULL,
    tier           text NOT NULL DEFAULT 'shared'        -- shared | dedicated
                       CHECK (tier IN ('shared', 'dedicated')),
    consent_global boolean NOT NULL DEFAULT false,         -- opt-in (DNA #7)
    created_at     timestamptz NOT NULL DEFAULT now(),
    settings       jsonb NOT NULL DEFAULT '{}'::jsonb
);

-- ── Runtime role + tenant-context helper ─────────────────────────────────────
-- The application connects as a NON-owner, NON-BYPASSRLS role; RLS policies (0006)
-- read the tenant id from a transaction-local GUC set per request:
--     SELECT set_config('app.tenant_id', '<uuid>', true);   -- true = tx-local
-- current_tenant() returns NULL when unset → policies deny by default.
CREATE OR REPLACE FUNCTION tenancy.current_tenant() RETURNS uuid
    LANGUAGE sql STABLE AS $$
    SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aios_app') THEN
        CREATE ROLE aios_app NOLOGIN NOBYPASSRLS;     -- grant to the login role used by the API
    END IF;
END$$;

GRANT USAGE ON SCHEMA ledger, control, jobs, graph, memory, behavior, tenancy TO aios_app;
