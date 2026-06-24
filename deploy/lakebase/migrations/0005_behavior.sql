-- 0005 — behavioral graph (the CLS corpus the arg-aware capture / cls_gate / cls_train
-- pipeline feeds). This is the per-tenant private behavioral store; the GLOBAL aggregate
-- corpus (the Akashic "every run becomes a star") is the consent-gated, tool-names-only
-- view materialized from here for tenants with tenancy.tenants.consent_global = true.

CREATE TABLE IF NOT EXISTS behavior.patterns (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    pattern_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    category    text,                                  -- code | docs | data | ...
    loop_type   text,                                  -- react_code | exploration | repetitive | ...
    tool_freq   jsonb       NOT NULL DEFAULT '{}'::jsonb,   -- {tool: count} — names only
    top_tools   text[]      NOT NULL DEFAULT '{}',
    arg_skeletons jsonb     NOT NULL DEFAULT '[]'::jsonb,   -- scrubbed (no bodies/secrets)
    intervention_rate real  NOT NULL DEFAULT 0.0,            -- Phase B supervision signal
    confidence  real        NOT NULL DEFAULT 0.75,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, pattern_id)
);
CREATE INDEX IF NOT EXISTS idx_patterns_cat ON behavior.patterns (tenant_id, category, loop_type);

-- P(next_tool | prev_tool) transition stats (the predict_behavior transition score).
CREATE TABLE IF NOT EXISTS behavior.transitions (
    tenant_id  uuid   NOT NULL REFERENCES tenancy.tenants(tenant_id),
    prev_tool  text   NOT NULL,
    next_tool  text   NOT NULL,
    n          bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (tenant_id, prev_tool, next_tool)
);

CREATE TABLE IF NOT EXISTS behavior.outcomes (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    outcome_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    run_id      uuid        NOT NULL,
    exit        text,                                  -- model_finished | error | doom | ...
    reward      real,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, outcome_id)
);

CREATE TABLE IF NOT EXISTS behavior.provider_stats (
    tenant_id   uuid   NOT NULL REFERENCES tenancy.tenants(tenant_id),
    provider    text   NOT NULL,                        -- claude | codex | gemini | local | ...
    metric      text   NOT NULL,
    value       double precision NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider, metric)
);

-- Global aggregate corpus (cross-tenant, consent-gated, tool-names + embedding only).
-- Populated by an aggregator worker from consenting tenants' behavior.patterns — never
-- holds tenant_id-attributable raw content. This is the public Akashic surface.
CREATE TABLE IF NOT EXISTS behavior.global_corpus (
    id          text        PRIMARY KEY,                -- non-reversible hash
    category    text,
    tool_freq   jsonb       NOT NULL DEFAULT '{}'::jsonb,
    top_tools   text[]      NOT NULL DEFAULT '{}',
    embedding   vector(768),                            -- of the STRUCTURAL summary only
    confidence  real        NOT NULL DEFAULT 0.75,
    contributed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_global_hnsw ON behavior.global_corpus
    USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_global_cat  ON behavior.global_corpus (category);
