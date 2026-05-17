# aios.product_recap.v1

Schema for product-repo recap packets emitted into
`.aios/inbox/myworld/product_recap__<repo>__<sprint_id>.json`.

Defined by: ASC-0173 (product-repo-consent-emitted-evidence-ingest)

## Purpose

Lets a product repo (uri, etc.) emit a sprint-close recap that AIOS absorbs as:

- a MemoryOS draft (via `memoryos import`)
- a CapabilityOS observation (via `aios_ingest_product_recap.py`)

without AIOS owning execution, without bulk git scrape, and without auto-acceptance.

## Required Fields

```json
{
  "schema": "aios.product_recap.v1",
  "product_repo": "uri",
  "sprint_id": "URI-210",
  "sprint_subject": "Anonymous pilot result template",
  "commit_sha": "<sha>",
  "files_touched": ["uri/lib/...", "uri/app/..."],
  "capabilities_used": ["nextjs", "kakao_map", "vercel_deploy"],
  "operator_signed_by": "<handle>",
  "consent": "I authorize AIOS to ingest this packet as a MemoryOS draft and CapabilityOS observation.",
  "evidence_refs": ["<commit URL>", "<sprint manifest path>"]
}
```

## Field Semantics

| Field | Required | Notes |
|---|---|---|
| `schema` | yes | Must equal `aios.product_recap.v1`. Older/newer versions rejected. |
| `product_repo` | yes | Repo slug. Allowed: `uri` initially; extends per contract. |
| `sprint_id` | yes | Repo-local sprint identifier. Must be unique within `product_repo`. |
| `sprint_subject` | yes | Human-readable one-line subject. |
| `commit_sha` | optional | If provided, must be a valid git SHA in `product_repo`. |
| `files_touched` | optional | List of file paths inside `product_repo`. |
| `capabilities_used` | yes | Free-form list of capability identifiers (e.g., `nextjs`, `kakao_map`). Used to build `cap_<repo>_<capability>` observation records. |
| `operator_signed_by` | yes | Handle of the product-repo operator who signed off. |
| `consent` | yes | Exact string match required: `"I authorize AIOS to ingest this packet as a MemoryOS draft and CapabilityOS observation."`. Without exact match, the packet is rejected. |
| `evidence_refs` | yes | At least one. URL or file-path string. Becomes MemoryOS `derives_from` / `evidence_refs`. |

## Acceptance Rules (Invariant-Bound)

1. **Invariant 6 (operator override)**: packets without `consent` field exact-match are rejected. No silent ingestion.
2. **Invariant 2 (draft-first)**: ingestion produces drafts only. Acceptance requires explicit MemoryOS review.
3. **Invariant 5 (provenance chain)**: `evidence_refs` must be non-empty. Records cite packet path + listed evidence.
4. **Invariant 7 (private-gated data)**: packets are rejected if they include raw private exports, secret-like patterns (`sk-*`, `BEGIN PRIVATE KEY`, `OPENAI_API_KEY`), or paths under `_from_desktop/`, `dain/`, `minyoung/`.

## Where Packets Land

- Inbox: `.aios/inbox/myworld/product_recap__<repo>__<sprint_id>.json`
- After ingest: moved to `.aios/processed/myworld/product_recap__<repo>__<sprint_id>.json` with a sibling `.receipt.json` recording the MemoryOS draft id and CapabilityOS observation entry.
- Rejected: moved to `.aios/rejected/myworld/product_recap__<repo>__<sprint_id>.json` with a sibling `.reject.json` recording the failed invariant.

## How AIOS Consumes Them

```bash
# Validate + ingest:
python scripts/aios_ingest_product_recap.py --inbox .aios/inbox/myworld --apply

# After ingest, the standard MemoryOS draft surface shows the new drafts:
cd memoryOS && python -m memoryos drafts list --status draft | grep product_recap

# And CapabilityOS recommendation reflects observed capabilities:
cd CapabilityOS && python -m capabilityos.cli \
  --catalog ../.aios/capability_observations/uri_capabilities.json \
  recommend --task "uri stack" --json
```

## What This Schema Does NOT Allow

- No execution requests. The packet describes WHAT happened, not WHAT TO DO.
- No memory-acceptance hints. AIOS reviewer decides acceptance.
- No cross-repo authority claims. The packet only speaks for its own `product_repo`.
- No silent supersession. Recap packets stack; they do not overwrite each other.
