---
contract_id: ASC-0277
slug: memoryos-cli-log-asset-pool-ledger
status: proposed
created: 2026-06-16T00:00:00+09:00
goal: Turn private AI/CLI work logs into reviewable, hash-addressed, privacy-safe assets that can be shared across an AIOS user pool without exposing raw provider transcripts, secrets, private files, or unpublished competition code.
owner_repo: memoryOS
supporting_repos:
  - hivemind
  - CapabilityOS
  - myworld
origin: operator_idea
---

# ASC-0277 MemoryOS CLI Log Asset Pool Ledger

- status: proposed
- owner repo: `memoryOS`
- supporting repos: `hivemind`, `CapabilityOS`, `myworld`
- proposed_by: codex@dacon
- proposed_at: 2026-06-16 KST

## Goal

Turn private AI/CLI work logs into reviewable, hash-addressed, privacy-safe
assets that can be shared across an AIOS user pool without exposing raw
provider transcripts, secrets, private files, or unpublished competition code.

This is motivated by prize-hunting and agent-behavior competitions where the
valuable asset is not only final code but the observable work process:
candidate generation, tool use, failure modes, submit economy, verification
receipts, and strategy pivots.

## User Thesis

If AIOS users can locally assetize their CLI logs into signed or
content-addressed receipts, a pool of participants can verify work patterns and
reuse safe methods. AIOS becomes a decentralized work lineage layer: not a
blockchain by default, but a local-first distributed ledger of proof packets
that can later be mirrored to a token or reputation network.

## Current Evidence

MemoryOS already has important primitives:

- AI export importers and `SourceArtifact` provenance.
- `memoryos import-run` for Hive Mind run artifacts.
- `memoryos hive-live validate/import/graph` for structured event streams.
- Draft-first `MemoryObject` review lifecycle.
- Retrieval traces and provenance graph surfaces.
- Provider docs assetization scripts.

Observed gap:

- There is no completed general-purpose `cli-log assetize` surface for arbitrary
  provider/agent CLI logs that emits a standard pool-verifiable receipt packet.
- Existing raw session/export data is intentionally sensitive and local.
- Hive live events are structured, but arbitrary Codex/Claude/Gemini/Qwen CLI
  logs still need a safe parser/normalizer/redactor before they can become
  shared assets.

## Required Product Shape

### MemoryOS

Owns:

- `memoryos cli-log validate <path> --json`
- `memoryos cli-log assetize <path> --out <dir> --json`
- `memoryos cli-log import <receipt.json> --dry-run|--json`
- Draft memory creation from sanitized insights only.
- SourceArtifact rows with raw log hash, parser version, redaction state, and
  local-only raw path.
- Provenance links from derived assets back to source receipt IDs.

Must not:

- Store raw provider logs in shared docs.
- Auto-accept derived memories.
- Expose secrets, raw prompts, private file paths, token streams, or account
  data in pool packets.

### Hive Mind

Owns:

- Structured event stream emission where possible.
- CLI wrapper receipts for provider executions.
- Verification receipts for tests, submits, and degraded provider runs.

### CapabilityOS

Owns:

- Recommendation-only routing of which providers/tools can emit compatible
  receipts.
- Fallback plan when a provider log cannot be parsed safely.

### MyWorld

Owns:

- Contract, pool governance policy, and operator checkpoints.
- Public-safe packet schema for pool sharing.

## Pool Packet Schema Sketch

```json
{
  "schema_version": "aios.cli_log_asset.v1",
  "asset_id": "cla_<content_hash>",
  "source": {
    "provider": "codex|claude|gemini|qwen|unknown",
    "raw_sha256": "<hash>",
    "raw_retained_local_only": true,
    "redaction_state": "redacted|blocked|manual_review"
  },
  "workline": {
    "goal_hash": "<hash>",
    "repo": "optional public-safe repo id",
    "turn_count": 0,
    "tool_call_count": 0,
    "verification_count": 0,
    "failure_modes": []
  },
  "assets": [
    {
      "type": "strategy_pivot|test_receipt|submission_receipt|provider_failure|method_pattern",
      "summary": "privacy-safe summary",
      "evidence_hash": "<hash>",
      "confidence": "low|medium|high"
    }
  ],
  "pool": {
    "share_level": "private|team|public_hash_only|public_summary",
    "review_status": "draft|reviewed|accepted|rejected",
    "verifier_ids": []
  }
}
```

## Verification Gate

MemoryOS implementation is not complete until:

- A fixture with synthetic CLI logs validates and assetizes.
- A fixture containing secret-looking strings is blocked or redacted.
- Re-import is idempotent by content hash.
- Draft memories remain draft until review.
- `memoryos doctor` or a dedicated smoke command confirms no raw log bodies
  enter public-safe ledgers.
- A pool packet can be inspected by another AIOS clone without the raw log.

## Stop Conditions

- Raw secrets detected.
- Raw provider transcript required for sharing.
- Parser cannot distinguish private from public-safe fields.
- Memory drafts auto-accepted.
- Pool packet implies financial/reputation token value before governance and
  legal review.

## Competition Link

For NYPC 2026 Master Track and similar agent-behavior competitions, this would
allow teams to keep private strategy logs while sharing verifiable method
receipts: local benchmark deltas, submit-economy discipline, failure modes,
and representative-answer selection. It should not publish active competition
code or strategy before rules permit sharing.

## Next

1. MemoryOS drafts `cli-log` parser/receipt schema with synthetic fixtures.
2. Hive Mind adds provider wrapper event emission parity.
3. CapabilityOS records compatible providers and redaction risks.
4. MyWorld defines pool governance: share levels, verifier role, and optional
   future token/reputation boundary.
