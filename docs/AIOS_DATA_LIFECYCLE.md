# AIOS Data Lifecycle — Crypto-Erase and Right-to-Erasure Design

**Status:** Design complete. Schema migration: `deploy/lakebase/migrations/0007_data_lifecycle.sql`.
**Applies to:** All tenants on the shared Lakebase project. Dedicated-project tenants
inherit the same design; their KMS keys live in a separate AWS KMS keystore.

---

## 1. The Contradiction and Its Resolution

AIOS DNA invariant #3 states: the ledger is append-only — no row in `ledger.events` is
ever deleted or modified. This is what makes the Merkle chain tamper-evident and the
audit history durable.

GDPR Article 17 (and equivalent laws) grants data subjects the right to erasure of their
personal data "without undue delay." For SaaS with real tenants this is not optional: a
single unable-to-erase incident can void the data-processing agreement.

These two requirements are not irreconcilable. The key insight: **GDPR does not require
destroying the physical record — it requires destroying the ability to read personal data
from it.** EU GDPR Recital 26 defines "personal data" as data that "could be attributed to
a natural person." Once the encryption key is irreversibly destroyed, the remaining
ciphertext cannot be attributed to anyone; it is no longer personal data under the
regulation's own definition. UK ICO guidance and French CNIL both formally accept
crypto-erasure as equivalent to deletion for encrypted data where key destruction is
verifiable. AWS KMS provides a tamper-evident deletion certificate; HashiCorp Vault
provides an audit log entry. Either satisfies the GDPR Article 5(2) accountability
requirement.

The reconciliation:

| Requirement | How it is satisfied |
|---|---|
| DNA #3: no row deleted | Ciphertext row stays in ledger. Hash unchanged. Merkle verifies. |
| GDPR: data must be erasable | AES-256-GCM key destroyed → ciphertext is computationally unreadable. |
| DNA #5: provenance chain | `ledger.events.key_id` ties the ciphertext to the key reference. `tenancy.erasure_requests` records the destruction with timestamps. |
| DNA #7: privacy boundary | `tenancy.tenant_keys` never stores key material — only the KMS reference. |

---

## 2. Crypto-Erase: How It Works

### 2.1 Encryption before write (application layer)

All `payload` data written to `ledger.events` for a crypto-erase-enabled tenant is
encrypted at the application layer **before** the INSERT reaches Postgres:

```
plaintext_payload (JSON)
    → AES-256-GCM encrypt with DEK
    → ciphertext_bytes  (stored in ledger.events.payload as bytea / base64-encoded text)
    → key_id (KMS reference string) stored in ledger.events.key_id
```

The Data Encryption Key (DEK) is a random 256-bit symmetric key. It is itself wrapped
(envelope-encrypted) by the tenant's Key Encryption Key (KEK) that lives in the KMS.
The application calls the KMS to decrypt the DEK on each read; the DEK never persists
in the application process memory beyond a single decrypt operation.

Postgres never sees the plaintext or the raw DEK. It stores:
- `payload`: opaque ciphertext bytes
- `key_id`: opaque KMS reference string (e.g. `arn:aws:kms:us-east-1:123:key/abc`, or a
  Vault path like `transit/keys/tenant-<uuid>`)

### 2.2 Key-reference table (`tenancy.tenant_keys`)

One row per active key per tenant. A key rotation creates a new row; old rows stay to
decrypt historical events written under the old key. The `status` column tracks:

- `active` — KMS key exists; events encrypted under this key_id are decryptable.
- `erased` — KMS key has been irreversibly destroyed. The `erased_at` timestamp records
  when the KMS deletion was confirmed. Events encrypted under this key_id are permanently
  unreadable ciphertext.

Key rotation does not itself trigger erasure. Erasure is a separate, explicit step.

### 2.3 Erasure = key destruction

To erase a tenant's data:

1. Call the KMS delete-key API (AWS KMS schedules deletion with a mandatory 7–30 day
   grace window; Vault `transit` keys support immediate revocation). The KMS issues a
   signed deletion receipt.
2. Set `tenancy.tenant_keys.status = 'erased'`, `erased_at = now()`.
3. After the KMS grace window expires (or immediately for Vault), no key material exists
   anywhere that can decrypt the ciphertext in `ledger.events`.

### 2.4 Why the Merkle chain is intact

The Merkle worker computes each node as:

```
node_hash = SHA256(prev_hash || seq || type || SHA256(raw_payload_bytes))
```

`raw_payload_bytes` is the **ciphertext** that was stored in Postgres. Key destruction
does not change the ciphertext bytes — it only makes them uninterpretable. Therefore:

- `SHA256(raw_payload_bytes)` is identical before and after key erasure.
- All Merkle hashes remain valid.
- An auditor can still verify the chain is complete and untampered.

