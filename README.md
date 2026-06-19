# AIOS — myworld control plane

[![tests](https://github.com/cjw0076/myworld/actions/workflows/tests.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/tests.yml)
[![docker](https://github.com/cjw0076/myworld/actions/workflows/docker.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/docker.yml)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/cjw0076/myworld)

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

**Easiest — no install needed:** click the badge above to open in GitHub Codespaces (browser IDE, free tier available). Then run `aios demo` in the terminal.

Or locally (3-line quickstart):

```sh
git clone https://github.com/cjw0076/myworld && cd myworld
pip install -e .
aios demo
```

After `pip install -e .` the `aios` command is registered globally — no need for `python bin/aios` or activating a virtualenv each time.

It shows the one idea AIOS is built around: the AI only *proposes*, then plain
deterministic code checks the part that has to be exact — and **rejects** the
answer if the check fails. The demo runs the same checker on a good study plan
(passes) and on a plan with a realistic AI slip — a session scheduled past its
deadline — and watches the code catch it. Every result leaves a provenance file.

## Live AI pipeline demo (requires a provider)

Once you have Ollama running (`aios setup apply`) or an API key set, run the
full organic pipeline in one command:

```sh
aios demo --chat
```

Example output:

```
  ┌─────────────────────────────────────────────────────────────┐
  │  AIOS demo --chat  — live organic pipeline run               │
  └─────────────────────────────────────────────────────────────┘

  Goal:     What is AIOS and how does the organic pipeline work?
  Provider: ollama_rest (local Ollama — no cost)
  Memory:   215 hit(s) recalled from memoryOS
  Turns:    4   exit=max_turns

  Answer:

    AIOS is a system that enables end-users to control and view how AI
    agents operate, ensuring transparency in their tasks. The organic
    pipeline involves capturing directives, managing task distribution,
    and allowing agents to perform their roles effectively while
    maintaining control and visibility for the user.

  Provenance: organic pipeline (preamble → loop → synthesis), no hardcoded output.
  Next: `aios serve` → http://localhost:8741/ for the full interactive UI.
```

Use `--goal "your question"` to ask anything.
Use `--json` for structured output.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh
aios setup apply        # provision local models (qwen3:1.7b / qwen3:8b via Ollama)
```

Full instructions: [`docs/AIOS_INSTALL.md`](docs/AIOS_INSTALL.md).

## Provider options — choose what fits your environment

AIOS auto-selects the best available provider in this order:

| Provider | Requires | Cost | Latency |
|----------|----------|------|---------|
| Ollama (local) | GPU + `aios setup apply` | Free | ~0.2–7s |
| Gemini REST | `GEMINI_API_KEY` | Free tier (1500 req/day) | ~1–3s |
| Anthropic REST | `ANTHROPIC_API_KEY` | Pay-per-token | ~1–3s |

```sh
# Check which providers are active right now:
curl http://localhost:8741/status

# Use Gemini (no GPU needed):
export GEMINI_API_KEY=your_key_here
aios serve

# Use Anthropic Claude (no GPU needed):
export ANTHROPIC_API_KEY=your_key_here
aios serve
```

In GitHub Codespaces: add your API key as a **Codespaces Secret** (`Settings → Codespaces → Secrets`) and it will be available as an environment variable when the container starts.

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

## Docker quickstart

No install needed — pull and run with your Gemini free-tier key:

```sh
docker run --rm -e GEMINI_API_KEY=your_key_here -p 8741:8741 \
  ghcr.io/cjw0076/myworld:latest \
  aios serve --host 0.0.0.0
```

Then open http://localhost:8741/ in your browser.

The default image command works offline with no key:

```sh
docker run --rm ghcr.io/cjw0076/myworld:latest
```

> **Note:** `--host 0.0.0.0` is required when running inside Docker — without it the server binds to the container's loopback only and `-p 8741:8741` has nothing to forward to.

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
