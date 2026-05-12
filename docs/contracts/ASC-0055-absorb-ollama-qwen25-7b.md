---
contract_id: ASC-0055
slug: absorb-ollama-qwen25-7b
status: closed
goal: Demonstrate the AIOS provider-absorption pipeline end-to-end by adding a recommendation-only CapabilityOS card and a Hive worker spec for the Ollama-served Qwen 2.5 7B local LLM, without binding or executing it.
created: 2026-05-13 KST
accepted: 2026-05-13 KST by claude acting operator (founder role delegated)
closed: 2026-05-13 00:22 KST
acceptance_authority: claude@myworld (operator) — founder asked to see how AIOS absorbs a new provider / local LLM ("새로운 provider 모델이 들어왔을 때, local llm이 생겼을 때 AIOS가 어떻게 흡수하는지 보자").
origin: founder demonstration request 2026-05-13 KST. Subject chosen: Ollama-served Qwen 2.5 7B as a realistic local-LLM example.
---

# ASC-0055 Absorb Ollama Qwen 2.5 7B (Demonstration)

## Why Now

The founder wants to see the provider-absorption pipeline in action. This
contract drives a single concrete absorption end-to-end so the operator
pair, codex, and any future LLM substrate can replay the recipe for the
next new provider/model. Pipeline stages:

1. **Evidence** — already captured via `aios_primitives web fetch` at
   `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json` (receipt
   `w-6eebb2055ff3`).
2. **Local registry** — already registered as
   `tool.ollama_qwen25_7b` via `aios_primitives tools register`.
3. **CapabilityOS card** — ADD `cap_ollama_qwen25_7b_local` to the
   catalog (this contract).
4. **Hive worker spec** — ADD `WorkerSpec` for invoking ollama (this
   contract; recommendation-only, no actual network call wired).
5. **Observation collection** — once a future contract dispatches a
   packet that recommends this card, `capability_pulse` accumulates
   `CapabilityObservation`s and Beta-mean confidence.
6. **Memory draft** — `memory_pulse` may surface the new card as a
   draft observation in MemoryOS review queue.

ASC-0055 only does stages 3–4. Stages 5–6 happen automatically through
existing pulses once dispatches start using the card.

## Required Reading

- `docs/AIOS_PRIMITIVES.md`
- `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json` (cited evidence)
- `CapabilityOS/capabilityos/schema.py` (CapabilityCard fields)
- `CapabilityOS/tests/fixtures/capabilities.json` (catalog format)
- `hivemind/hivemind/local_workers.py` (existing WorkerSpec patterns)

## Scope

repos:

- `myworld`
- `CapabilityOS`
- `hivemind`

allowed_files:

