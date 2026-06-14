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

## See it in 30 seconds (no API key, no GPU, no network)

```sh
git clone https://github.com/cjw0076/myworld && cd myworld
python bin/aios demo        # or: bin/aios demo
```

It shows the one idea AIOS is built around: the AI only *proposes*, then plain
deterministic code checks the part that has to be exact — and **rejects** the
answer if the check fails. The demo runs the same checker on a good study plan
(passes) and on a plan with a realistic AI slip — a session scheduled past its
deadline — and watches the code catch it. Every result leaves a provenance file.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh
aios setup apply        # provision local models (qwen3:1.7b / qwen3:8b via Ollama)
```

Full instructions: [`docs/AIOS_INSTALL.md`](docs/AIOS_INSTALL.md).

## Chat UI — talk to your AIOS

After install, start the web interface:

```sh
aios serve              # → http://localhost:8741/
aios serve --tunnel     # → https://xxxx.trycloudflare.com  (shareable public URL)
```

The UI is a conversation thread backed by the organic pipeline: each message
runs through memory retrieval → tool loop (up to 6 turns) → local LLM
synthesis → Korean / English answer. Session history persists in the browser;
conversation context carries across messages in the same tab.

No API key required if Ollama is running locally with qwen3 models.
Provider can be switched (claude / codex / gemini / local) per message.

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
