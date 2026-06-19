# AIOS

[![tests](https://github.com/cjw0076/myworld/actions/workflows/tests.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/tests.yml)
[![docker](https://github.com/cjw0076/myworld/actions/workflows/docker.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/docker.yml)
[![PyPI](https://img.shields.io/pypi/v/aios-os)](https://pypi.org/project/aios-os/)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/cjw0076/myworld)

**An AI agent that learns from every run — and from every other agent's runs.**

Most AI agents are stateless. Each session starts from zero. AIOS keeps a behavioral memory ledger across sessions, across models, and across users — so the agent gets measurably smarter over time.

---

## The problem

You run Claude Code or Codex to fix a bug. It works. Tomorrow you run it again on a similar problem. It makes the same mistakes, takes the same wrong turns. **Nothing carried over.**

Multiply this by a team. Or by every developer running AI agents today. Billions of execution minutes, zero learning transfer.

---

## What AIOS does

**1. Remembers what worked** — Every agent session is distilled into a behavioral signature: what tools were used, in what order, for what kind of task. Stored in a global ledger with a Merkle-verified audit trail.

**2. Predicts what comes next** — Given your current context ("just ran a failing test, need to fix the import"), AIOS finds similar past sessions and tells you which tool to reach for next — before you waste tokens on wrong turns.

**3. Transfers knowledge across providers** — A Codex session that found an efficient debugging pattern makes the Claude agent smarter. A local LLM run that hit a doom loop prevents the next agent from repeating it.

---

## Quickstart

```sh
# No GPU, no API key needed for the first demo:
git clone https://github.com/cjw0076/myworld && cd myworld
pip install -e .
aios demo
```

Output:

```
  Checker says: PASS ✓  (3 courses scheduled, no deadline violated)
  Checker says: CAUGHT ✗ — the AI scheduled work after the deadline
```

The demo shows the core idea: AI proposes, deterministic code verifies, wrong answers are rejected. Every run leaves a provenance record.

---

## AkashicRecord — live behavioral ledger

The global memory layer is live and public. No sign-up required.

```
https://aios-akashic.cjw070690.workers.dev/
```

**Dashboard** — real-time entry counts by category, provider, OS origin, Merkle root.

**Memory Galaxy** — 3D force-directed graph of behavioral similarity. Nodes are agent sessions, edges are semantic similarity. Categories glow when you type a context.

```
https://aios-akashic.cjw070690.workers.dev/galaxy
```

**Prediction API** — open endpoint, no auth:

```sh
curl -X POST https://aios-akashic.cjw070690.workers.dev/predict \
  -H "Content-Type: application/json" \
  -d '{"context": "running tests, got import error, need to fix the module", "top_k": 3}'
```

```json
{
  "predictions": [
    { "tool": "Bash",  "score": 0.54 },
    { "tool": "Edit",  "score": 0.31 },
    { "tool": "Read",  "score": 0.15 }
  ],
  "n_similar": 30
}
```

**Merkle verification** — every entry is content-addressed and provable:

```sh
curl https://aios-akashic.cjw070690.workers.dev/root
curl https://aios-akashic.cjw070690.workers.dev/proof/<entry-id>
```

---

## Full install — with live providers

```sh
# One command: clones repos + installs + wires into your agent CLIs
curl -fsSL https://raw.githubusercontent.com/cjw0076/myworld/main/install.sh | sh

# Provision a local model (no API cost):
aios setup apply        # pulls qwen3:1.7b via Ollama

# Start the chat UI:
aios serve              # → http://localhost:8741/
```

### Provider options

AIOS auto-selects the best available provider:

| Provider | Setup | Cost |
|----------|-------|------|
| Ollama (local) | `aios setup apply` | Free |
| Gemini REST | `GEMINI_API_KEY=...` | Free tier (1500 req/day) |
| Anthropic Claude | `ANTHROPIC_API_KEY=...` | Pay-per-token |

In GitHub Codespaces: add your key under **Settings → Codespaces → Secrets**.

---

## Contribute your agent sessions

Every session you run makes the global ledger smarter for everyone:

```sh
# Opt-in: send your local behavioral patterns (tool names only, no content)
aios behavior contribute --opt-in code,docs
```

**Privacy guarantee:** only structural metadata is stored — tool names, sequence, category. No prompts, no outputs, no file contents. Verified by the Worker's privacy gate before any entry reaches D1.

---

## Architecture (for developers)

```
Your agent CLI (Claude Code / Codex / local LLM)
        ↓
   aios_head.py  ←── memory retrieval, capability routing, doom-loop guard
        ↓
   aios_turn_loop.py  ←── event log, session record, tool dispatch
        ↓
   AkashicRecord (Cloudflare Worker + D1)  ←── global behavioral ledger
        ↓
   /predict  /graph  /proof  /checkpoints  ←── open API
```

Five OS modules, each owning a distinct authority layer:

| Module | Role |
|--------|------|
| **myworld** | Contracts, dispatch, operator kernel |
| **hivemind** | Execution harness, verification, run receipts |
| **memoryOS** | Append-only memory graph, provenance, retrieval |
| **CapabilityOS** | Tool/API routing recommendations |
| **GenesisOS** | Assumption mutation, cross-domain reasoning |

---

## Docker

```sh
docker run --rm -e GEMINI_API_KEY=your_key -p 8741:8741 \
  ghcr.io/cjw0076/myworld:latest aios serve --host 0.0.0.0
```

---

## Current state

The ledger has **~1,400 behavioral entries** from real agent sessions. Prediction accuracy improves with scale — the network effect becomes visible above 10,000 entries. This is early, but the infrastructure is production-grade (Cloudflare Workers + D1, Merkle-verified, globally distributed).

If you run AI agents regularly, contributing your session patterns (opt-in, tool names only) is the fastest way to make the predictions useful.

---

## Learn more

- [`docs/AIOS_MINIMUM_KERNEL_AUDIT.md`](docs/AIOS_MINIMUM_KERNEL_AUDIT.md) — what the kernel actually does
- [`docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md`](docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md) — ledger design and roadmap
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — operator entry points
