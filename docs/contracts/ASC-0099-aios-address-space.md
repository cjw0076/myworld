---
contract_id: ASC-0099
slug: aios-address-space
status: accepted
goal: Add an AIOS address layer above path-based files so large projects can route by content, meaning, provenance, capability, and execution state instead of only filesystem locations.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by Codex under founder-delegated operator instruction
closed: pending
origin: founder direction 2026-05-13 KST — "주소 기반 파일 시스템 이상으로의 효율을 가져야"
---

# ASC-0099 AIOS Address Space

## Why Now

Path-based files are necessary recovery substrate, but they are not efficient
enough for a large AIOS. A file path answers "where is the byte container?"
It does not answer:

- Which decision, memory, contract, capability, provider, or run does this
  artifact represent?
- Which sources support it?
- Which agent can safely act on it?
- Which project or semantic concept does it belong to?
- Whether a newer object supersedes it?
- Whether a remote agent should see raw refs or only redacted labels?

AIOS needs a higher address layer that keeps files as storage but lets agents
route by stable object identity, semantic intent, provenance, and capability
affordance.

## Target Model

AIOS addresses are not only paths. They are typed references:

```text
aios://contract/ASC-0091
aios://memory/mem_3af960f629693170
aios://source/src_...
aios://run/hive/<run_id>
aios://capability/provider-route/codex
aios://concept/provider-backpressure
aios://project/uri/goal/<goal_id>
```

Each address must resolve to a bounded record:

- canonical id
- type
- owning OS/repo
- privacy class
- provenance refs
- current status
- local storage pointer, if one exists
- redacted summary safe for remote/model context

## Scope

repos:

- `myworld`
- `memoryOS`
- `CapabilityOS`
- `hivemind`

allowed_files:

