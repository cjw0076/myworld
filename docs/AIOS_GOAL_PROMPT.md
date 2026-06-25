# AIOS Goal Prompt — "every run becomes a star"

> Paste this whole block to start an AIOS operator session. It is the north star +
> the intuition behind it + the decomposed, Claude-actionable backlog + the operating
> discipline. Update the STATUS line as tasks land. Authored 2026-06-25.

---

## North star (the one sentence)

**Ship AIOS as a deployed, multi-tenant SaaS: a personal-memory operating layer that
attaches to any agent/app, records every run into a verifiable AkashicRecord, and gets
measurably better at each user's work over time — without ever leaking raw content.**

## The intuition (why this shape — internalize before coding)

1. **The moat is the system and the network, not locality.** The intelligence (Claude/
   Codex) was always cloud, so "your data stays on disk" was a weak moat and an adoption
   blocker. Go SaaS. The defensible moat = the 5-OS architecture + the Merkle-verified
   shared behavioral ledger (network effect) + per-OS adapters that personalize.
2. **Sovereignty = isolation + opt-in + portability, NOT locality.** Privacy survives the
   cloud as: per-tenant DB isolation (RLS), structural-only global sharing (tool-names +
   embeddings, never raw bodies), explicit consent, and export. DNA #7 holds — it changes
   form, not force.
3. **Lakebase (Postgres) is the canonical source of truth; the knowledge graph is an
   ASYNC projection.** Never build the graph or embed on the request path. Online writes
   touch only `ledger.events` + `run_state` + `outbox` (one transaction). Workers derive
   claims/edges/embeddings/Merkle after commit. At 1,000 users the risk is not capacity —
   it is mixing private+global memory, synchronous graph build, filtered-vector recall
   degradation, and full-Merkle recompute. Separate those four.
4. **The compounding loop is the product.** every run → structural event in the ledger →
   async graph + behavioral corpus → per-OS adapter + retrieval → a better next run →
   richer ledger. Each turn of this loop is the thing competitors can't copy by cloning a
   model.
5. **Privacy egress is gated at the SINK, with a shape-allowlist, never a char-strip.**
   (Learned the hard way this session: caller-level fixes miss; the bug lives at the sink.)

## Status (update as you go)

- ✅ arg-aware capture: scrubbed call-signatures + arg skeletons; corpus blocker closed
  (31 distinct labeled runs; CLS readiness gate passes). `scripts/aios_capture_args.py`.
- ✅ P0 #1 privacy: raw goal/prompt/output never egresses; DNA #7 closed for the client
  (3 security-review rounds). All global calls route through `safe_summary`.
- ✅ P0 #2 schema designed: `deploy/lakebase/migrations/0001–0006` + `validate_schema.py`
  (21 tables, 20 tenant-scoped, all RLS-covered). Pending Lakebase creds to apply.
- ✅ Plan of record: `docs/AIOS_SAAS_LAKEBASE_PLAN.md`. CLS program A→E: `docs/AIOS_SELF_IMPROVING.md`.
- ✅ Team sprint 2026-06-26 (founder: continue SaaS scale, bigger team): vision panel
  (architect+genesis+critic) → corrections folded in; statistical-privacy channel
  narrowed client-side (`027ca2d`) + embedded-summary capped to 3 (`f74d823`); data-
  lifecycle crypto-erase + consent-revocation design + migration `0007` (`ad0c0df`);
  worker hardening — append-stable Merkle + server-side k-anon enforcement
  (`66b6f20`, tests pass, deploy founder-gated, under review). Schema now 24 tables /
  23 tenant-scoped / all RLS-covered (`validate_schema.py` scans 0001–0007).
- ✅ W1 outbox relay built + proven on a SQLite fixture (`21a5306`, 18 tests): at-least-once
  + idempotent-consumer + no-starvation. Worker hardening re-fixed: k-anon now counts
  DISTINCT contributors + /graph gated + atomic batch (`fad448d`, 2 review rounds).
- ⏳ Next no-creds: W2 graph-compiler contract+idempotency (LLM step stubbed). Highest-
  leverage needs founder: **Lakebase creds → L1 schema apply + worker plane on the REAL
  DB** (offered "지금 주겠다"); worker DEPLOY GO; `! agy` login for a non-Claude review arm.