What the auditor **cannot** recover is what the event said — which is exactly the point.
The chain proves "an event of type X occurred at time T for tenant UUID Y." The type
column is structural (e.g. `run_started`, `tool_call`) and must never contain PII; this
is enforced at the privacy gate before the INSERT.

### 2.5 Pre-existing plaintext rows (migration path)

The existing schema stores `payload` as plaintext `jsonb`. Migration to encrypted
payloads proceeds in two phases:

**Phase A — new data only (immediate, post-0007):**
New tenants onboarded after 0007 is applied always write encrypted payloads. The
application checks `tenancy.tenant_keys` at connection time; if a row exists with
`status='active'`, it encrypts before writing and stores `key_id`. Plaintext rows have
`key_id IS NULL`.

**Phase B — backfill (deferred, founder-gated):**
Existing plaintext rows (where `key_id IS NULL`) are re-encrypted in a background job:
1. Fetch batch of rows WHERE `key_id IS NULL` for the tenant.
2. Decrypt (they are already plaintext — no-op decrypt).
3. Re-encrypt with the tenant's active DEK.
4. UPDATE `payload = ciphertext`, `key_id = :key_id` in a single atomic statement.
   This is the ONLY case where `ledger.events` rows are updated; it is a one-time
   migration that converts plaintext to ciphertext and is authorized as an explicit
   data-migration contract, not normal app-path writes.

Until Phase B completes, erasure of a tenant with pre-existing plaintext rows is partial.
The policy: block erasure request completion until backfill is confirmed, or scope
the GDPR obligation to "data written after consent_global opt-in date."

**Required ALTER (already in 0007):**
```sql
ALTER TABLE ledger.events ADD COLUMN IF NOT EXISTS key_id text;
```

---

## 3. Consent_global Revocation Flow

### 3.1 The k-anonymity problem

`behavior.global_corpus` is deliberately cross-tenant: it holds aggregate tool-frequency
patterns across all consenting tenants with no `tenant_id` column. This k-anonymity
design prevents fingerprinting a single tenant via the global corpus.

The problem: when a tenant revokes `consent_global`, we must remove their contribution
from the aggregate — but the aggregate has no per-tenant attribution. If we stored the
attribution, we would break k-anonymity.

### 3.2 Solution: private contribution mapping

`behavior.corpus_contributions` (new in 0007) holds one row per `(tenant_id, corpus_id)`
pair with the exact `contrib_freq` delta the tenant added to that global corpus row.
This table is:
- Per-tenant (tenant_id FK, RLS-isolated).
- NEVER exposed via any public API or query surface.
- Deleted as part of the revocation procedure once the decrement completes.

The contribution mapping is the minimum information needed to perform an exact decrement.
It does not re-introduce per-tenant data into the global corpus; it is only read during
the revocation procedure and then destroyed.

### 3.3 Decrement procedure (executed by aggregator worker)

When `consent_global` is revoked for tenant T (either via settings update or as part of
a full erasure request):

**Step 1.** Fetch all rows in `behavior.corpus_contributions` WHERE `tenant_id = T`.

