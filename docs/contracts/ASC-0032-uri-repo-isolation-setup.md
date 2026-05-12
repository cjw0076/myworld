---
contract_id: ASC-0032
slug: uri-repo-isolation-setup
status: closed
goal: Create an isolated Uri child repository for the student digital campus business workspace without mixing product artifacts into the MyWorld control plane.
created: 2026-05-12
accepted: 2026-05-12
closed: 2026-05-12
---

# ASC-0032 Uri Repo Isolation Setup

## Scope

- repos: `myworld`, `uri`
- allowed_files:
  - `.gitmodules`
  - `uri` gitlink
  - `docs/contracts/ASC-0032-uri-repo-isolation-setup.md`
  - `docs/contracts/README.md`
  - `docs/AIOS_AGENT_LEDGER.md`
- forbidden_files:
  - `hivemind/**`
  - `memoryOS/**`
  - `CapabilityOS/**`
  - `uri/data/**`
  - `uri/raw_exports/**`
  - `uri/private_sources/**`
  - `uri/.env`
  - `uri/.env.*`

## Responsibilities

### Hive Mind

- responsibility: no child execution required for scaffold; future Uri
  implementation packets should route through Hive Mind.
- must_produce: `execution_receipt` for future prototype work.

### MemoryOS

- responsibility: future Uri memory imports must stay draft-first and
  provenance-backed.
- must_produce: `context_pack`, `retrieval_trace`, `review_queue` when Uri
  research is imported.

### CapabilityOS

- responsibility: future tool, web research, GitHub, design, and prototype
  routes must be recommendation-first.
- must_produce: `capability_plan`, `fallback_plan`, `risk_notes` for Uri
  research and prototype tasks.

### Operator

- responsibility: requested a lower `uri` repo setup so Uri work does not mix
  with `myworld`.
- checkpoint_required: false for scaffold; true before ingesting private campus
  data, using paid APIs, or attempting any nonpublic company workflow research.

## Verification Gate

```bash
git -C uri status --short
git -C uri remote -v
git ls-files -s uri
git status --short
```

The gate passes when `uri` is a committed standalone repo with private remote
`cjw0076/uri-v3`, and MyWorld sees only a gitlink plus control-plane docs.

## Stop Conditions

- privacy_violation
- scope_violation
- missing_required_artifact
- ownership_conflict
- contract_ambiguous
- nonpublic code or tool access required
- proprietary workflow copied without public evidence or license

## Receipts

- Uri private GitHub remote: `https://github.com/cjw0076/uri-v3`
- Uri initial commit: `8f1621f Initial Uri workspace scaffold`
- Uri worklog follow-up commit: `f0edcbb Record Uri scaffold remote setup`
- MyWorld integration: `.gitmodules` entry plus `uri` gitlink.

## Work Packets

### WP-0032-A - Scaffold isolated Uri child repo

- target_agent: codex
- target_repo: uri
- status: done
- issued: 2026-05-12
- accepted: 2026-05-12
- closed: 2026-05-12
- depends_on: none
- brief: |
    Create an isolated child repository at `myworld/uri` for Uri product and
    business work. Include repo-local agent instructions, product north star,
    student digital campus business model, AIOS operating model, memory policy,
    capability map, legal guardrails, and worklog. Keep raw data and private
    sources out of git. Create private GitHub repo `cjw0076/uri-v3`, push the
    initial scaffold, and return only a gitlink to MyWorld.
- result: `uri/docs/AGENT_WORKLOG.md` and private remote `cjw0076/uri-v3`.
