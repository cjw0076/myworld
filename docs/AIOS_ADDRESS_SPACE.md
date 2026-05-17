# AIOS Address Space

AIOS stores data in files, but agents should not treat file paths as primary
identity. A path says where bytes live. An AIOS address says what an object is,
who owns it, how it is supported, and how safely it can be shared.

## Address Forms

```text
aios://contract/ASC-0091
aios://dispatch/asc-0091
aios://memory/mem_3af960f629693170
aios://source/src_b0786be419dddcc7
aios://trace/rtrace_...
aios://hyperedge/hedge_...
aios://run/hive/run_20260511_202021_fce844
aios://capability/cap_memoryos_context_build
aios://capability/provider-route/codex
```

## Resolution Envelope

Every resolver returns the same top-level envelope:

```json
{
  "schema_version": "aios.address.resolution.v1",
  "address": "aios://memory/mem_...",
  "found": true,
  "kind": "memory",
  "id": "mem_...",
  "owner_os": "MemoryOS",
  "owner_repo": "memoryOS",
  "privacy": "local",
  "status": "draft",
  "summary": "bounded human/model-safe summary",
  "storage_refs": ["memoryOS/memory/objects.jsonl"],
  "provenance_refs": ["docs/contracts/ASC-0091-...md"],
  "record": {}
}
```

`record` is bounded and redacted for remote audiences. Raw files remain
recovery substrate; cross-OS packets should prefer `aios://...` addresses and
include paths only as storage pointers.

## Privacy

- `audience=local`: may include local storage refs and raw refs.
- `audience=remote`: suppresses raw refs, absolute paths, private paths, raw
  provider output, and large content bodies.

Address resolution must not accept memory, execute capabilities, install tools,
or mutate lower repos.

## Ownership

| Address kind | Owner |
| --- | --- |
| `contract`, `dispatch` | myworld |
| `memory`, `source`, `trace`, `hyperedge` | MemoryOS |
| `run/hive` | Hive Mind |
| `capability/*` | CapabilityOS |
| `concept/*` | GenesisOS meaning layer, with MemoryOS provenance later |

## Design Rule

Path is a fallback pointer, not primary identity.