- `docs/contracts/ASC-0099-aios-address-space.md`
- `docs/AIOS_ADDRESS_SPACE.md`
- `scripts/aios_address.py`
- `tests/test_aios_address.py`
- `memoryOS/memoryos/schema.py`
- `memoryOS/memoryos/cli.py`
- `memoryOS/tests/test_address_space.py`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/cli.py`
- `CapabilityOS/tests/test_cli.py`
- `hivemind/hivemind/hive.py`
- `hivemind/tests/test_address_resolution.py`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- bulk data rewrites
- unrelated UI files
- `uri/**`
- `_from_desktop/**`, `dain/**`, `minyoung/**`

## Per-OS Responsibility

### myworld.must_produce

- AIOS address specification in `docs/AIOS_ADDRESS_SPACE.md`.
- Resolver CLI `scripts/aios_address.py` with:
  - `resolve <aios://...> --json`
  - `index --json`
  - `redact <aios://...> --audience remote --json`
- Tests proving contract, dispatch, run, memory, and capability address parsing.
- Rule: path is a fallback pointer, not the primary identity.

### memoryOS.must_produce

- Map `MemoryObject`, `SourceArtifact`, `RetrievalTrace`, and `Hyperedge` ids
  into `aios://memory/*`, `aios://source/*`, `aios://trace/*`, and
  `aios://hyperedge/*`.
- Provide read-only address resolution for memory objects with privacy-aware
  redaction.
- Do not auto-accept any memory through address resolution.

### capabilityos.must_produce

- Map capability cards, provider routes, fallback plans, and MCP candidates into
  `aios://capability/*`.
- Return recommendation-only address metadata: no install, no execute.
- Capability address resolution must include risk and authority notes.

### hivemind.must_produce

- Allow Hive run receipts and provider-loop artifacts to cite AIOS addresses
  instead of only local paths.
- Verification receipts should contain both local path and canonical AIOS
  address when available.

### genesisos.must_produce

- No implementation role in this contract.
- Later work may add `aios://concept/*` semantic alignment addresses.

## Work Packets

### WP-0099-myworld-control-plane-resolver

owner: `myworld`

status: implemented

must_produce:

- `docs/AIOS_ADDRESS_SPACE.md`
- `scripts/aios_address.py`
- `tests/test_aios_address.py`
- `aios.address.resolution.v1`
- `aios.address.index.v1`

verification:

```bash
python -m unittest tests/test_aios_address.py
python -m py_compile scripts/aios_address.py
python scripts/aios_address.py resolve aios://contract/ASC-0091 --json
python scripts/aios_address.py resolve aios://memory/mem_3af960f629693170 --json
python scripts/aios_address.py resolve aios://capability/provider-route/codex --json
python scripts/aios_address.py index --json
```

### WP-0099-memoryOS-native-address-resolution

owner: `memoryOS`

status: dispatched_next

must_produce:

- read-only MemoryOS CLI/API surface for `aios://memory/*`,
  `aios://source/*`, `aios://trace/*`, and `aios://hyperedge/*`
- remote redaction parity with the myworld resolver
- no auto-accept or lifecycle mutation during address resolution

### WP-0099-capabilityOS-native-address-resolution

owner: `CapabilityOS`

status: dispatched_next

must_produce:

- read-only CapabilityOS CLI surface for `aios://capability/*`
- provider-route addresses as recommendation-only metadata
- explicit risk, authority, cost, and privacy notes

### WP-0099-hivemind-address-citation

owner: `hivemind`

status: dispatched_next

must_produce:

- Hive run receipts can cite `aios://run/hive/<run_id>`
- provider fallback and verification receipts can include canonical AIOS
  addresses beside local path refs
- no execution behavior changes beyond address citation and resolution smoke

## Design Questions

Q1. Should `aios://concept/*` live in GenesisOS or MemoryOS?

Default answer: GenesisOS owns meaning normalization; MemoryOS stores accepted
concept memory and provenance. ASC-0099 should define the address shape but only
implement concrete object/run/capability addresses first.

Q2. Is content addressing hash-based or semantic?

Answer: both, but in layers. Content hash proves byte identity. Semantic address
points to the stable AIOS object identity that may survive file moves,
summaries, supersession, and redaction.

Q3. Does this replace the filesystem?

No. It makes the filesystem an implementation detail. Files remain recovery and
debug surfaces; AIOS agents should prefer typed addresses when crossing OS
boundaries.

## Verification Gate

```bash
python -m unittest tests/test_aios_address.py
cd memoryOS
python -m unittest tests/test_address_space.py
cd ../CapabilityOS
python -m pytest tests/test_cli.py -v
cd ../hivemind
python -m pytest tests/test_address_resolution.py -v
cd ..
python scripts/aios_address.py resolve aios://contract/ASC-0091 --json
python scripts/aios_address.py resolve aios://memory/mem_3af960f629693170 --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `address_privacy_leak`: remote redaction emits raw refs or absolute private
  paths.
- `path_primary_identity_regression`: cross-OS packet uses only a file path
  when an AIOS address is available.
- `ambiguous_address_resolution`: one address resolves to multiple live objects
  without supersession metadata.
- `auto_accept_memory`: address import or resolution accepts memory without
  review.
- `capability_exec_leak`: CapabilityOS address resolution installs or executes a
  tool.
- `schema_drift`: MemoryOS, CapabilityOS, and Hive disagree on address envelope
  keys.

## Receipts

- myworld phase implemented:
  - `docs/AIOS_ADDRESS_SPACE.md`
  - `scripts/aios_address.py`
  - `tests/test_aios_address.py`
- verification passed:
  - `python -m unittest tests/test_aios_address.py`
  - `python -m py_compile scripts/aios_address.py`
  - `python scripts/aios_address.py resolve aios://contract/ASC-0091 --json`
  - `python scripts/aios_address.py resolve aios://memory/mem_3af960f629693170 --json`
  - `python scripts/aios_address.py resolve aios://capability/provider-route/codex --json`
  - `python scripts/aios_address.py index --json`
- live index observed:
  - contracts: 99
  - memory objects: 38
  - capabilities: 6
  - hive runs: 181
- remaining before close:
  - MemoryOS native address command/test
  - CapabilityOS native address command/test
  - Hive address citation smoke/test
- child packet dogfood:
  - `asc-0099.memoryOS` collected with local fallback held for verifier
  - `asc-0099.CapabilityOS` collected with local fallback held for verifier
  - `asc-0099.hivemind` collected with local fallback held for verifier
- runtime follow-up closed:
  - `ASC-0100` corrected child watcher behavior from provider avoidance to
    provider reroute across Codex, Claude, Gemini, and local substrate.
