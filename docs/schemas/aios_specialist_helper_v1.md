# aios.specialist_helper.v1

Schema for a **specialist helper** in the AIOS Specialist Helper Layer.

Origin: founder conception 2026-05-16 — the local LLM is not one central
daemon; it is a *population of specialist helpers*, "code parts" an agent
uses, distributed, like expert helpers in human society. Validated against
Minsky's Society of Mind and the NVIDIA position paper "Small Language Models
are the Future of Agentic AI" (Lego-like composition: scale out with small
specialists, not up with monolithic models; task experts handle 80-90% of
routine subtasks, frozen frontier models handle hard reasoning).

## What a specialist helper is

A narrow, callable, local-LLM-backed expert. It is a **tool**, never an
authority. An agent with a routine subtask routes to a helper, the helper
computes, the agent uses the result. The frozen frontier agent keeps the hard
reasoning; the helper offloads the routine 80-90%.

## Card format

A helper is a CapabilityOS capability card (so `capabilityos recommend` can
route to it) with an added `helper` block. The catalog file
(`.aios/helpers/catalog.json`) uses the standard `capabilityos.catalog.v1`
contract.

```json
{
  "id": "cap_helper_<specialty>",
  "name": "<Specialty> Specialist",
  "kind": "skill",
  "description": "...",
  "domains": ["<task words>", "helper", "specialist"],
  "actions": ["<verb>"],
  "inputs": ["<input kind>"],
  "outputs": ["<output kind>"],
  "risk": "low", "cost": "free", "latency": "medium", "privacy": "local",
  "requires_network": false, "executes_tools": false, "status": "active",
  "evidence_refs": ["docs/schemas/aios_specialist_helper_v1.md"],
  "helper": {
    "schema": "aios.specialist_helper.v1",
    "tier": "fast | default | strong | code",
    "model": "<optional explicit model hint — tier is preferred>",
    "specialty": "<one-line narrow specialty>",
    "role_prompt": "<the framing the runner prepends to the agent's input>",
    "boundary": "tool_only — computes/proposes, never an authority"
  }
}
```

## Field semantics

| Field | Meaning |
|---|---|
| `id` | `cap_helper_<specialty>` — stable, referenced by routing |
| `kind` | `skill` (a specialist helper is a skill) |
| `domains` / `actions` | task-match terms — how `capabilityos recommend` routes to it |
| `helper.tier` | model tier — `fast`/`default`/`strong`/`code`. Resolved at call time against models actually installed, via `.aios/helpers/model_tiers.json`. This is the model-agnostic path: attach any model, the layer adapts. |
| `helper.model` | optional explicit model hint — used only if no tier resolves; the layer always falls back to an installed model |
| `helper.specialty` | the one narrow thing it is good at |
| `helper.role_prompt` | prepended to the caller's input by the runner |
| `helper.boundary` | always `tool_only` — enforced by the layer |

## Model-agnostic resolution

A helper declares a **tier**, not a hardwired model. At call time the runner
queries the local runtime (Ollama) for installed models and resolves the
tier via `.aios/helpers/model_tiers.json` — walking a preference list and
falling back gracefully. Attach any model (`ollama pull <model>`, add it to
a tier's `prefer` list or it is picked up if already named) and every helper
on that tier adapts with no code change. No single model is load-bearing —
per the 2026 consensus that there is no single best local LLM.

`aios helper models` shows installed models and how each tier + helper
currently resolves.

## The layer

| Part | Mechanism |
|---|---|
| **register** | add a helper card to `.aios/helpers/catalog.json` (contributed from anywhere) |
| **discover / route** | `capabilityos recommend --catalog .aios/helpers/catalog.json` ranks helpers for a task |
| **invoke** | a thin runner (`scripts/aios_helper.py run`) — CapabilityOS is recommend-only and must not execute; the runner calls the local LLM |
| **observe** | helper invocations are recorded so the catalog accrues observation evidence |

## Hard boundary (enforced by the layer, not optional)

- A helper is a **tool**. It computes or proposes. It NEVER:
  - accepts memory (DNA Invariant 2 — draft-first)
  - creates, closes, or modifies contracts
  - overrides a frozen frontier agent's plan
  - sits on the critical reasoning path of an irreversible action
- A helper that exceeds the tool boundary is a layer violation.
- The capability gradient holds: helpers are the *weakest* reasoners; they
  serve routine load, they do not decide. (Skeptic-voice constraint, 2026-05-16.)

## Distributed by design

Helpers are contributed from many places (any OS, any product repo) into one
catalog, discovered through one router. "Distributed contribution, unified
discovery" — the founder's "여러 곳에서 인간사회처럼 전문가 helper".
