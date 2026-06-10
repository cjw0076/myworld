---
contract_id: ASC-0195
slug: memoryos-embed-fallback-hermetic-tests
status: closed
goal: Make MemoryOS embedding fallback tests hermetic so the full repo gate is stable whether local Ollama is running or absent.
created: 2026-05-18 00:25 KST
accepted: 2026-05-18 KST
closed: 2026-05-18 00:39 KST
acceptance_authority: codex@myworld acting operator under continuous AIOS completion goal; triggered by ASC-0194 full-gate blocker.
proposed_by: codex@myworld
supersedes: none
---

# ASC-0195 MemoryOS — Embed Fallback Hermetic Tests

## Why

ASC-0194 produced a focused-verified MemoryOS Graph Control Model alpha, but
full `python -m pytest -q` was not claimable because four existing embedding
fallback tests assume Ollama is absent while the current AIOS machine has
Ollama reachable at the default endpoint.

This is not a Graph Control Model bug. It is a test-environment coupling bug:
fallback tests must deliberately route to an unreachable local endpoint or
mock the embedding helper, instead of depending on the ambient machine state.

DNA references: Invariant 4 (named exit), Invariant 5 (provenance chain),
Invariant 8 (bounded verification), Invariant 9 (testable operating behavior).

## Scope

repos:

- `memoryOS`

allowed_files:

- `memoryOS/tests/test_embed.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/docs/STATUS.md`
- `memoryOS/docs/TODO.md`

forbidden_files:

- `.env`
- raw exports
- private runtime auth files
- `memoryOS/memory/objects.jsonl`
- `memoryOS/memory/sources.jsonl`
- `memoryOS/memory/retrieval_traces.jsonl`
- `memoryOS/memory/graph_control_runs.jsonl`
- production embedding implementation files unless the tests prove a real
  product defect beyond test hermeticity

## AIOS Role Evidence

### 5-Persona Use

- Hive / Wrapper: codex@memoryOS through child watcher; no provider fallback
  expected unless watcher failure occurs.
- MemoryOS / Retriever: no retrieval trace required; this is a MemoryOS-owned
  test harness hardening task discovered by ASC-0194 verification evidence.
- CapabilityOS / Router: no new tool route required; local pytest and
  py_compile are sufficient.
- GenesisOS / Philosophy: discomfort identified: "fallback" tests were really
  "whatever the host happens to run" tests.
- MyWorld / Sovereign: myworld issues the contract, dispatches to memoryOS,
  collects result, and decides whether ASC-0194 can advance toward full close.

## memoryOS Must Produce

- Hermetic fallback tests in `tests/test_embed.py` that pass both when Ollama
  is reachable and when it is absent.
- No mutation of real memory ledgers.
- Repo-local worklog/status note explaining why the test fixture was changed.

## CapabilityOS

No role in this contract. This is not a tool search problem; it is a
deterministic test fixture problem.

## GenesisOS

Advisory role only: name the semantic trap. "Ollama absent" is a condition the
test must create, not an assumption about the host.

## Verification Gate

Run from `memoryOS/`:

```bash
python -m pytest tests/test_embed.py -q
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py tests/test_doctor.py tests/test_mcp.py -q
python -m py_compile memoryos/cli.py memoryos/embed.py memoryos/schema.py memoryos/store.py
git diff --check
```

Done means the failing four embed fallback cases from ASC-0194 pass on a host
with live Ollama and no production memory ledgers are changed.

## Stop Conditions

- The fix requires changing production embedding semantics instead of test
  isolation.
- Tests need ambient local Ollama availability to pass.
- Any raw memory ledger, private runtime auth file, `.env`, or private export path is
  touched.
- Full gate still fails for reasons not isolated to known environment coupling.

## Work Packets

### WP-0195-A — Harden MemoryOS embed fallback tests

- target_agent: codex
- target_repo: memoryOS
- status: done
- issued: 2026-05-18
- accepted: 2026-05-18 00:33 KST
- closed: 2026-05-18 00:39 KST
- depends_on: ASC-0194 focused result
- brief: |
    Read this contract and `memoryOS/tests/test_embed.py`. Fix only the
    embedding fallback tests that assume ambient Ollama absence. Make absent
    fallback tests explicitly use an unreachable local URL or a mock so they
    pass even when `http://127.0.0.1:11434` is alive. Do not change production
    embedding behavior unless a real defect is proven. Run the verification
    gate and write a concise result packet.
- result: `.aios/outbox/memoryOS/asc-0195.memoryOS.result.json`

## Result

MemoryOS commit `146b946 Harden embed fallback tests` closed the environment
coupling. The worker changed only the allowed MemoryOS test/doc files:

- `memoryOS/tests/test_embed.py`
- `memoryOS/docs/AGENT_WORKLOG.md`
- `memoryOS/docs/STATUS.md`
- `memoryOS/docs/TODO.md`

The fix creates the Ollama-absent condition explicitly: CLI fallback tests use
a reserved unreachable local URL, and in-process fallback tests mock
`memoryos.embed.get_embedding` to return `None`. No production embedding
semantics or real memory ledgers were changed.

## Verification Receipts

Worker receipts:

```bash
cd memoryOS
python -m pytest tests/test_embed.py -q
# 65 passed, 5 subtests passed
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py tests/test_doctor.py tests/test_mcp.py -q
# 578 passed, 5 subtests passed
python -m py_compile memoryos/cli.py memoryos/embed.py memoryos/schema.py memoryos/store.py
python -m pytest -q
# 2027 passed, 18 subtests passed
git diff --check
```

Supervisor recheck from myworld:

```bash
cd memoryOS
python -m pytest tests/test_graph_control.py tests/test_embed.py tests/test_schema.py tests/test_doctor.py tests/test_mcp.py -q
# 578 passed, 5 subtests passed
python -m py_compile memoryos/cli.py memoryos/embed.py memoryos/schema.py memoryos/store.py
git diff --check
```

## Closeout

ASC-0195 is closed. The ASC-0194 full-gate blocker caused by ambient Ollama is
removed; remaining ASC-0194 work is the myworld-side dream-cycle wiring, not
embed fallback hermeticity.
