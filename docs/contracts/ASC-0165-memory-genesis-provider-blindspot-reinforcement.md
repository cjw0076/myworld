---
contract_id: ASC-0165
slug: memory-genesis-provider-blindspot-reinforcement
status: closed
goal: Reinforce MemoryOS and GenesisOS where provider CLIs are weakest: failure memory, retrieval of blind spots, discomfort sensing, and invention candidates.
created: 2026-05-14 12:40 KST
accepted: 2026-05-14 12:40 KST
closed: 2026-05-14 12:49 KST
acceptance_authority: founder delegated continuation under active AIOS evolution goal.
origin: Founder observed that Hive and CapabilityOS are already relatively strong at execution/routing, while MemoryOS and GenesisOS remain weak; reverse-engineering provider blind spots should therefore focus on memory and discomfort-driven invention.
---

# ASC-0165 Memory/Genesis Provider Blindspot Reinforcement

DNA references: Invariant 1 (decide before acting), Invariant 2
(draft-first memory), Invariant 5 (provenance chain), Invariant 6 (operator
override remains possible), Invariant 7 (private-gated data stays out of
dispatch and prompt artifacts).

## Plain Language

Provider CLIs can execute and answer, but they forget friction, smooth over
failure, converge on normal plans, and need the user to keep supplying the
interesting pressure. This contract strengthens the two AIOS layers that
should counter that weakness:

- MemoryOS should remember failures and blind spots, not only successful facts.
- GenesisOS should feel discomfort and turn it into named needs and invention
  candidates.

## Assumptions

- Hive Mind and CapabilityOS are not the first bottleneck in this slice.
  They are still used as execution wrapper and route evidence, but this
  contract deliberately optimizes MemoryOS and GenesisOS.
- A failure memory is not an accepted truth. It is a draft object with
  provenance and review lifecycle.
- A GenesisOS invention candidate is not an implementation plan. It is a
  speculative branch that MyWorld may later convert into a contract.
- The best near-term test is local CLI/schema behavior, not a broad product
  UI change.

## Counter-Default Branch

Default AIOS behavior would create another contract, dispatch it, run tests,
and close it. The counter-default branch is to treat the user's discomfort
with that loop as the product signal: AIOS must produce durable traces of
what felt wrong, what need that implies, and what invention candidate follows.

## Distant-Domain Analogy

Treat AIOS like ecology and city planning, not only software delivery. MemoryOS
keeps the ecological record of failed experiments with conditions and
provenance; GenesisOS studies the civic irritation caused by those failures
and sketches new instruments before MyWorld decides what should be built.

## Scope

repos:

- `GenesisOS`
- `memoryOS`
- `myworld`

allowed_files:

- `GenesisOS/genesisos/critic.py`
- `GenesisOS/genesisos/cli.py`
- `GenesisOS/tests/test_critic.py`
- `GenesisOS/tests/test_cli.py`
- `GenesisOS/docs/GENESIS_DOCTRINE.md`
- `GenesisOS/docs/AGENT_WORKLOG.md`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/importers.py`
- `memoryOS/memoryos/cli.py`
- `memoryOS/tests/test_schema.py`
- `memoryOS/tests/test_import_run.py`
- `memoryOS/docs/RETRIEVAL.md`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `docs/contracts/ASC-0165-memory-genesis-provider-blindspot-reinforcement.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `hivemind/**`
- `CapabilityOS/**`
- `.env`
- `.env.*`
- provider credentials
- raw private exports
- private chat transcripts
- `.runs/<other_runs>/**`
- `GenesisOS/genesisos/__pycache__/**`

## AIOS Role Evidence

### MemoryOS

must_produce:

- A draft-first failure memory representation for provider/agent blind spots.
- Provenance fields that point back to source artifact or result packet,
  without storing private raw logs.
- Retrieval guidance so failure memories can appear in future context packs
  when relevant.
- Tests proving failure memories remain draft/reviewable and provenance-bound.

suggested_shape:

```json
{
  "kind": "failure_memory",
  "failure_class": "provider_backpressure|provider_access_denied|empty_output|prompt_prison|retrieval_gap|tool_misroute",
  "symptom": "short sanitized symptom",
  "source_artifact_id": "source_or_receipt_id",
  "provenance_ref": "relative/path/to/result.json",
  "negative_pair": true,
  "review_status": "draft"
}
```

### GenesisOS

must_produce:

- A discomfort primitive that accepts a friction/failure text and emits:
  `discomfort_signal`, `named_need`, `invention_candidates`,
  `recombination_sources`, `risks`, and `contract_seeds`.
- A CLI surface, for example `python -m genesisos.cli discomfort --text ... --json`.
- Doctrine/worklog updates clarifying that GenesisOS is the OS that feels
  discomfort, but does not execute, accept memory, or route tools.
- Tests proving the output is speculative-only and includes at least one
  invention candidate from discomfort.

suggested_shape:

