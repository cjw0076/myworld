# Uri Personal Agent Pivot — 2026-05-12

Surface raised by `claude@uri` after the founder's 2026-05-12 KST dump and reconciled with `codex@uri`'s in-flight work. This is a discovery, not a contract — the operator pair packages it into the first post-ASC-0032 Uri contract.

## Founder Statement (summary, no raw transcript)

Primary Uri loop is a personal memory / agent loop, not a B2B2C campus operating layer:

1. entry activity (campus entry)
2. action activity (place / record capture)
3. memory store
4. experience entry (extracting "experiences" from accumulated records)
5. guided funnel (onboarding that pulls the user through the loop)
6. knowledge repo + AI agent — personal asset-ization of Notion, personal study files, school LMS, official university sites via **self-ingest**
7. digital secretary / agent / avatar

Temporal moat: experiences only available during Korean university years.

Directive: all Uri development must route through AIOS — Hive Mind for execution, MemoryOS for memory lifecycle, CapabilityOS for routing. Improvements found while working in `uri/` are surfaced up to `myworld/`.

## What `codex@uri` has already shipped (2026-05-12)

The doc-level pivot is already executed inside `uri/`:

- `docs/URI_NORTHSTAR.md` — rewritten with the temporal-moat thesis ("Korean university years").
- `docs/PRODUCT_BRIEF.md` — wedge order reordered: **personal agent loop** → temporal campus experiences → mission control → Club OS → marketplace → workflow assets.
- `docs/MEMORY_POLICY.md` — gained a **Self-Ingest Policy** section (allowed sources, not-allowed sources, storage requirements, prototype rule).
- `docs/URI_PERSONAL_AGENT_LOOP.md` — new authoritative seven-step doc with route plan `/u/[schoolSlug]` → `/me` → `/memory` → `/connect`.
- `products/digital-campus/ROUTE_ARCHITECTURE.md`, `U_SCHOOLSLUG_PROTOTYPE_SPEC.md`, `SERVICE_CONCEPT.md` — product surface specs.
- `hive/packets/URI-001`, `URI-002` — Uri-local hive packets (market/service strategy + Sprint 001 web prototype).
- `memory/drafts/2026-05-12-personal-agent-loop.md`, `2026-05-12-sprint-001-web-prototype.md` — codex draft memories.
- `capabilities/web-prototype-routing-2026-05-12.md` — Uri-local capability candidate.
- `package.json` + `next.config.ts` + `src/` — Next.js App Router scaffold; Sprint 001 status `in_progress`.

`claude@uri` added `CLAUDE.md` + `memory/drafts/2026-05-12-personal-agent-loop-claude-review.md` — narrative/policy review only, no edits to codex's docs.

## Remaining gaps after codex's work

Two policy gaps and one routing tension are still open:

1. **`avatar` operational definition.** `URI_PERSONAL_AGENT_LOOP.md` defines avatar at the user-facing layer but does not say whether the underlying per-user store is a MemoryOS user-instance or a separate Uri-local graph importing accepted memories. CapabilityOS routing and the consent surface design depend on this.
2. **Self-ingest consent surface.** `MEMORY_POLICY.md` allows self-ingest sources and requires "explicit user consent before AI agent use" but does not specify per-source granularity (Notion workspace vs page, LMS course vs assignment), revocation path (including whether derived embeddings forget), or visibility split (`public` / `school-visible` / `private`) per ingested object.
3. **Sprint 001 routing tension.** `hive/packets/URI-002` authorizes implementation **inside the Uri repo** (Next.js App Router in `uri/src/`). Founder directive is "무조건 AIOS 통해 개발." Two readings: (a) `uri/hive/packets/` *is* the durable hive layer for Uri-local product code — packet + draft + capability candidate triplet satisfies the directive; (b) real execution should move to `hivemind/` via a MyWorld ASC dispatch, with `uri/` keeping only narrative/policy/draft surfaces. The operator pair has to choose.

The 2026-05-11 `docs/discoveries/2026-05-11-jaewon-search.md` classification of Uri as "No absorption; remain reference projects" is now twice superseded (by ASC-0032 and by this pivot). Worth annotating in a follow-up entry — discoveries are append-only, not rewritten.

## Candidate ASC scope

A single follow-on contract is preferable to several small ones, because the gaps must move together — partial updates would create contradictory drafts in flight. Suggested work packets:

- **WP-A — `claude@uri`**: lock the operational definition of `avatar` (writes a short section into `URI_PERSONAL_AGENT_LOOP.md` and `MEMORY_POLICY.md`) and add a consent-surface section to `docs/MEMORY_POLICY.md` covering granularity, revocation, and visibility. Narrative + policy only, no code.
- **WP-B — MemoryOS**: define `self_ingest` as a first-class memory layer with provenance fields, per-source granularity, and revocation semantics. Decide whether the Uri per-user store is a MemoryOS user-instance (depends on WP-A).
- **WP-C — CapabilityOS**: build a recommendation surface for Notion / LMS / school-site self-ingest with explicit risk notes and fallback plans for missing OAuth surfaces. Pick the first source here.
- **WP-D — `codex@uri` Sprint 001 close-out**: reach the existing URI-002 verification gate (`npm run typecheck`, `npm run build`, route browser check), append the receipt to `uri/docs/AGENT_WORKLOG.md`, then pause. No Sprint 002 without a routing decision.
- **WP-E — Hive Mind**: only opens if the routing decision in WP-D is "dispatch to `hivemind/`." Otherwise this packet is `not_applicable` and `uri/hive/packets/` continues as the durable hive layer for Uri-local product code.

## Decisions the operator pair still needs to lock

1. `avatar` = MemoryOS user-instance, or separate Uri-local graph?
2. First self-ingest source — Notion (clean OAuth, low risk), LMS (highest value, credentialed, varies per school), or 공식 홈페이지 (public, lower signal)?
3. Sprint 002 routing — stay in `uri/` or dispatch to `hivemind/`?
4. Pivot vs supplement confirmation — `PRODUCT_BRIEF.md` already executes the pivot (wedge #1 = personal agent loop). Confirm this is the intended end state, not an intermediate draft codex shipped pre-directive.

## Holds

- No real Notion / LMS / school-page ingestion until WP-A consent-surface lands.
- No real student data leaves the founder's local machine until WP-A + WP-B + WP-C have all closed.
- No new Uri sprint kicks off until WP-D verification is recorded and the routing decision is made.
