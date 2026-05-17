# AIOS — myworld control plane

**AIOS** is a local-first agent operating layer. It wraps provider agent CLIs
(Claude Code, Codex CLI, local LLMs) in symbiosis — giving their one-shot
execution continuity, memory, governance, and recovery — and is spreading from
single-model toward a society of specialized local models.

`myworld` is the **control plane**: contracts, dispatch, the deterministic
kernel, and the always-on autopoietic round controller. It coordinates four
sibling OS repos:

- **hivemind** — execution layer (a contracted, verifiable, replayable run harness)
- **memoryOS** — memory substrate (an append-only, provenance-stamped, retrievable graph)
- **CapabilityOS** — capability map (recommendation-only routing)
- **GenesisOS** — divergence layer (re-framing reasoning across fixed axes)

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh
```

Then:

```sh
aios setup apply        # provision local models + config + the always-on service
aios self-model build   # what AIOS knows about itself
```

Full instructions: [`docs/AIOS_INSTALL.md`](docs/AIOS_INSTALL.md).

## Orientation

- `docs/AIOS_NORTHSTAR.md` — the system's final shape
- `docs/AIOS_DNA.md` — the invariants AIOS will not violate
- `docs/contracts/` — the contract ledger (every change is a contract)
- `docs/AIOS_AGENT_LEDGER.md` — the append-only cross-repo decision log
- `CLAUDE.md` / `AGENTS.md` — operator entry points

## Design in one line

The deterministic kernel keeps the invariants; the autopoietic loop (dream →
consolidate → verify → self-evolve) keeps AIOS learning; provider CLIs and
local models do the reasoning. AIOS is the operating layer, not the model.
