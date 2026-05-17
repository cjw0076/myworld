# aios.distilled_pattern.v1

Schema for a **distilled-pattern packet** — the unit of the AIOS federation.

Origin: founder direction 2026-05-17 — "federation 모델로 확정하고 증류-패턴
packet 스키마를 제작하자." The AIOS ecosystem is a *federation of sovereign
AIOSes*, not a central absorber. Each AIOS keeps its raw memory local
(DNA Invariant 7); only **distilled patterns** — already abstracted away
from raw episodes — flow to a shared commons, consent-gated, and the
commons redistributes them. This is federated distillation: knowledge
through abstracted patterns, never raw data.

This packet generalizes the ASC-0173 consent-emit primitive one level up:
ASC-0173 = a product repo emits a consent-gated recap to its AIOS.
This = an AIOS emits a consent-gated distilled pattern to the federation.
Same consent gate, same draft-first, same provenance discipline — no new
trust primitive.

## What a distilled pattern is — and is NOT

**IS:** an abstraction the dream organ already produced — a
`consolidated_schema` (a recurring pattern across many episodes), an
abstracted capability observation, a failure-mode, or a GenesisOS
escape-vector. It is general, de-identified, and carries no raw episodic
content.

**IS NOT:** raw MemoryOS drafts, conversation/episode text, contract
bodies, ledger entries, file contents, credentials, or anything traceable
to a person, machine, or private path. If a packet contains raw data it is
rejected — that is the Invariant 7 boundary.

## Packet format

```json
{
  "schema": "aios.distilled_pattern.v1",
  "pattern_id": "<sha256[:16] of pattern text — stable, dedup key>",
  "source_aios": "<pseudonymous federation node id — NOT a person/machine>",
  "pattern_kind": "consolidated_schema | capability_observation | failure_mode | escape_vector",
  "pattern": "<the abstracted pattern, one paragraph — no raw episodes>",
  "evidence_class": "distilled",
  "consent": "I authorize this distilled pattern to be shared to the AIOS federation commons. It contains no raw private data.",
  "projection_hash": "<sha256 of pattern — integrity>",
  "emitted_at": "<ISO-8601>",
  "expiry": "<ISO-8601 date — the pattern is not valid forever>",
  "revocable": true,
  "provenance": {
    "derived_from_kind": "dream_consolidation",
    "source_aios": "<same pseudonymous id>"
  }
}
```

## Field semantics

| Field | Meaning |
|---|---|
| `schema` | exact `aios.distilled_pattern.v1` |
| `pattern_id` | `sha256(pattern)[:16]` — stable identity, dedup across the commons |
| `source_aios` | a **pseudonymous** federation node id. Never a person, email, hostname, or path. The commons does not know who. |
| `pattern_kind` | one of the four abstracted kinds — all are dream-organ / GenesisOS outputs, never raw |
| `pattern` | the abstracted pattern itself, one paragraph |
| `evidence_class` | must be `distilled`. A packet with `raw` (or raw-looking content) is rejected |
| `consent` | exact-match string required — without it the federation does not ingest (Invariant 6) |
| `projection_hash` | `sha256(pattern)` — integrity + tamper check |
| `expiry` | patterns expire; the commons drops stale patterns (ASC-0124 federation gate) |
| `revocable` | the source AIOS can revoke a pattern; the commons must honor revocation |
| `provenance` | points at the *kind* of source (e.g. dream_consolidation), never the raw source artifact |

## Federation gates (ASC-0124, the highest-risk surface)

A distilled-pattern packet is accepted to the commons only if ALL hold:

1. **Consent** — exact `consent` string present (Invariant 6).
2. **Privacy projection** — privacy scan finds no secret patterns
   (`sk-*`, `*_API_KEY`, `BEGIN PRIVATE KEY`), no founder-gated paths
   (`_from_desktop/`, `dain/`, `minyoung/`), and `evidence_class == "distilled"`.
   Raw episodic content is rejected (Invariant 7).
3. **Pseudonymity** — `source_aios` matches a pseudonymous-id pattern, not
   an email / hostname / absolute path.
4. **Integrity** — `projection_hash == sha256(pattern)`.
5. **Freshness** — `expiry` is in the future.
6. **Draft-first** — the commons receives the pattern as a DRAFT. It is not
   redistributed until reviewed (Invariant 2).

## What the commons is — and is NOT

**IS:** a redistributor — a library. It holds reviewed distilled patterns
with provenance and serves them back to any federation node. It owns
nothing; each pattern remains revocable by its source AIOS.

**IS NOT:** an owner, a central AIOS, or a data warehouse. It never holds
raw memory. It cannot identify a source. It cannot prevent a node from
leaving with its own patterns.

## How a federation node uses it

```text
emit:    a sovereign AIOS distills a dream consolidation → consent-gated
         aios.distilled_pattern.v1 packet → federation commons (draft)
review:  the commons (or an operator) reviews the draft pattern
absorb:  any node pulls reviewed patterns → its own MemoryOS as DRAFTS
         (never auto-accepted) → its dream organ may consolidate them in
learn:   federated distillation — patterns can feed the local-LLM
         retraining track, so the federation raises ceilings collectively
```

## What this schema does NOT do

- It does not wire cross-AIOS data flow. That touches Invariant 7 (the
  founder-declared inviolable privacy boundary) and ASC-0124 deferred
  federation pending its gates. The *wiring* is a founder + Hive gated
  decision. This schema is the spec the wiring will conform to.
- It does not allow raw memory, episodes, or identity to cross.
- It does not make the commons an authority — patterns are drafts,
  revocable, expiring.

## Relationship to existing AIOS

- generalizes ASC-0173 (`aios.product_recap.v1`) — same consent-emit shape
- the `pattern` content is produced by the dream organ
  (`consolidated_schema`) and GenesisOS (`escape_vector`)
- `source_aios` pseudonymity + projection-only sharing follows ASC-0062
  (peer-share-privacy-projection)
- federation gates follow ASC-0124's verdict on the federation surface