**Step 2.** For each contribution row `(corpus_id, contrib_freq)`:
  - Execute within a transaction:
    ```sql
    UPDATE behavior.global_corpus
    SET
        tool_freq   = tool_freq - contrib_freq,    -- JSONB subtraction (key-by-key decrement)
        contributors = contributors - 1,
        withheld    = (contributors - 1 < min_contributors),
        contributed_at = now()
    WHERE id = :corpus_id;
    ```
  - If `contributors` drops to 0: delete the row (no data remains; deletion is safe because
    global_corpus is a projection, not source data — DNA #3 does not apply to projections).
  - If `contributors` drops below `min_contributors` but is > 0: set `withheld = true`.
    The serving layer's WHERE clause (`WHERE withheld = false`) prevents this row from
    being returned on `/sync` or `/predict` requests. The row survives for future recovery.

**Step 3.** Recompute `top_tools` for each affected corpus row from the updated `tool_freq`.

**Step 4.** If the corpus row has an `embedding` (computed from structural data that
included this tenant's contribution), schedule a re-embedding job in `jobs.outbox`. The
stale embedding is harmless while `withheld = true`; re-embedding fires when the corpus
row becomes servable again.

**Step 5.** DELETE all `behavior.corpus_contributions` rows for tenant T. The mapping is
no longer needed; retaining it would be unnecessary data retention.

**Step 6.** Update `tenancy.tenants.consent_global = false` (if not already set).

### 3.4 k-anonymity floor enforcement after decrement

After the decrement, the aggregator enforces:
- `withheld = true` if `contributors < min_contributors` (default 5).
- Serving layer (Cloudflare worker `/sync` and `/predict`) filters `WHERE withheld = false`.
- A corpus row recovers to `withheld = false` when a new consenting tenant contributes
  and `contributors` crosses back above `min_contributors`.

This ensures that a corpus row that drops to, say, 3 contributors after a revocation is
not exposed even though it still contains aggregate data.

---

## 4. Retention Policy

### 4.1 Data classification

| Data class | Storage | Erasure method | DNA #3 applies? |
|---|---|---|---|
| Ledger events | `ledger.events.payload` (ciphertext) | Crypto-erase (key destroy) | Yes — row never deleted |
| Graph projections | `graph.edges_current`, `graph.claims` | Hard delete (regenerable from events) | No — projection |
| Memory embeddings | `memory.embeddings` | Hard delete (regenerable from memories) | No — projection |
| Memory content | `memory.memories`, `memory.candidates` | Hard delete (structural content only; PII prevented at edge) | No — projection |
| Behavior patterns | `behavior.patterns`, `behavior.transitions`, `behavior.outcomes` | Hard delete (projection from events) | No — projection |
| Global corpus contribution | `behavior.global_corpus` (aggregate) | Decrement + withheld flag | No — projection |
| Contribution mapping | `behavior.corpus_contributions` | Delete on revocation complete | No — lifecycle metadata |
| Key reference | `tenancy.tenant_keys` | Mark erased; row retained for audit | No — lifecycle metadata |
| Erasure receipt | `tenancy.erasure_requests` | Retained indefinitely (audit) | Append-only by policy |
| Run state | `control.run_state` | Hard delete | No — projection |
| Outbox | `jobs.outbox` | Hard delete after dispatch | No — transient |

**Hard-deletable (projections, embeddings):** These are regenerable from `ledger.events`.
Deleting them reclaims storage and satisfies erasure for derived personal data without
requiring cryptographic guarantees.

**Crypto-erased (ledger.events):** The source record. Not deleted; key destroyed.

**Retained for audit (erasure_requests, tenant_keys):** These rows contain no personal data
(only UUIDs, timestamps, KMS references). They are the provenance chain required by
DNA #5 and the accountability trail required by GDPR Article 5(2).

### 4.2 TTL tiers

| Table | Default TTL | Rationale |
|---|---|---|
| `ledger.events` | No TTL (append-only; crypto-erase on request) | Source of truth; deletion forbidden |
| `jobs.outbox` | 7 days after `dispatched_at IS NOT NULL` | Transient relay; no long-term value |
| `memory.retrievals` | 90 days | Query history; no long-term value |
| `memory.episodes` | No TTL (summarized behavioral record) | Needed for memory reconstruction |
| `graph.edges_current` | Rebuilt on compiler version bump | Disposable projection |
| `behavior.corpus_contributions` | Deleted on revocation | Single-use lifecycle metadata |

TTLs are enforced by a background worker job (not in this schema; see `jobs.outbox`
topic `ttl_sweep`). They apply in addition to, not instead of, the erasure flow.

---

## 5. Erasure Request Flow (End-to-End)

### 5.1 The five steps

1. **Request received.** Tenant calls `DELETE /account` or `POST /data/erasure-request`.
   A row is inserted into `tenancy.erasure_requests` (status `pending`). The request
   triggers consent_global revocation immediately (steps 2 and 3 of §3.3 fire for the
   behavior data).

2. **Key destruction.** The erasure orchestrator calls the KMS delete-key API for all
   active keys in `tenancy.tenant_keys` for this tenant. On confirmation:
   - `tenancy.tenant_keys.status = 'erased'`, `erased_at = now()` for each key.
   - `tenancy.erasure_requests.key_destroyed_at = now()`, status → `key_erased`.
   From this moment, all AES-256-GCM ciphertext in `ledger.events.payload` for this
   tenant is permanently unreadable. The Merkle chain continues to verify.

3. **Projection purge.** Hard-delete all regenerable rows for the tenant from:
   `memory.embeddings`, `memory.memories`, `memory.candidates`, `memory.episodes`,
   `graph.edges_current`, `graph.claims`, `graph.claim_evidence`, `graph.claim_relations`,
   `graph.entities`, `graph.entity_aliases`, `control.run_state`, `behavior.patterns`,
   `behavior.transitions`, `behavior.outcomes`, `behavior.provider_stats`,
   `memory.retrievals`, `memory.feedback`, `jobs.outbox`.
   Update: `tenancy.erasure_requests.projections_purged_at = now()`, status →
   `projections_purged`.

4. **Global corpus decrement.** Execute the procedure in §3.3 steps 1–6. Update:
   `tenancy.erasure_requests.global_decremented_at = now()`, status → `global_decremented`.

5. **Receipt issued.** Set `tenancy.erasure_requests.status = 'complete'`, assign a
   `receipt_id` (UUID or opaque token returned to the tenant for their compliance records).
   Optionally soft-delete or anonymize the `tenancy.tenants` row (replace slug, settings
   with tombstone values; retain the UUID as a dead FK anchor for the erasure_requests
   audit row). The `ledger.events` rows remain as opaque ciphertext — the audit chain
   showing that a tenant existed and had activity is preserved; their data is not.

### 5.2 Error handling and idempotency

Each phase is idempotent: re-running the orchestrator after a failure re-checks the KMS
key status and the timestamp fields before repeating work. The `status` field is the
checkpoint; a crashed orchestrator resumes from the last completed phase.

KMS key destruction is idempotent (destroying an already-destroyed key is a no-op or a
well-defined "key not found" response). Projection hard-deletes are idempotent (DELETE
WHERE tenant_id = X has no effect if already deleted). Global corpus decrements use
`behavior.corpus_contributions` rows as the source of truth; once those rows are deleted
(step 5 of §3.3), the decrement cannot run again, preventing double-decrement.

### 5.3 Compliance artifacts

On request completion the system can generate a GDPR erasure certificate containing:
- `erasure_requests.request_id` (UUID)
- `erasure_requests.receipt_id`
- Timestamps for each phase
- The KMS deletion certificate (from AWS / Vault)
- Confirmation that `contributors` was decremented for all affected corpus rows

This artifact satisfies Article 5(2) accountability and can be provided to a supervisory
authority on request.

---

## 6. Schema Changes Summary

### 6.1 New tables (in 0007)

| Table | Schema | Purpose |
|---|---|---|
| `tenancy.tenant_keys` | tenancy | KMS key reference per tenant; status tracks active vs erased |
| `tenancy.erasure_requests` | tenancy | Append-only audit log of erasure request lifecycle |
| `behavior.corpus_contributions` | behavior | Private contribution mapping for global corpus decrement |

All three have `tenant_id`, RLS enabled/forced, and `tenant_isolation` policy in 0007.

### 6.2 Column additions to existing tables (in 0007, idempotent)

| Column | Table | Added by | Semantics |
|---|---|---|---|
| `key_id text` | `ledger.events` | 0007 `ADD COLUMN IF NOT EXISTS` | KMS key ref; NULL = plaintext |
| `withheld boolean` | `behavior.global_corpus` | 0007 `ADD COLUMN IF NOT EXISTS` | k-anon floor enforcement |

### 6.3 Required ALTERs NOT in 0007 (deferred, require founder gate)

These changes touch the application write path and require a coordinated deploy:

1. **`ledger.events.payload` type change (deferred):** The current column is `jsonb`.
   Encrypted payloads are binary (`bytea`) or base64-encoded `text`. The application can
   handle this transparently (base64 in a text column is the lowest-friction path), but
   a formal type migration requires a maintenance window. Until then, plaintext rows
   coexist with ciphertext rows distinguished by `key_id IS NULL`.

2. **Worker-side decryption on read (deferred):** The Cloudflare worker currently reads
   `payload` and forwards it to the client. After crypto-erase is enabled, the worker
   must call the KMS to decrypt before forwarding. This is a behavioral change in the
   hot read path and requires a worker deploy (already founder-gated per README §Residual).

3. **Aggregator contrib_freq tracking on write (deferred):** The aggregator worker must
   write to `behavior.corpus_contributions` every time it promotes a tenant's pattern
   to `global_corpus`. This requires a worker deploy.

---

## 7. DNA Invariant Compliance

| DNA # | Invariant | How this design complies |
|---|---|---|
| #1 Recommendation-only | No auto-binding | Erasure requires explicit tenant request or operator action; never auto-triggered. |
| #2 Draft-first | Memory changes require review | Projection purge (step 3) is a direct hard-delete; this is acceptable because these are derived data, not source records. The source record (ledger.events) is never deleted. |
| #3 Append-only audit | No record destroyed | ledger.events rows are never deleted or updated (except the one-time Phase B backfill which is a data migration, not an app-path operation). Erasure receipts are also append-only. |
| #4 Stop conditions named | Every loop has an exit | Erasure request has five named statuses; each is a named exit condition. Decrement loop exits when corpus_contributions is empty. |
| #5 Provenance chain | Every record cites evidence | ledger.events.key_id → tenancy.tenant_keys. erasure_requests records each phase timestamp. corpus_contributions records the exact delta. |
| #6 Operator override | Override always possible | The operator can pause an erasure request mid-flight by setting error_detail and halting the orchestrator. KMS keys with a pending-deletion grace window can be restored within that window. |
| #7 Private-gated data | Private data stays out of dispatch and prompt artifacts | key_id is an opaque KMS reference (no secrets). corpus_contributions is never exposed via public APIs. KMS key material is never written to Postgres. |
