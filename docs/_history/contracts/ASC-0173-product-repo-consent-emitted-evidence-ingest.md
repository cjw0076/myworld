---
contract_id: ASC-0173
slug: product-repo-consent-emitted-evidence-ingest
status: closed
goal: Let product repos (uri first) emit recap/capability packets that AIOS absorbs as MemoryOS drafts and CapabilityOS observations, closing the "AIOS has 0 record of uri's 187 shipped sprints" gap WITHOUT bulk pull, WITHOUT supersession of any in-flight contract, and WITHOUT claiming execution authority.
created: 2026-05-15 KST
accepted: 2026-05-15 KST by claude@myworld under delegated authority (additive scope, no supersession, no DNA invariant risk, no founder escalation rule triggered)
closed: 2026-05-15 KST — 4/4 stop conditions met: schema present, end-to-end flow verified, uri emit hook shipped producing URI-211 real packet, capabilityos observed cap_uri_* > 0
supersedes: none (additive; explicitly does NOT supersede ASC-0128..0142 or ASC-0166..0171)
acceptance_authority: founder
replaces: ASC-0172 (withdrawn) Packet A + Packet B, scoped down and consent-gated
origin: claude@myworld study findings 2026-05-15 (docs/study/2026-05-15-observer-vs-executor-prior-art.md). Industry consensus (OpenTelemetry GenAI stable, W&B canonical) supports observer-first absorption; adversarial critic confirmed bulk-ingest violates Invariant 6 (operator override) without explicit consent. This contract delivers the absorbable value via emit-based consent.

---

# ASC-0173 Product Repo Consent-Emitted Evidence Ingest

## Plain Language

uri (and later other product repos) shipped 187 sprints. AIOS has zero record
of any of them. The right fix is NOT for AIOS to scrape uri's git history.
The right fix is for uri to **emit** a small recap packet at sprint boundary,
and for AIOS to absorb that packet as a MemoryOS draft + CapabilityOS
observation, with provenance, with explicit consent, with no execution claim.

This is the W&B / Helicone / LangSmith pattern: one line at the boundary,
observation only, no orchestration takeover.

## Scope

repos:

- `myworld` (define emit schema; build ingest tool)
- `memoryOS` (accept emit packets via existing `import-run` or new
  `ingest-product-recap` subcommand)
- `CapabilityOS` (accept observation packets via existing observe surface)
- `uri` (emit ONE recap packet on sprint close; opt-in; signed by uri operator)

forbidden_files:

- `uri/**` outside a single emit hook (no AIOS edits to uri source)
- bulk import of git history without explicit emit packet
- any file under `_from_desktop/`, `dain/`, `minyoung/`, `.env`
- changes to in-flight contracts ASC-0128..0142 or ASC-0166..0171

## What Gets Emitted (uri side)

At sprint close (manual or hook), uri emits one JSON packet to
`myworld/.aios/inbox/myworld/product_recap__uri__<sprint_id>.json`:

```json
{
  "schema": "aios.product_recap.v1",
  "product_repo": "uri",
  "sprint_id": "URI-210",
  "sprint_subject": "Anonymous pilot result template",
  "commit_sha": "<sha>",
  "files_touched": ["uri/lib/...", "uri/app/..."],
  "capabilities_used": ["nextjs", "kakao_map", "vercel_deploy"],
  "operator_signed_by": "uri operator handle",
  "consent": "I authorize AIOS to ingest this packet as a MemoryOS draft and CapabilityOS observation.",
  "evidence_refs": ["uri commit URL", "uri sprint manifest path"]
}
```

The consent line is the load-bearing field. Without it, AIOS does NOT ingest.
This satisfies Invariant 6 (operator override always possible) explicitly.

## What AIOS Does (myworld + memoryOS + CapabilityOS sides)

### Packet A — myworld defines schema + ingest hook

- Owner: `myworld`
- Action: write `docs/schemas/aios_product_recap_v1.md` defining the schema
  above with required vs optional fields.
- Action: add `scripts/aios_ingest_product_recap.py` that reads
  `.aios/inbox/myworld/product_recap__*.json`, validates consent, and
  produces (a) a MemoryOS-importable markdown and (b) a CapabilityOS
  observation packet.
- Acceptance evidence: schema file exists; ingest script passes a unit test
  using a synthetic uri packet.

### Packet B — memoryOS accepts the ingestion as drafts

- Owner: `memoryOS`
- Action: extend `python -m memoryos drafts` (or add a new subcommand
  `ingest-product-recap`) to accept the markdown produced by Packet A and
  create draft records with `origin: product_repo_emit, consent_signed_by: <handle>`.
- Acceptance evidence: a synthetic uri recap packet produces ≥ 1 draft
  visible via `python -m memoryos drafts list --status draft`. Draft is
  NOT auto-accepted (Invariant 2).

### Packet C — CapabilityOS records observations

- Owner: `CapabilityOS`
- Action: ingest the `capabilities_used` field as observation events. After
  ingest, `python -m capabilityos.cli recommend --task "uri stack" --json`
  returns `observed_capabilities > 0` with `cap_uri_*` records cited.
- Acceptance evidence: command above returns at least one capability with
  `observation_count > 0` and `evidence_refs` citing the emit packet.

### Packet D — uri commits the emit hook (opt-in only)

- Owner: `uri`
- Action: uri operator decides if/when to add the emit hook (manual script,
  git hook, or sprint-close ritual). AIOS does not push this code. uri
  documents the opt-in in its own `docs/AGENT_WORKLOG.md`.
- Acceptance evidence: at least one product_recap packet exists in
  `.aios/inbox/myworld/` for a uri sprint, signed by uri operator.

## Stop Conditions (Named)

This contract is **closed** when all four are true:

1. Schema file `docs/schemas/aios_product_recap_v1.md` exists.
2. Synthetic test packet flows end-to-end: ingest → memoryOS draft →
   capabilityOS observation. No silent acceptance anywhere.
3. uri has emitted ≥ 1 real recap packet (opt-in) and AIOS has absorbed it
   as drafts with proper provenance.
4. `python -m capabilityos.cli recommend --task "uri stack" --json` returns
   ≥ 1 observed `cap_uri_*` capability.

This contract **fails and escalates to founder** if:

- Any packet ingested without `consent` field (Invariant 6 violation).
- Any draft auto-accepted without explicit review (Invariant 2 violation).
- Bulk git-history pull is attempted instead of emit-based ingest.
- This contract is interpreted as superseding any in-flight execution-authority
  contract. It does NOT. Those contracts live their own lifecycle.

## What This Does NOT Do

- Does NOT take execution authority from product repos.
- Does NOT supersede ASC-0166..0171 (execution-authority surface).
- Does NOT resolve the observer-vs-executor reframe question (that goes to
  ASC-0174 Hive debate).
- Does NOT bulk-ingest existing 187 sprints. Past sprints can be emitted by
  uri retroactively if uri operator chooses, but no scrape from AIOS side.

## Provenance

- claude@myworld study findings 2026-05-15:
  `docs/study/2026-05-15-observer-vs-executor-prior-art.md`
- prior-art evidence: OpenTelemetry GenAI conventions stable Jan 2026;
  W&B canonical observer-first pattern; HashiCorp management plane model
- adversarial critic input: bulk-ingest violates Invariant 6, must be
  emit-based; 6 of 14 alleged "permission contracts" are CLOSED with
  shipped harness work
- DNA Invariant 2 (draft-first), 5 (provenance chain), 6 (operator override)
