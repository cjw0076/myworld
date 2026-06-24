-- 0004 — long-term memory + vector retrieval. Embeddings are a REGENERABLE index,
-- not source data. Private (per-tenant) corpus stays here; the global aggregate corpus
-- is separate (0005 behavior + a consent gate) — never co-mingled (the #1 risk at scale).

CREATE TABLE IF NOT EXISTS memory.episodes (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    episode_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    run_id      uuid        NOT NULL,
    summary     text,                                  -- structural/redacted summary (no raw bodies)
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, episode_id)
);

CREATE TABLE IF NOT EXISTS memory.candidates (
    tenant_id    uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    candidate_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    episode_id   uuid,
    content      text        NOT NULL,
    status       text        NOT NULL DEFAULT 'draft'   -- draft-first (DNA #2)
                     CHECK (status IN ('draft','accepted','rejected')),
    created_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, candidate_id)
);

CREATE TABLE IF NOT EXISTS memory.memories (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    memory_id   uuid        NOT NULL DEFAULT gen_random_uuid(),
    kind        text        NOT NULL,                  -- user | feedback | project | reference | ...
    content     text        NOT NULL,
    confidence  real        NOT NULL DEFAULT 0.75,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, memory_id)
);

-- Vectors live in their own table so the search index is independent of row churn and
-- the model/dim can be migrated without touching memories. 768-dim default (bge/nomic).
CREATE TABLE IF NOT EXISTS memory.embeddings (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    memory_id   uuid        NOT NULL,
    model       text        NOT NULL,                  -- provenance: which embedder produced this
    embedding   vector(768) NOT NULL,
    PRIMARY KEY (tenant_id, memory_id, model)
);
-- tenant_id leads a btree so a SELECTIVE tenant filter is exact-then-rank for small
-- private corpora (avoids the pgvector "ANN-scan-then-filter under-returns" trap); the
-- HNSW index serves large/global corpora. Both exist; the query planner picks per filter.
CREATE INDEX IF NOT EXISTS idx_emb_tenant ON memory.embeddings (tenant_id, model);
CREATE INDEX IF NOT EXISTS idx_emb_hnsw   ON memory.embeddings
    USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS memory.retrievals (
    tenant_id    uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    retrieval_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    query_summary text,                                 -- structural query (never raw text)
    hits         jsonb       NOT NULL DEFAULT '[]'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, retrieval_id)
);

CREATE TABLE IF NOT EXISTS memory.feedback (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    feedback_id uuid        NOT NULL DEFAULT gen_random_uuid(),
    memory_id   uuid,
    signal      text        NOT NULL,                  -- used | helpful | wrong | stale | ...
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, feedback_id)
);
