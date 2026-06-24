-- 0003 — knowledge graph. Built ASYNCHRONOUSLY by the Graph Compiler from
-- ledger.events; NEVER on the request path. Separation:
--   Event   = happened (immutable, 0002)
--   Claim   = extracted, reviewable knowledge (draft → accepted)
--   Edge    = accepted claim unfolded into the current graph projection (disposable)
-- edges_current is a PROJECTION: if the compiler version changes, truncate + rebuild.

CREATE TABLE IF NOT EXISTS graph.entities (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    entity_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    kind        text        NOT NULL,                 -- person | tool | project | concept | ...
    canonical   text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, entity_id)
);

CREATE TABLE IF NOT EXISTS graph.entity_aliases (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    entity_id   uuid        NOT NULL,
    alias       text        NOT NULL,
    PRIMARY KEY (tenant_id, entity_id, alias)
);

-- Claims are draft-first (DNA #2). Idempotent on the compiler signature so a queue
-- retry of the same event never duplicates a claim.
CREATE TABLE IF NOT EXISTS graph.claims (
    tenant_id        uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    claim_id         uuid        NOT NULL DEFAULT gen_random_uuid(),
    subject_id       uuid,
    predicate        text        NOT NULL,
    object_id        uuid,
    object_literal   text,
    status           text        NOT NULL DEFAULT 'draft'    -- draft | accepted | rejected | superseded
                          CHECK (status IN ('draft','accepted','rejected','superseded')),
    confidence       real        NOT NULL DEFAULT 0.5,
    source_event_id  uuid        NOT NULL,
    compiler_name    text        NOT NULL,
    compiler_version text        NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, claim_id),
    UNIQUE (tenant_id, source_event_id, compiler_name, compiler_version, predicate)
);
CREATE INDEX IF NOT EXISTS idx_claims_status ON graph.claims (tenant_id, status);

CREATE TABLE IF NOT EXISTS graph.claim_evidence (
    tenant_id  uuid NOT NULL REFERENCES tenancy.tenants(tenant_id),
    claim_id   uuid NOT NULL,
    event_id   uuid NOT NULL,                          -- evidence_ref into ledger.events (DNA #5)
    PRIMARY KEY (tenant_id, claim_id, event_id)
);

CREATE TABLE IF NOT EXISTS graph.claim_relations (
    tenant_id   uuid NOT NULL REFERENCES tenancy.tenants(tenant_id),
    claim_id    uuid NOT NULL,
    related_id  uuid NOT NULL,
    relation    text NOT NULL,                         -- supports | contradicts | refines | ...
    PRIMARY KEY (tenant_id, claim_id, related_id, relation)
);

-- The fast-traversal projection of ACCEPTED claims. Recomputable from graph.claims.
CREATE TABLE IF NOT EXISTS graph.edges_current (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    src_id      uuid        NOT NULL,
    dst_id      uuid        NOT NULL,
    relation    text        NOT NULL,
    weight      real        NOT NULL DEFAULT 1.0,
    claim_id    uuid        NOT NULL,
    PRIMARY KEY (tenant_id, src_id, relation, dst_id)
);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON graph.edges_current (tenant_id, dst_id, relation);
