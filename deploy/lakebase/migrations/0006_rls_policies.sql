-- 0006 — Row-Level Security. The tenant boundary, enforced by the DB, not app code.
-- Every tenant-scoped table: RLS ENABLE + FORCE (so even the table owner is constrained
-- in normal use), with a uniform policy tenant_id = tenancy.current_tenant(). The app
-- connects as aios_app (NOLOGIN/NOBYPASSRLS, from 0001); current_tenant() reads the
-- tx-local 'app.tenant_id' GUC and returns NULL when unset → default-deny.

DO $$
DECLARE
    t text;
    tenant_tables text[] := ARRAY[
        'ledger.events', 'control.run_state', 'jobs.outbox',
        'graph.entities', 'graph.entity_aliases', 'graph.claims',
        'graph.claim_evidence', 'graph.claim_relations', 'graph.edges_current',
        'memory.episodes', 'memory.candidates', 'memory.memories',
        'memory.embeddings', 'memory.retrievals', 'memory.feedback',
        'behavior.patterns', 'behavior.transitions', 'behavior.outcomes',
        'behavior.provider_stats'
    ];
BEGIN
    FOREACH t IN ARRAY tenant_tables LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', t);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
            USING (tenant_id = tenancy.current_tenant())
            WITH CHECK (tenant_id = tenancy.current_tenant())
        $f$, t);
        -- read/write for the app role; UPDATE/DELETE granted selectively below.
        EXECUTE format('GRANT SELECT, INSERT ON %s TO aios_app', t);
    END LOOP;
END$$;

-- ledger.events is APPEND-ONLY (DNA #3): app may INSERT/SELECT, never UPDATE/DELETE.
REVOKE UPDATE, DELETE ON ledger.events FROM aios_app;

-- Mutable projections the online write path updates (optimistic version / outbox drain).
GRANT UPDATE ON control.run_state TO aios_app;
GRANT UPDATE ON jobs.outbox       TO aios_app;     -- set dispatched_at
-- Draft lifecycle transitions (status) on claims/candidates are worker-role actions;
-- grant UPDATE there to aios_app too since the review gate runs in-app for now.
GRANT UPDATE ON graph.claims        TO aios_app;
GRANT UPDATE ON graph.edges_current TO aios_app;
GRANT UPDATE ON memory.candidates   TO aios_app;
GRANT UPDATE ON memory.memories     TO aios_app;
GRANT UPDATE ON behavior.patterns   TO aios_app;
GRANT UPDATE ON behavior.transitions TO aios_app;

-- tenancy.tenants: a tenant may read ONLY its own row (no cross-tenant enumeration).
ALTER TABLE tenancy.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenants FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_self ON tenancy.tenants
    USING (tenant_id = tenancy.current_tenant());
GRANT SELECT ON tenancy.tenants TO aios_app;

-- behavior.global_corpus is intentionally CROSS-TENANT (the public aggregate): no RLS,
-- holds no tenant_id and no raw content (tool-names + structural-summary embedding only).
-- The aggregator worker writes it; the app reads.
GRANT SELECT ON behavior.global_corpus TO aios_app;

-- Sequences used by app inserts.
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ledger, control, jobs, graph, memory, behavior, tenancy TO aios_app;
