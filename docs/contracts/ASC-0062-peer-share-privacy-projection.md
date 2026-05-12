---
contract_id: ASC-0062
slug: peer-share-privacy-projection
status: closed
goal: Define and verify the first Sovereign Swarm privacy projection layer before any peer identity, share repo, remote sync, or raw memory federation exists.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by codex acting operator (founder directive: next work after sovereign swarm design decision)
acceptance_authority: codex@myworld initial accept (prep-only scope per A5); founder 재원 explicit GO 2026-05-13 KST in chat ("go"). Subsequent ASC-0063 (peer identity) requires separate founder GO per dialogue agreement.
origin: docs/discoveries/2026-05-13-sovereign-swarm-design-dialogue.md TURN 5.
closed: 2026-05-13 KST by codex acting operator
---

# ASC-0062 Peer-Share Privacy Projection

## Why Now

Sovereign Swarm AIOS can become dangerous if the first primitive is identity,
share repo sync, or remote import. The first primitive must instead answer:
what is allowed to leave this local AIOS instance at all?

ASC-0062 creates a local-only privacy projection validator. It does not create
peer identity, keys, share repos, git sync, network fetch, remote import, or
MemoryOS acceptance.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/AIOS_SWARM_NORTHSTAR.md`
- `docs/AIOS_SHARE_INVARIANTS.md`
- `scripts/aios_share_projection.py`
- `tests/test_aios_share_projection.py`
- `tests/fixtures/share_projection/valid_capability_observation.json`
- `tests/fixtures/share_projection/reject_raw_memory.json`
- `tests/fixtures/share_projection/reject_secret_path.json`
- `docs/contracts/ASC-0062-peer-share-privacy-projection.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/**`
- `memoryOS/**`
- `CapabilityOS/**`
- `uri/**`
- `.env`
- `.env.*`
- `.aios/logs/**`
- `.runs/**`
- `raw_exports/**`
- `_from_desktop/**`
- `dain/**`
- `minyoung/**`

## Responsibilities

### myworld.must_produce

- `docs/AIOS_SWARM_NORTHSTAR.md`: Sovereign Swarm north star and non-goals.
- `docs/AIOS_SHARE_INVARIANTS.md`: six invariants, hard-ban paths, eligible
  projection kinds, and stop conditions.
- `scripts/aios_share_projection.py verify <record.json> --json`: validates a
  single local projection record. It must be local-only and perform no network,
  git sync, signing, import, memory acceptance, or provider execution.
- Fixtures for:
  - valid capability observation projection
  - rejected raw memory projection
  - rejected hard-ban secret path projection
- Tests for schema, default deny, eligible kinds, hard-ban paths, redaction
  proof fields, and signature field presence.

### child repos

- No source role. The validator is a myworld control-plane preflight layer.

## Projection V1

Required fields:

- `schema_version: "aios.share_projection.v1"`
- `projection_id`
- `source_os: myworld|memoryOS|CapabilityOS|hivemind`
- `record_kind`
- `visibility`
- `source_ref`
- `source_hash`
- `projection_hash`
- `redaction_proof`
- `payload`
- `producer`
- `signature`
- `created_at`

Eligible `record_kind` values:

- `memory_draft_projection`
- `capability_observation_projection`
- `hive_run_receipt_projection`
- `contract_projection`
- `ledger_projection`

Visibility:

```json
{
  "share": false,
  "peer_whitelist": [],
  "encryption": null,
  "purpose": "peer_review|capability_observation|run_receipt|contract_projection"
}
```

Default is deny. `visibility.share` must be `true` and `record_kind` must be
eligible for a projection to pass.

## Verification Gate

```bash
python -m py_compile scripts/aios_share_projection.py
python -m unittest tests/test_aios_share_projection.py
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/valid_capability_observation.json --json
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_raw_memory.json --json
python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_secret_path.json --json
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Valid synthetic projection returns `status=passed`.
- Raw memory fixture returns `status=blocked`.
- Secret-path fixture returns `status=blocked`.
- Full myworld AIOS tests pass.
- Monitor remains clear.

## Stop Conditions

- `raw_memory_projection_allowed`
- `automatic_accept_enabled`
- `remote_execution_by_trust`
- `unsigned_record_passed`
- `global_canonical_truth_claimed`
- `hard_ban_path_allowed`
- `network_or_git_sync_added`
- `child_repo_scope_leak`
- `verification_gate_failed`

## Work Packets

### WP-0062-A — Codex@myworld implements privacy projection preflight

- target_agent: codex
- target_repo: myworld
- status: accepted
- closed: 2026-05-13 KST
- issued: 2026-05-13 KST
- accepted: 2026-05-13 KST
- depends_on: none
- brief: |
    Implement the local-only privacy projection validator, docs, fixtures, and
    tests. Do not create peer identity, share repos, remote sync, signing
    keys, MemoryOS import, or provider execution. This contract only defines
    what may be shared later.
- result: closed
- evidence:
  - `python -m py_compile scripts/aios_share_projection.py`
  - `python -m unittest tests/test_aios_share_projection.py`
  - `python scripts/aios_share_projection.py verify tests/fixtures/share_projection/valid_capability_observation.json --json`
  - `python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_raw_memory.json --json`
  - `python scripts/aios_share_projection.py verify tests/fixtures/share_projection/reject_secret_path.json --json`
  - `python -m unittest discover -s tests -p 'test_aios_*.py'`
  - `python scripts/aios_monitor.py assess --json`
