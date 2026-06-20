# AIOS Production Hosting Runbook

> Last updated: 2026-06-20 | Maintained by: claude@myworld

---

## Current Production Surfaces

### 1. Akashic Record Worker (LIVE)

| Property | Value |
|----------|-------|
| URL | `https://aios-akashic.cjw070690.workers.dev` |
| Infra | Cloudflare Worker + D1 SQLite |
| Purpose | Append-only distributed memory / Merkle audit |
| Entry count | 1,509 (as of 2026-06-20) |
| Schema | `aios.akashic_record.v2` |

**Key endpoints:**
```
GET  /status       → entry counts by category/provider
GET  /root         → current Merkle root hash + entry_count
POST /contribute   → ingest a new memory record
POST /recall       → semantic search
GET  /checkpoints  → public audit checkpoint list
```

**Deploy command:**
```bash
cd deploy/akashic-worker
npx wrangler deploy
```

**Verify live:**
```bash
curl https://aios-akashic.cjw070690.workers.dev/status | jq .total
curl https://aios-akashic.cjw070690.workers.dev/root | jq .root_hash
```

---

### 2. End-User Serving (PENDING public URL)

Local surfaces exist but no public URL is live yet:

| App | Local port | Status |
|-----|-----------|--------|
| `apps/control` | 5173 | Local dev only |
| `apps/serving` | TBD | Local dev only |
| `apps/akashic-ui` | TBD | Local dev only |

**Gap:** `public_url.json → end_user_serving.public_url` is null until deployed.

**Deploy path (Cloudflare Pages):**
```bash
# 1. Build
cd apps/control && npm run build

# 2. Deploy
npx wrangler pages deploy dist --project-name aios-control

# 3. Update proof
# Edit .aios/serving/proofs/public_url.json → end_user_serving.public_url
```

---

## Distinction: Akashic Infra vs End-User Serving

The audit (ASC-0279) requires these to be treated separately:

- **Akashic Worker** = memory infrastructure. Not the product.
- **End-user serving** = dashboard/CLI the user actually visits.

Both can share Cloudflare infra but serve different audit criteria.

---

## Akashic Worker: Incident Runbook

### Worker not responding
```bash
# Check CF dashboard or:
curl -I https://aios-akashic.cjw070690.workers.dev/status
# If 5xx: check D1 binding in wrangler.json and CF dashboard
```

### D1 schema drift
```bash
cd deploy/akashic-worker
# Re-apply migrations:
npx wrangler d1 execute aios-akashic --file=migrations/0001_init.sql
```

### Checkpoint verification
```bash
python3 scripts/aios_agent_behavior.py checkpoint
cat docs/akashic_checkpoints.jsonl | tail -1
curl https://aios-akashic.cjw070690.workers.dev/checkpoints | jq .
```

---

## Evidence Links

- `.aios/serving/proofs/public_url.json` — structured URL proof record
- `docs/akashic_checkpoints.jsonl` — public audit trail
- `deploy/akashic-worker/wrangler.json` — CF Worker config
- `docs/contracts/ASC-0279-world-service-objective-audit.md` — audit source