```json
{
  "schema_version": "genesisos.discomfort.v1",
  "authority": "speculative_only",
  "discomfort_signal": "repeated_user_reprompt|provider_blindspot|memory_gap|meaning_drift|tool_friction",
  "named_need": "short need statement",
  "invention_candidates": [
    {
      "candidate_id": "stable id",
      "premise": "what to invent",
      "recombination_sources": ["memory", "routing", "human_discomfort"],
      "why_it_might_matter": "short rationale",
      "risk": "why it may be wrong"
    }
  ],
  "contract_seeds": ["bounded MyWorld contract seed"]
}
```

### CapabilityOS

- role: advisory only
- no implementation in this contract
- evidence_use: existing provider fallback/route logs may be referenced as
  sanitized examples, but CapabilityOS source is out of scope.

### Hive Mind

- role: execution wrapper only
- no implementation in this contract
- evidence_use: child watcher result packets are sufficient for this slice.

### myworld

must_produce:

- Dispatch packets for `GenesisOS` and `memoryOS`.
- Collected result packets from both child repos or explicit stop-condition
  receipts.
- Ledger closeout only after child repo evidence exists.

## Verification Gate

GenesisOS gate:

```bash
cd GenesisOS
python -m unittest tests/test_critic.py tests/test_cli.py
python -m genesisos.cli discomfort --text "provider keeps failing and user keeps reprompting because the system forgets the friction" --json
```

MemoryOS gate:

```bash
cd memoryOS
python -m unittest tests/test_schema.py tests/test_import_run.py
```

MyWorld gate:

```bash
python scripts/aios_dispatch.py collect --repo GenesisOS
python scripts/aios_dispatch.py collect --repo memoryOS
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- GenesisOS emits a speculative discomfort-to-invention payload with no
  execution authority.
- MemoryOS can store or normalize failure-memory draft evidence without
  promoting it to accepted memory.
- Both child repo result packets are present and `passed`, or a stop
  condition names the exact blocker.
- No raw private provider logs, credentials, or private transcripts enter
  durable docs.

## Stop Conditions

- `memory_acceptance_without_review`
- `genesis_claims_execution_authority`
- `private_raw_log_leaked`
- `failure_memory_without_provenance`
- `child_repo_scope_violation`
- `provider_backpressure_without_fallback_receipt`

## Work Packets

### WP-0165-A — GenesisOS discomfort-to-invention primitive

- target_agent: codex
- target_repo: GenesisOS
- status: closed
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14 12:49 KST
- depends_on: ASC-0164
- brief: |
    Add a GenesisOS discomfort primitive and CLI command that turns sanitized
    friction text into a speculative invention candidate with named need,
    recombination sources, risks, and contract seeds. Preserve GenesisOS
    authority boundaries.
- result: implemented by founder-delegated operator rescue after provider
    execution was held. GenesisOS now exposes `genesisos.discomfort.v1` through
    `python -m genesisos.cli discomfort --text ... --json`.

### WP-0165-B — MemoryOS failure-memory draft surface

- target_agent: codex
- target_repo: memoryOS
- status: closed
- issued: 2026-05-14
- accepted: 2026-05-14
- closed: 2026-05-14 12:49 KST
- depends_on: ASC-0163
- brief: |
    Add or normalize a draft-first failure memory representation for provider
    blind spots and agent failures. It must be provenance-bound, reviewable,
    and retrievable as negative evidence without becoming accepted truth.
- result: implemented by founder-delegated operator rescue after provider
    execution was held. MemoryOS now has `make_failure_memory_object()` and
    `import-run` preserves `kind=failure_memory` drafts as reviewable negative
    evidence observations.

## Receipts

- GenesisOS watcher result:
  `.aios/outbox/GenesisOS/asc-0165.GenesisOS.result.json`, status `held`;
  attempts were Codex `provider_access_denied`, Claude
  `provider_backpressure`, local `done` but final held because local cannot be
  the verifier.
- MemoryOS watcher result:
  `.aios/outbox/memoryOS/asc-0165.memoryOS.result.json`, status `held`;
  attempts were Codex `provider_access_denied`, local `done` but final held
  because local cannot be the verifier.
- operator rescue verification:
  - `cd GenesisOS && python -m unittest tests/test_critic.py tests/test_cli.py`
    passed 8/8.
  - `cd GenesisOS && python -m genesisos.cli discomfort --text "provider keeps failing and user keeps reprompting because the system forgets the friction" --json`
    emitted `schema_version=genesisos.discomfort.v1` and
    `authority=speculative_only`.
  - `cd memoryOS && python -m unittest tests/test_schema.py tests/test_import_run.py`
    passed 64/64.
  - `cd GenesisOS && python -m py_compile genesisos/cli.py genesisos/critic.py`
    passed.
  - `cd memoryOS && python -m py_compile memoryos/schema.py memoryos/cli.py`
    passed.
- release: `python scripts/aios_dispatch.py release --dispatch-id asc-0165
  --agent codex --override-authority ... --close-type closed_goal_met`
  succeeded and wrote MemoryOS draft `mem_a77bb22cadf11cae`.
- monitor closeout: `health=attention`, `watched.alerts=3`,
  `watched.repos=4`. The remaining medium findings are expected `repo_dirty`
  alerts for the ASC-0165 child-repo changes in memoryOS and GenesisOS; the
  low finding is generated GenesisOS Python cache.
