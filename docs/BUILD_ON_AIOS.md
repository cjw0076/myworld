# Build on AIOS

AIOS is an operating layer for AI agents — it **wraps** the LLMs, agent CLIs, and
tools already on your machine and makes them learn from every run. The fastest
way into the community is to extend one of its four open seams. Each is small,
self-contained, and has a clear "done" test.

> New here? Run `aios onboard` first. It prints exactly what your device has and
> what AIOS can already use — and the `absorbed_not_executable` list is a live
> backlog of adapters waiting to be written. That list is your good-first-issue.

---

## The four extension seams

### 1. Provider adapters — *make an absorbed CLI usable*
`aios onboard` absorbs every agent CLI on the device, but only those with an
**adapter** can be routed to. Today `claude`, `codex`, `gemini`, and local
`ollama` have adapters; `grok` and `cursor` are absorbed but not yet executable.

**Add one:** a provider adapter is a single entry in `scripts/aios_adapters.py`
(`AdapterSpec(name, binary, argv_template)`) — how to shell out to the CLI and
read its reply. ~5 lines.

- **Good first issue:** add the `grok` adapter, then `aios onboard` should move it
  from `absorbed_not_executable` into `verified_ready`. That diff *is* the test.

### 2. Domain minds — *teach AIOS a domain*
A "mind" is a standalone tool that embeds expert domain knowledge as code
(`scripts/financemind.py`, `hrmind.py`, …) — zero external API, runnable offline.
The pattern: domain constants + a small model + a structured JSON result.

**Add one:** copy an existing mind, swap the domain knowledge, register a
`cap_tool_<name>` card (seam 3) and a one-line entry in
`scripts/aios_tool_executor.py`. Then `aios do "<your domain task>"` routes to it.

### 3. Capability cards — *make AIOS route to your thing*
`CapabilityOS` is a recommendation-only catalog. A card describes a tool/MCP/API/
skill so the router can rank it for a task. Cards are pure data with evidence
links — no execution, no network.

**Add one:** append a card to `CapabilityOS/capabilityos/catalog.py`
(`executes_tools: False`, non-empty `evidence_refs`), sync the fixture, run
`python -m pytest`. The audit gate enforces the invariants for you.

### 4. Behavioral memory — *grow the galaxy*
Every agent session is distilled into a behavioral signature (tool names + order,
never content) and added to the public AkashicRecord ledger. More sessions →
better next-tool predictions for everyone.

**Contribute:** `aios behavior contribute --opt-in code,docs`. Privacy is
structural — only tool/action types leave your machine, never arguments or
content. Verify any entry against the Merkle root: `curl …/root`.

---

## House rules (the DNA invariants)

Whatever you build, AIOS keeps seven invariants. Contributions are reviewed
against them:

1. **Recommendation-only** — CapabilityOS ranks, it never executes.
2. **Draft-first memory** — nothing becomes accepted memory without review.
3. **Append-only audit** — ledgers and receipts are never edited destructively.
4. **Named exits** — every loop has a stop condition (no silent runaway).
5. **Provenance** — every record cites its evidence.
6. **Operator override** — a human can always intervene.
7. **Privacy boundary** — no secrets, raw exports, or private paths in shared
   artifacts. Ever.

---

## Contributing

1. Fork the relevant repo (`myworld`, `hivemind`, `memoryOS`, `CapabilityOS`).
2. Make the smallest change that adds one capability through one seam.
3. Add or update the one test that fails if your change breaks (`python -m pytest`).
4. Open a PR describing which seam you extended and the before/after of
   `aios onboard` or `aios do` where relevant.

Good contributions are **small and verifiable**: one adapter, one mind, one card,
one fix. The seams are designed so you never need to understand the whole
organism to add value to it.

---

## Where the community lives

- **Discussions** — design questions, "what should I build", show-and-tell.
- **Issues** — the `absorbed_not_executable` backlog, `good-first-issue` labels.
- **The ledger** — your contributed sessions are visible (and provable) at the
  public AkashicRecord dashboard.

> Maintainers: wire the channel links here (GitHub Discussions / chat) and pin a
> "first adapter in 10 minutes" walkthrough — the seam-1 grok adapter is the
> canonical starter.
