# AIOS Deploy Manifest

What a fresh machine needs for AIOS to run as a complete "1인 1 AIOS" —
declared so deployment is turnkey and reproducible. `aios setup` reads this
intent and provisions it idempotently (a retried setup converges to the
same state).

Founder requirement (2026-05-17): everything this build produced — organs,
local models, helper catalog, MCP delegation — must be set up
*automatically on deploy*, not by hand.

## Local models (provisioned via Ollama)

| model | tier / role | size | set |
|---|---|---|---|
| `qwen3:1.7b` | fast tier — triage, classification | ~2 GB | minimal |
| `qwen3:8b` | default tier — summarize, extract | ~5 GB | minimal |
| `nomic-embed-text` | MemoryOS embeddings — semantic retrieval | ~0.3 GB | minimal |
| `qwen3:30b-a3b` | strong tier — consolidation, dream organ | ~18 GB | recommended |
| `deepseek-coder-v2:16b` | code tier — coding helpers | ~9 GB | recommended |

`minimal` is pulled automatically by `aios setup apply`. `recommended` is
pulled by `aios setup apply --full`. AIOS runs on `minimal` alone — the
model-agnostic tier system falls back down the prefer list, so the strong
tier resolves to `qwen3:8b` until `qwen3:30b-a3b` is present.

## Config (provisioned from `deploy/` templates)

| file | from template | purpose |
|---|---|---|
| `.aios/helpers/catalog.json` | `deploy/helpers_catalog.json` | the specialist helper roster |
| `.aios/helpers/model_tiers.json` | `deploy/model_tiers.json` | model-agnostic tier map |
| `.mcp.json` | `deploy/mcp.json` | AIOS MCP server registration (agent delegation) |

`.aios/` is gitignored (runtime state), so these are seeded from committed
`deploy/` templates on a fresh clone.

## Service

The always-on round controller (the autopoietic loop: dream → librarian →
local-operator → verify → self-evolve) is installed as a user-systemd
service by `aios install` — `aios setup` delegates to it.

## Organs (shipped in `scripts/`)

The organs are repo code — present on clone, no provisioning needed:
dream, librarian, local-operator, verify, self-evolve, helper layer,
research-fetch, MCP server, sovereignty, completion check.

## Verification

`aios setup apply` finishes by running `aios complete` — the deploy is
confirmed when the completion check is visibly green.

## The turnkey path

```bash
git clone <aios repo> && cd myworld
aios setup apply          # minimal models + config + service + verify
# or: aios setup apply --full   (also pulls the recommended large models)
```

One command → a complete, self-maintaining, sovereign personal AIOS.
