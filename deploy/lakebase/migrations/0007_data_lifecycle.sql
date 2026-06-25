-- 0007 — data lifecycle: crypto-erase, erasure requests, corpus contribution tracking.
-- Reconciles DNA #3 (append-only ledger) with GDPR-class right-to-erasure.
-- Mechanism: per-tenant AES-256-GCM key reference stored here; actual key material
-- lives ONLY in an external KMS. "Erasure" = KMS key destruction; the ciphertext
-- rows in ledger.events remain intact (Merkle chain preserved), but are permanently
-- unreadable. See docs/AIOS_DATA_LIFECYCLE.md for full design rationale.
-- Apply after 0006. Idempotent (IF NOT EXISTS + ADD COLUMN IF NOT EXISTS).

-- ── tenancy.tenant_keys ──────────────────────────────────────────────────────
-- Per-tenant KMS key reference table. Holds the opaque key_id (e.g. AWS KMS ARN
-- or Vault key path) that identifies the tenant's Data Encryption Key (DEK).
-- The DEK wraps all AES-256-GCM ciphertext written to ledger.events.payload.
-- Key material is NEVER stored here — only the KMS reference.
-- status:
--   active  → key exists in KMS; payload rows are decryptable.
--   erased  → KMS key has been irreversibly destroyed; ciphertext is permanently
--             opaque. The ledger row remains; its hash in the Merkle chain is
--             unchanged (hash(ciphertext) = hash(ciphertext) regardless of key).
CREATE TABLE IF NOT EXISTS tenancy.tenant_keys (
    key_ref_id  uuid        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id   uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    key_id      text        NOT NULL,                  -- opaque KMS reference; never the raw key
    status      text        NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'erased')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    erased_at   timestamptz,                           -- set when KMS key destruction is confirmed
    PRIMARY KEY (key_ref_id)
);
CREATE INDEX IF NOT EXISTS idx_tenant_keys_tenant ON tenancy.tenant_keys (tenant_id, status);

-- ── tenancy.erasure_requests ─────────────────────────────────────────────────
-- Append-only provenance record for every erasure or consent-revocation request
-- (DNA #3 + #5). One row per request; status fields advance monotonically as each
-- phase completes. A receipt_id is issued when status reaches 'complete'.
-- Phases (in order):
--   pending             → request received, not yet started
--   key_erased          → KMS key destroyed (ciphertext now unreadable)
--   projections_purged  → regenerable derived tables hard-deleted for this tenant
--   global_decremented  → global_corpus contributor counts decremented
--   complete            → receipt issued; tenant row may now be soft-deleted
CREATE TABLE IF NOT EXISTS tenancy.erasure_requests (
    request_id              uuid        NOT NULL DEFAULT gen_random_uuid(),
    tenant_id               uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    requested_at            timestamptz NOT NULL DEFAULT now(),
    reason                  text,                      -- gdpr_erasure | consent_revoke | account_delete
    status                  text        NOT NULL DEFAULT 'pending'
                                CHECK (status IN (
                                    'pending','key_erased','projections_purged',
                                    'global_decremented','complete'
                                )),
    key_destroyed_at        timestamptz,               -- wall-clock confirmation from KMS
    projections_purged_at   timestamptz,               -- when derived rows were hard-deleted
    global_decremented_at   timestamptz,               -- when global_corpus was decremented
    receipt_id              text        UNIQUE,        -- external correlation id issued on complete
    error_detail            text,                      -- last error for retry diagnostics
    PRIMARY KEY (request_id)
);
CREATE INDEX IF NOT EXISTS idx_erasure_tenant ON tenancy.erasure_requests (tenant_id, status);

-- ── behavior.corpus_contributions ────────────────────────────────────────────
-- Private per-tenant record of exactly which structural delta each tenant
-- contributed to each behavior.global_corpus row. Used ONLY by the aggregator
-- worker during consent_global revocation to perform the exact decrement.
-- NEVER exposed via public APIs (/sync, /predict, or any client-facing endpoint).
-- Rows are deleted from this table once the decrement completes, closing the
-- privacy loop (the contribution mapping itself becomes unnecessary after revocation).
-- contrib_freq: the {tool: count} delta this tenant added to global_corpus.tool_freq.
--              Subtracting it restores the aggregate to pre-contribution state.
CREATE TABLE IF NOT EXISTS behavior.corpus_contributions (
    tenant_id       uuid        NOT NULL REFERENCES tenancy.tenants(tenant_id),
    corpus_id       text        NOT NULL,              -- behavior.global_corpus.id (FK by convention)
    contrib_freq    jsonb       NOT NULL DEFAULT '{}'::jsonb,
    contributed_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, corpus_id)
);

