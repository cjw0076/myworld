# AIOS Canonical Shape

This document removes the current ambiguity around "AIOS", "complete",
"production", "service", and "OS". It is the vocabulary gate for future
claims. If another document uses these words differently, this document wins
unless the operator explicitly supersedes it.

## Canonical Sentence

AIOS is a local-first device-head operating layer: a governed kernel and
control plane that lets agents use memory, tools, providers, filesystems,
web evidence, and hosted surfaces without losing authority, provenance,
privacy, or replayability.

Shorter:

```text
AIOS = device-head kernel + control plane + memory/capability/execution organs.
Products and hosted surfaces run above it; provider platforms run below or
beside it as replaceable vendors.
```

## The Five Layers

| Layer | What It Is | Owned By | Completion Word | Not This |
| --- | --- | --- | --- | --- |
| L1 Kernel/head | `aios <goal>`, ContractObject, authority checks, tool syscalls, receipts, rollback | myworld kernel scripts | `kernel-complete` | not a workflow engine, not a chat wrapper |
| L2 Control plane | contracts, dispatch, watcher/round state, ledger, objective audits | myworld | `control-plane-ready` | not the implementation owner for every repo |
| L3 Organs | MemoryOS, CapabilityOS, Hivemind, GenesisOS | child OS repos | `organ-ready` per OS | not one monolith |
| L4 Service surfaces | `apps/serving`, `apps/control`, CLI/API entry points, support views | myworld plus serving contracts | `service-ready` | not proof that every hosted infra path is hardened |
| L5 Public infrastructure | Akashic Worker, Cloudflare Pages, Docker/PyPI/GHCR, public proofs | deploy/runtime owners | `public-infra-live` | not the whole AIOS by itself |

Use the narrowest true word. Never collapse the layers into "AIOS complete".

## Status Vocabulary

| Claim | Allowed Meaning | Required Evidence |
| --- | --- | --- |
| `kernel-complete` | The minimum local head can turn a goal into governed tool actions and receipts. | `docs/AIOS_MINIMUM_KERNEL_AUDIT.md`, focused head/runtime tests |
| `self-maintaining-complete` | The local autopoietic loop can run and preserve state without chat context. | `docs/AIOS_NORTHSTAR_READY.md`, round-controller/latest receipts |
| `world-service-objective-ready` | ASC-0279 objective audit is fully proven and contract hygiene is clean. | `python3 scripts/aios_world_service_audit.py --json` reports `completion_claim_supported=true` |
| `service-ready` | End-user serving release gate is green. | `python3 scripts/aios_serving_release_gate.py assess --root . --json` |
| `world-deployable` | World readiness spine is green. | `python3 scripts/aios_world_readiness.py --json` |
| `public-infra-live` | A public endpoint responds and has a runbook/proof record. | `.aios/serving/proofs/public_url.json`, `docs/deploy/PRODUCTION_HOSTING_RUNBOOK.md`, live HTTP check |
| `public-product-ready` | A real user can install, use, understand, recover, and trust the product path. | README/install smoke, hosted proof, support/runbook, privacy proof, rollback path, user-facing docs |

`production-grade` is banned unless scoped: say `production-grade Akashic
infra`, `production-grade kernel`, or `production-grade public product`.

## Boundary Rules

| Ambiguous Question | Canonical Answer |
| --- | --- |
| Is AIOS a kernel or a product? | Kernel/control plane first; products are surfaces above it. |
| Is AIOS local or hosted? | Local-first. Hosted/public surfaces are projections and distribution paths. |
| Is AIOS MemoryOS? | No. MemoryOS is the most important organ, but AIOS is the governed loop across organs. |
| Does MyWorld implement everything? | No. MyWorld routes, audits, dispatches, and records. Child repos implement their organs. |
| Are provider managed agents AIOS? | No. They are vendors. AIOS absorbs their stable primitives through ownership matrices and receipts. |
| Is Akashic Worker the product? | No. It is public memory infrastructure. It can power products but is not the whole product. |
| Does a green release gate mean AIOS is finished? | No. It means one scoped readiness claim is true. |

## Assumptions And Negations

| Assumption | Negation | Rule |
| --- | --- | --- |
| "Complete" means no work remains. | Operating systems evolve forever. | Always attach a completion scope. |
| Public endpoint means product readiness. | Infra can be live while UX/support/install remain weak. | Public endpoint proves only `public-infra-live`. |
| Provider state reduces AIOS complexity. | Provider state can split memory, authority, and retention. | Provider IDs are source refs until absorbed by AIOS ownership rules. |
| More contracts make AIOS clearer. | More contracts can hide the actual user path. | Prefer one canonical vocabulary gate over another planning contract. |

## Time Horizons

| Horizon | Meaning Of This Resolution |
| --- | --- |
| 1 hour | Agents stop saying "AIOS complete" without a scope and can run the right audit command. |
| 1 week | README, deploy docs, contracts, and release gates use the same completion vocabulary. |
| 1 year | AIOS can add providers, hosted workers, memory pools, and product surfaces without changing its identity. |

## Current State As Of 2026-06-21 KST

| Scope | Current Evidence | Status |
| --- | --- | --- |
| Kernel/head | Minimum kernel audit says 6/6 CC complete; head/runtime tests exist. | `kernel-complete` |
| Self-maintaining local loop | Northstar-ready defines self-maintaining completion; round controller exists. | `self-maintaining-complete`, subject to live monitor health |
| World service objective | ASC-0279 currently reports 14/14 proven and no hygiene gaps. | `world-service-objective-ready` |
| End-user serving release | Serving release gate reports ready. | `service-ready` |
| Public infra | Akashic Worker and Cloudflare Pages proof/runbook exist. | `public-infra-live` |
| Public product | Install, docs, hosted UI, privacy, support, rollback, and user recovery still need real-user validation. | not yet proven |

## Required Wording

Use:

```text
AIOS is kernel-complete, self-maintaining locally, world-service-objective-ready,
and has live public infrastructure. Public-product readiness still needs
real-user validation.
```

Do not use:

```text
AIOS is complete.
AIOS is production-ready.
AIOS is the Akashic Worker.
AIOS is just the README product.
```