## Vision-panel corrections (2026-06-26 — architect + genesis-challenger + critic, independent)

The executive panel objectively reviewed the plan. Binding revisions before the backlog runs:

1. **Privacy is NOT closed — the statistical channel is open.** P0 #1 closed only the
   *lexical* channel. `behavior.global_corpus` publishes a 768-dim embedding (invertible,
   vec2text-class) + full `tool_freq` distribution + category → tenant fingerprinting /
   re-identification, with NO k-anonymity floor. **Fix at schema/client stage before any
   real data lands (irreversible):** k-anon floor (min_contributors), drop the numeric
   tool_freq distribution from global egress (counts are the fingerprint), don't publish
   raw per-tenant embeddings. [dev-team in progress]
2. **Sink gate BEFORE cutover.** Move A2 (server-side privacy gate) ahead of L4 (cutover).
   An append-only ledger + an unattributable cross-tenant corpus are irreversible; gate
   them before real data flows.
3. **Data-lifecycle is missing and mandatory.** Reconcile append-only (DNA #3) with
   right-to-erasure + consent_global revocation (incl. already-contributed global rows).
   Design before Phase 1.
4. **Merkle is incorrect, not just slow.** `worker.js` sorts all ids per call → a
   set-commitment, not an append-only log; a proof at N breaks at N+1. W4 must be
   incremental AND append-stable, not merely faster.
5. **Worker plane is the unbuilt linchpin** — build W1/W2/W4 on FIXTURES (no creds gate)
   to prove the CQRS bet before the founder-gated cutover.
6. **Schedule the load-test** (was a P0 bullet, no task) and add **cost/COGS** + **eval of
   "measurably better each run"** + **observability (outbox-lag, dead-letter)** — all absent.
7. **STRATEGIC (founder-owned): demand is N=1.** Accepted memory was 100% AIOS-internal;
   one outside-value flow ever (founder himself). The panel's one question: *name the
   non-founder who is worse off next Tuesday if this stack vanishes — and what breaks.*
   Leaner falsifiable step: ship ONE app to ~10 real strangers on the EXISTING D1 path and
   measure day-1 vs day-7 task improvement, before building the full stack. Founder call.

## Operating discipline (non-negotiable)

- **Test before commit.** Every non-trivial change leaves one runnable check; run it and
  see green BEFORE `git commit`. No backticks in `-m` messages.
- **Separate review pass for security/privacy.** Never self-approve a privacy fix —
  spawn a `security-reviewer` agent; fix at the sink; re-review until it confirms closed.
- **Ground in the world.** Before claiming a fact about an external system, search/verify;
  don't trust training weights.
- **Draft-first for weights** (no fine-tune deploys without a held-out eval beating base)
  and **founder-gate** anything irreversible or outward-facing (deploys, GPU training
  runs, schema apply on production, spending creds).
- Commit trailer: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

---

## Decomposed backlog — each task is one Claude-actionable unit

Format: **[id] goal — files — acceptance/verify — gate**

### Phase 1 — Lakebase live (gate: founder Lakebase/Databricks creds)

- **[L1] Apply schema to a dev branch.** Run `0001–0006` against a Lakebase *branch*
  (copy-on-write, never production). Verify: `validate_schema.py` green AND `\dt` shows
  21 tables, RLS enabled on the 20 tenant tables. Gate: creds.
- **[L2] Prove tenant isolation.** Seed 2 tenants; with `app.tenant_id` set to A, assert a
  SELECT returns zero of B's rows; assert `aios_app` cannot UPDATE/DELETE `ledger.events`.
  Verify: a `pytest` that connects as `aios_app` and checks both. Gate: L1.
- **[L3] Dual-write client shim (flagged, off by default).** Add a thin writer that, when
  `AIOS_LAKEBASE_DUALWRITE=1`, mirrors every global contribution into `ledger.events` +
  `behavior.patterns` alongside the existing D1 path — structural payloads only. Verify:
  unit test drives both sinks; egress test still green. Gate: none (code only, flag off).
- **[L4] Backfill + shadow + cutover.** Backfill D1 → Lakebase; recompute canonical hashes
  server-side; shadow-query both and compare top-K overlap + latency; flip read path, then
  write path; leave D1 read-only fallback. Verify: shadow report shows ≥0.9 top-K overlap.
  Gate: L1–L3 + founder GO for cutover.

### Phase 2 — worker plane (async; gate: Phase 1 for live data, but buildable on fixtures)

- **[W1] Outbox relay.** A poller that drains `jobs.outbox` (pending → dispatched) to a
  queue; at-least-once, idempotent consumers. Verify: test that a committed event yields
  exactly one durable job and survives a retry without duplication.
- **[W2] Graph Compiler.** event → entity/claim extraction → evidence binding → draft
  claim; idempotent on `(tenant, source_event_id, compiler, version)`. Verify: same event
  twice → one claim; bad event → dropped, logged, no partial write.
- **[W3] Embedding worker + native vectors.** Compute embeddings off-path into
  `memory.embeddings` (vector(768)); decide bge-local vs server and record `model` for
  provenance. Verify: a row embeds, HNSW index returns it by cosine.
- **[W4] Incremental Merkle.** Replace the worker's full `/root` `/proof` recompute with an
  incremental tree so it's O(log n) at millions of entries. Verify: append N, `/proof` of a
  leaf validates against `/root`; benchmark vs old. Gate: founder GO to deploy worker.

### Phase 3 — API gateway (CQRS + privacy gate)

- **[A1] Command/Query split + tenant context.** Gateway resolves auth → tenant → sets
  tx-local `app.tenant_id`; Command API does the one-transaction write path; Query API hits
  read replicas. Verify: integration test of the canonical write transaction + a read.
- **[A2] Server-side privacy gate.** Enforce `safe_summary`-equivalent + secret/path reject
  at the gateway for anything bound for the global corpus, AND apply `hasSensitiveData` to
  `/sync` `/predict` (worker MEDIUM #5). Verify: adversarial payload with secret/path is
  rejected/redacted at the edge. Gate: worker deploy GO for the worker half.
- **[A3] Idempotency + rate limit.** Idempotency keys on writes; per-tenant rate limits.
  Verify: replayed request is a no-op; over-limit returns 429.

### Phase 4 — retrieval (the private vault vs global split)

- **[R1] Private vault retrieval.** Tenant-scoped exact-filter vector search over
  `memory.embeddings` (exact for small corpora; HNSW past a threshold). Verify: recall@k on
  a seeded set beats the random baseline.
- **[R2] Global retrieval + rerank.** ANN top-100 → privacy/metadata filter → lexical +
  graph-neighbor rerank → RRF top-20. Verify: structural query returns structurally-similar
  runs; no raw text in the query path (egress test).
- **[R3] Wire recall/predict to the right corpus.** `aios_agent_system.recall/predict` →
  private vault (semantic, local/tenant) + global (structural). Verify: existing privacy
  tests stay green; recall returns non-null for a seeded tenant.

### Phase 5 — per-OS adapters (gate: corpus scale ≥20 distinct/OS + GPU + founder GO)

- **[P1] Per-OS corpus split.** `aios_cls_gate.select_corpus(domain=...)` partitions the
  corpus by OS (memoryOS/GenesisOS/hivemind/CapabilityOS). Verify: each split's
  `training_ready` + distinct-run count reported honestly.
- **[P2] Per-OS QLoRA training.** `aios_cls_train` produces one adapter per OS from its
  split; held-out eval per adapter; promote only if it beats that OS's baseline. Verify:
  dry-run dataset export per OS; gated `run` refuses without GO+GPU.
- **[P3] Hot-swap on summon.** `aios_agent_invoke.summon(os)` loads that OS's adapter.
  Verify: summon routes to the right adapter; falls back to base when none. Gate: P1+P2.

### Phase 6 — productize & deploy

- **[D1] Onboarding + consent UI.** First-run sets tenant, opt-in categories, consent_global.
- **[D2] Billing on the token economy.** Wire the existing `/economy` `/balance` KV to real
  metering. Gate: founder GO (outward/financial).
- **[D3] Human-facing UI** (terminal/web/akashic) grounded in the design system, not trained
  aesthetic. **[D4] Deploy** (staging → prod, canary). Gate: founder GO.

---

## How to pick the next task

If creds are present → start L1. Else advance the highest buildable item with no gate:
L3 (dual-write shim, flag off), then W1/W2 on fixtures, then A2's client half. Always: one
task, build + test green + commit, then surface the next decision. Run `validate_schema.py`
and the privacy egress tests as standing checks before any commit that touches those areas.