-- ── Column additions to tables owned by earlier migrations ───────────────────
-- These are idempotent (ADD COLUMN IF NOT EXISTS). They extend rather than alter
-- existing rows: NULL / false defaults are safe for pre-existing data.

-- ledger.events.key_id
-- NULL  = plaintext row written before crypto-erase was enabled (pre-existing data).
-- text  = opaque KMS key reference matching tenancy.tenant_keys.key_id;
--         payload is AES-256-GCM ciphertext encrypted at the application layer
--         before the INSERT. Postgres stores bytes; it never sees plaintext.
-- The Merkle worker hashes the raw payload bytes (ciphertext), so hash values are
-- stable regardless of key status. When status becomes 'erased', hash still verifies.
ALTER TABLE ledger.events
    ADD COLUMN IF NOT EXISTS key_id text;

COMMENT ON COLUMN ledger.events.key_id IS
    'KMS key reference for AES-256-GCM payload encryption. '
    'NULL = pre-crypto-erase plaintext row. '
    'When the referenced key is destroyed (tenancy.tenant_keys.status=erased), '
    'payload is permanently unreadable ciphertext; the Merkle hash is unchanged.';

-- behavior.global_corpus.withheld
-- Set to true when contributors drops below min_contributors after a revocation.
-- The serving layer (worker /sync and /predict handlers) MUST filter WHERE withheld = false.
-- Rows are not deleted: they recover to withheld=false if new contributors join.
ALTER TABLE behavior.global_corpus
    ADD COLUMN IF NOT EXISTS withheld boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN behavior.global_corpus.withheld IS
    'k-anonymity enforcement: true when contributors < min_contributors after a revocation. '
    'Serving layer must exclude withheld rows. Resets to false when contributors recovers.';

-- ── RLS for new tenant-scoped tables ─────────────────────────────────────────
-- Applies the same uniform policy as 0006 to the three new tables.
-- Uses pg_policies existence check for idempotency (CREATE POLICY has no IF NOT EXISTS
-- before Postgres 17; this block is safe to re-run on any Postgres version).
DO $$
DECLARE
    t            text;
    schema_name  text;
    table_name   text;
    new_tenant_tables text[] := ARRAY[
        'tenancy.tenant_keys',
        'tenancy.erasure_requests',
        'behavior.corpus_contributions'
    ];
BEGIN
    FOREACH t IN ARRAY new_tenant_tables LOOP
        schema_name := split_part(t, '.', 1);
        table_name  := split_part(t, '.', 2);

        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', t);

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies
            WHERE schemaname = schema_name
              AND tablename  = table_name
              AND policyname = 'tenant_isolation'
        ) THEN
            EXECUTE format(
                $f$CREATE POLICY tenant_isolation ON %s
                   USING (tenant_id = tenancy.current_tenant())
                   WITH CHECK (tenant_id = tenancy.current_tenant())$f$,
                t
            );
        END IF;

        EXECUTE format('GRANT SELECT, INSERT ON %s TO aios_app', t);
    END LOOP;
END$$;

-- erasure_requests: the erasure orchestrator updates status + timestamp fields in place.
GRANT UPDATE ON tenancy.erasure_requests TO aios_app;

-- tenant_keys: status transitions to 'erased' + erased_at stamping during erasure flow.
GRANT UPDATE ON tenancy.tenant_keys TO aios_app;

-- corpus_contributions: the aggregator worker deletes rows once the decrement is done.
GRANT UPDATE, DELETE ON behavior.corpus_contributions TO aios_app;

-- Sequences (covers gen_random_uuid() defaults on the new tables).
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA tenancy, behavior TO aios_app;
