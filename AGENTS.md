# MyWorld Agent Entry

Before working from the `myworld/` workspace root, read these files:

1. `docs/AIOS_NORTHSTAR.md`
2. `docs/AIOS_DEFINITION.md`
3. `docs/AIOS_AGENT_PROTOCOL.md`
4. `docs/AIOS_SMART_CONTRACT.md`
5. `docs/AIOS_WORK_DISPATCH.md`
6. `docs/AIOS_BUILD_METHOD.md`
7. `docs/AIOS_AGENT_LEDGER.md`
8. The role file for the repo you are touching:
   - `docs/agents/HIVEMIND_AGENT.md`
   - `docs/agents/MEMORYOS_AGENT.md`
   - `docs/agents/CAPABILITYOS_AGENT.md`

Repository boundaries:

- `hivemind/` owns execution, scheduling, provider CLI wrapping, proofs, and verification.
- `memoryOS/` owns memory, context paging, provenance, review lifecycle, and retrieval traces.
- `CapabilityOS/` owns capability maps, routing recommendations, tool/MCP/API/skill catalogs, and fallback plans.

Do not mix ownership unless an AIOS smart contract or operator instruction explicitly assigns cross-repo work.

Default rule: `myworld/` dispatches work; implementation happens inside the
owning lower repo.

Codex's primary control-plane duty is to search, retrieve context, route
capabilities, issue precise work packets, verify evidence, and propose better
AIOS methods when the current loop cannot close.
