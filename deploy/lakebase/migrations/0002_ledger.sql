-- 0002 — the write path: immutable event ledger + run state + transactional outbox.
-- The ONLY things an online request touches. Everything else (graph, embeddings,
-- Merkle) is derived asynchronously by the worker plane from ledger.events.

-- ── ledger.events — immutable source of truth ────────────────────────────────
-- Append-only (DNA #3). No UPDATE/DELETE in the app role (enforced by grants in 0006).
-- payload is structural/redacted at the edge before it ever reaches here (DNA #7):
-- no raw prompts/outputs/secrets — the API gateway's privacy gate owns that.
CREATE TABLE IF NOT EXISTS ledger.events (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    event_id    uuid        NOT NULL DEFAULT gen_random_uuid(),
    run_id      uuid        NOT NULL,
    seq         bigint      GENERATED ALWAYS AS IDENTITY,
    type        text        NOT NULL,                 -- run_started | turn | tool_call | run_finished | ...
    payload     jsonb       NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_events_run   ON ledger.events (tenant_id, run_id, seq);
CREATE INDEX IF NOT EXISTS idx_events_type  ON ledger.events (tenant_id, type, created_at);

-- ── control.run_state — current projection w/ optimistic concurrency ─────────
CREATE TABLE IF NOT EXISTS control.run_state (
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    run_id      uuid        NOT NULL,
    state       text        NOT NULL,                 -- running | finished | failed | ...
    version     bigint      NOT NULL DEFAULT 0,        -- bump on each transition; compare-and-set
    updated_at  timestamptz NOT NULL DEFAULT now(),
    meta        jsonb       NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (tenant_id, run_id)
);

-- ── jobs.outbox — transactional outbox ───────────────────────────────────────
-- Written in the SAME transaction as the event + projection, so a committed event
-- always has its queue message (no dual-write loss). A relay/poller drains it to the
-- worker plane (Graph Compiler, Embedding, Merkle, …) and marks dispatched_at.
CREATE TABLE IF NOT EXISTS jobs.outbox (
    id            bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id     uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    topic         text        NOT NULL,               -- graph_compile | embed | merkle | consolidate | ...
    payload       jsonb       NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    dispatched_at timestamptz                          -- NULL = pending
);
CREATE INDEX IF NOT EXISTS idx_outbox_pending ON jobs.outbox (created_at)
    WHERE dispatched_at IS NULL;

-- Canonical online write path (reference — executed by the Command API):
--   BEGIN;
--   SELECT set_config('app.tenant_id', :tenant, true);
--   INSERT INTO ledger.events (tenant_id, run_id, type, payload) VALUES (...);
--   UPDATE control.run_state SET state=:s, version=version+1, updated_at=now()
--     WHERE tenant_id=:tenant AND run_id=:run AND version=:expected;   -- optimistic
--   INSERT INTO jobs.outbox (tenant_id, topic, payload) VALUES (...);
--   COMMIT;
-- NO LLM extraction / embedding / Merkle / traversal here — workers do that after commit.
