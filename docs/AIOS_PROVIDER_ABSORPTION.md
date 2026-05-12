# AIOS Provider Absorption

Provider absorption is how AIOS learns about a new provider, model, tool, or
runtime without immediately binding it to execution.

ASC-0055 is the first replayable example: Ollama-served Qwen 2.5 7B.

## Six Stages

1. Evidence
   - Capture public or local evidence as a receipt.
   - ASC-0055 evidence: `docs/evidence/2026-05-13-absorption-ollama-qwen25-7b.json`
   - Receipt id: `w-6eebb2055ff3`

2. Local Registry
   - Register the provider as an available primitive or local tool candidate.
   - ASC-0055 registry id: `tool.ollama_qwen25_7b`

3. CapabilityOS Card
   - Add a recommendation-only `CapabilityCard`.
   - ASC-0055 card id: `cap_ollama_qwen25_7b_local`
   - Required invariant: `executes_tools=false`.
   - Network invariant: localhost availability is described, but
     CapabilityOS does not connect to it.

4. Hive Worker Spec
   - Add a declared `WorkerSpec` so Hive can route or prepare plans.
   - ASC-0055 worker spec: `ollama_qwen25_7b`
   - Required invariant: declaration only. The contract does not wire a
     network call or provider execution.

5. Observation Collection
   - Once future dispatches recommend or use the card, CapabilityOS pulse
     records observations from result packets.
   - The confidence update is evidence-bound and stays recommendation-only.

6. Memory Draft
   - MemoryOS may receive provider/card observations as memory draft
     candidates through existing pulse/review paths.
   - No provider fact becomes accepted memory without review.

## Template

For the next provider absorption, create a contract with:

- provider name and runtime
- evidence receipt path and id
- local registry id
- CapabilityOS card id
- Hive worker spec name
- explicit non-execution invariant
- verification commands for `audit`, `recommend`, `show`, Hive routing tests,
  MyWorld tests, monitor, and capability pulse

## Stop Conditions

- No evidence receipt.
- CapabilityOS card executes tools.
- Hive worker spec opens a provider connection in the absorption contract.
- The provider bypasses Hive provider-loop or action policy.
- MemoryOS receives accepted memory without review.
