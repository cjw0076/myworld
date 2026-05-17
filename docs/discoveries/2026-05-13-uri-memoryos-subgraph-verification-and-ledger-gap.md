# Uri MemoryOS Subgraph Verification + Ledger Gap

- date: 2026-05-13 KST
- source repo: `uri`
- observed by: codex@uri as AIOS Executor

## Observation

During URI-052, Codex needed visual proof for `/memory` schema receipt. The
existing port 3000 server was `next dev`, so screenshots included the Next
development issue overlay even though console/page errors were clean.

Codex reran the visual check against production `next start` on port 3001 to
produce a cleaner proof image.

At the same time, Claude appended Sprint 040 to `docs/AGENT_WORKLOG.md` while
Codex was closing URI-052. The local registry had to add `URI-053` as a
ledger-only reconciliation after the fact.

## AIOS Improvement

AIOS should provide two primitives for child repos:

- `visual_verify(mode=prod)`: build, start an ephemeral production server on an
  unused port, run Playwright, store screenshot, then shut the server down.
- `allocate_work_id(agent, source)`: transactional work-id allocation before any
  agent writes sprint/worklog artifacts.

Update from URI-054: `visual_verify(mode=prod)` must also stop or isolate any
active `next dev` process for the same repo. Running `next dev` and `next start`
against the same `.next` directory caused stale chunk references and false
production failures. The verifier should check that every static chunk referenced
by the target page returns HTTP 200 before taking screenshots.

## Why It Matters

Uri depends on visual, app-like iteration. Verification screenshots should show
the product, not dev-tool overlays. Multi-agent sprint velocity also needs a
shared allocator so Claude planning and Codex execution do not require manual
ledger repair.