- `CapabilityOS/tests/fixtures/capabilities.json`
- `CapabilityOS/capabilityos/catalog.py`
- `CapabilityOS/capabilityos/schema.py` (if vocabulary extension needed)
- `CapabilityOS/tests/test_cli.py`
- `CapabilityOS/tests/test_observation.py` (if observation shape needs new test)
- `hivemind/hivemind/local_workers.py`
- `hivemind/tests/test_local_worker_routing.py`
- `docs/AIOS_PROVIDER_ABSORPTION.md` (recipe doc)
- `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json`
- `docs/contracts/ASC-0055-absorb-ollama-qwen25-7b.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `hivemind/hivemind/hive.py` (only local_workers.py changes; main CLI unchanged in V1)
- `memoryOS/**`
- `uri/**`
- `.aios/logs/**`
- `.env`

## Per-OS Responsibility

### myworld.must_produce

- `docs/AIOS_PROVIDER_ABSORPTION.md` — codify the 6-stage recipe so the
  next provider absorption can replay it.
- Close contract + ledger entry.

### CapabilityOS.must_produce

- New `CapabilityCard` `cap_ollama_qwen25_7b_local` in
  `tests/fixtures/capabilities.json` with fields:
  - `id: cap_ollama_qwen25_7b_local`
  - `name: "Ollama Qwen 2.5 7B (local)"`
  - `kind: tool` or `model` (operator picks; existing VALID_KINDS)
  - `description: short`
  - `privacy: local`
  - `requires_network: false` (localhost only)
  - `executes_tools: false` (recommendation-only invariant)
  - `risk: low`
  - `evidence_refs: ["docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json"]`
- `audit --json` must still return `recommendation_only: true` and
  `execution_enabled: []`.
- `recommend --task "private local LLM with tool use"` should rank
  `cap_ollama_qwen25_7b_local` in top 3.

### hivemind.must_produce

- New `WorkerSpec` in `hivemind/local_workers.py` for `ollama_qwen25_7b`
  with: name, model_tag (`qwen2.5:7b`), endpoint (`http://localhost:11434`),
  capabilities list. NOT wired to invoke the network in V1 — only declared.
- Routing test that `intent_router` returns the new worker for matching
  intents (e.g. "summarize locally" / "draft memo private").

### memoryOS

- No source change. The new evidence + card will surface as drafts via
  the existing memory pulse / doc scout chain.

## Verification Gate

```bash
cd /home/user/workspaces/jaewon/myworld/CapabilityOS
python -m pytest tests/test_cli.py tests/test_observation.py -v
python -m capabilityos.cli audit --json
python -m capabilityos.cli recommend --task "private local LLM with tool use" --json
python -m capabilityos.cli show cap_ollama_qwen25_7b_local --json
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m pytest tests/test_local_worker_routing.py -v
cd /home/user/workspaces/jaewon/myworld
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
bash scripts/aios_coevolution/capability_pulse.sh
```

Pass criteria:

- New card visible in `capabilityos show cap_ollama_qwen25_7b_local`.
- `audit` returns `recommendation_only: true`, `execution_enabled: []`.
- `recommend` ranks the new card in top 3 for the test task.
- Hive `WorkerSpec` declared and routing test passes.
- Full test suite green.
- `capability_pulse` runs and reports the new observation count.

## Stop Conditions

- `capability_executes_provider`: any change wires actual network call.
- `auto_add_without_evidence`: card created without evidence_refs to the
  receipt at `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json`.
- `hive_binds_provider`: hivemind worker spec actually opens connection.
- `audit_regression`: audit no longer returns recommendation_only=true.
- `child_repo_scope_leak`: edits outside allowed_files.
- `verification_gate_failed`

## Receipts

Pending until verification.

## Work Packets

### WP-0055-A — Codex@myworld writes the recipe doc

- target_agent: codex
- target_repo: myworld
- status: done
- issued: 2026-05-13 KST
- accepted: 2026-05-13 KST
- closed: 2026-05-13 00:22 KST
- depends_on: none
- brief: |
    Author `docs/AIOS_PROVIDER_ABSORPTION.md` describing the 6-stage
    absorption recipe based on this contract's actual execution. Cite
    every artifact (receipt id, registry entry, card id, worker spec
    name) so the next absorption can fill the same template.
- result: `.aios/outbox/myworld/asc-0055.myworld.result.json`

### WP-0055-B — Codex@CapabilityOS adds the new card

- target_agent: codex
- target_repo: CapabilityOS
- status: done
- issued: 2026-05-13 KST
- accepted: 2026-05-13 00:17 KST
- closed: 2026-05-13 00:21 KST
- depends_on: none
- brief: |
    Add `cap_ollama_qwen25_7b_local` to `tests/fixtures/capabilities.json`
    with the fields listed in this contract's "CapabilityOS.must_produce"
    section. Ensure audit + recommend tests still pass. Reference the
    evidence receipt path in `evidence_refs`.
- result: `.aios/outbox/CapabilityOS/asc-0055.CapabilityOS.result.json`

### WP-0055-C — Codex@hivemind adds the WorkerSpec

- target_agent: codex
- target_repo: hivemind
- status: done
- issued: 2026-05-13 KST
- accepted: 2026-05-13 00:17 KST
- closed: 2026-05-13 00:21 KST
- depends_on: WP-0055-B
- brief: |
    Add a `WorkerSpec` for `ollama_qwen25_7b` in
    `hivemind/hivemind/local_workers.py`. Declared only — no network
    call. Update `tests/test_local_worker_routing.py` to assert that
    intent_router returns the new worker for `"private local LLM"`
    style intents.
- result: `.aios/outbox/hivemind/asc-0055.hivemind.result.json`

## Closeout

- CapabilityOS commit: `653e2ef`
- Hive commit: `56ae4e7`
- MyWorld recipe: `docs/AIOS_PROVIDER_ABSORPTION.md`
- CapabilityOS card: `cap_ollama_qwen25_7b_local`
- Hive worker spec: `ollama_qwen25_7b`
- Evidence receipt: `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json`
- CapabilityOS focused tests passed 16/16.
- Hive local worker routing tests passed 5/5.
- MyWorld AIOS tests passed 131/131.
- Capability pulse completed with `recommendation_only=true` and
  `audit_status=ok`.

Dispatch send was action-policy escalated because provider absorption is an
external-effect checkpoint class. Acting operator proceeded only because the
implementation is recommendation-only: CapabilityOS does not execute the
provider, and Hive records a declared worker spec without invoking Ollama.
