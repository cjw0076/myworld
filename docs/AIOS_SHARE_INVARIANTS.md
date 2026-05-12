# AIOS Share Invariants

These invariants are mandatory for Sovereign Swarm AIOS. A share primitive that
violates any of them is not an AIOS feature.

## Six Invariants

1. No raw memory federation.
   MemoryOS accepted memory, raw memory bodies, private transcripts, and raw
   exports do not leave the local instance.

2. No automatic accept.
   Peer records can enter review queues or draft states only. Local review is
   required before a record affects accepted memory or policy.

3. No remote execution by trust alone.
   A peer's Hive receipt is evidence. It is not permission to execute locally
   or remotely.

4. No unsigned peer record.
   A shareable projection must carry signature metadata. ASC-0062 checks field
   presence; cryptographic identity arrives in a later contract.

5. No global canonical truth.
   The swarm does not produce one truth database. It produces evidence streams.

6. Only local posterior belief.
   Each AIOS instance updates its own belief from evidence, trust weights, and
   review outcomes.

## Hard-Ban Paths And Classes

The share projection validator must block:

- `_from_desktop/`
- `dain/`
- `minyoung/`
- `.env`, `.env.*`
- `**/*secret*`
- `**/*credential*`
- `**/*token*`
- `raw_exports/`
- `data/`
- `.aios/logs/`
- `.runs/`
- provider stdout/stderr bodies
- private transcripts
- unredacted local paths

## Eligible Projection Kinds

ASC-0062 permits only these V1 projection kinds:

- `memory_draft_projection`
- `capability_observation_projection`
- `hive_run_receipt_projection`
- `contract_projection`
- `ledger_projection`

Everything else is blocked by default.

## Redaction Proof V1

V1 uses local preflight proof, not peer-verifiable Merkle proof:

- `source_hash`: canonical hash of the local source record.
- `projection_hash`: canonical hash of the redacted projection payload.
- `redaction_proof.policy_version: "aios.share_policy.v1"`
- `redaction_proof.removed_paths[]`
- `redaction_proof.removed_classes[]`

Allowed removed classes:

- `secret`
- `personal_data`
- `raw_export`
- `provider_output`
- `local_path`
- `private_transcript`

Merkle proofs belong in the later share repo and manifest layer. Zero-knowledge
proofs are out of scope for the first implementation.

## Stop Conditions

- A raw or accepted memory object passes validation.
- A projection can be shared with `visibility.share=false`.
- A secret path or known secret pattern passes validation.
- A projection lacks signature metadata.
- A validator performs network, git sync, MemoryOS acceptance, or provider
  execution.
- A contract claims global canonical truth or remote execution authority.
