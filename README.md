# AIOS

[![tests](https://github.com/cjw0076/myworld/actions/workflows/tests.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/tests.yml)
[![docker](https://github.com/cjw0076/myworld/actions/workflows/docker.yml/badge.svg)](https://github.com/cjw0076/myworld/actions/workflows/docker.yml)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/cjw0076/myworld)

**Your AI agents learn from every run — instead of starting from zero.**

Most AI agents are stateless: each session starts over. AIOS keeps a local behavioral-memory ledger across runs and across models, so your agents carry forward what worked instead of repeating the same mistakes. (The longer-term vision — a shared ledger where every agent's runs help every other's — is below; today the value is single-user and local.)

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

Output (abridged):

```
  ── Run 1 — a brand-new agent, empty memory ───────────────────
    predictor: no_data  (0 prior runs)
    → no prior runs — starting from zero.

  ── AIOS records what the agent just did ──────────────────────
    ingested 1 run → ledger   (what worked: Read, Edit, Bash, Grep)

  ── Run 2 — same task, same question, now WITH memory ─────────
    → top suggestion: Edit   (grounded in the run recorded moments ago)

  ── Closing act — AI proposes, code verifies ──────────────────
    Checker says: PASS ✓  (3 courses scheduled, no deadline violated)
    Checker says: CAUGHT ✗ — the AI scheduled work after the deadline
```

Act one is the headline: the ledger turns run 1's experience into run 2's head start — offline, deterministic, using the real ingest/predict machinery. Act two shows the safety idea: AI proposes, deterministic code verifies, wrong answers are rejected. Every run leaves a provenance record.

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

**Prediction API** — open endpoint:

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

> The keyless free tier is small (10 requests/day, shared per IP) — if you get a
> `402 free tier exhausted`, register a free API key and pass it as `X-AIOS-Key`:
>
> ```sh
> curl -X POST https://aios-akashic.cjw070690.workers.dev/register
> ```

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

**Privacy guarantee:** only structural metadata is stored — tool names, sequence, category. No prompts, no outputs, no file contents. Verified by the Worker's privacy gate before any entry reaches D1. Contributions are **public and pseudonymous**: entries land in the shared ledger under a one-way salted pseudonym (your API key is never stored). The worker is additionally designed to enforce a k-anonymity floor (sparse rows served only once enough distinct contributors back them) — rolling out with the next worker deploy.

---

## Build on AIOS

AIOS has four small, self-contained extension seams — provider adapters, domain
minds, capability cards, and behavioral memory. Run `aios onboard`: its
`absorbed_not_executable` list is a live good-first-issue backlog (write the
`cursor` adapter in ~5 lines and watch it move to `verified_ready`).

→ **[docs/BUILD_ON_AIOS.md](docs/BUILD_ON_AIOS.md)** — the contributor guide.

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

| Module | Role | Availability |
|--------|------|--------------|
| **myworld** | Contracts, dispatch, operator kernel | public (this repo) |
| **hivemind** | Execution harness, verification, run receipts | public |
| **memoryOS** | Append-only memory graph, provenance, retrieval | private research repo |
| **CapabilityOS** | Tool/API routing recommendations | private research repo |
| **GenesisOS** | Assumption mutation, cross-domain reasoning | private research repo |

The OSS core in this repo is **self-contained**: the behavioral ledger, demo, and
`aios` CLI run without the private modules (they add the deeper memory graph and
routing research, and are being opened progressively).

---

## Docker

```sh
docker run --rm -e GEMINI_API_KEY=your_key -p 8741:8741 \
  ghcr.io/cjw0076/myworld:latest aios serve --host 0.0.0.0
```

---

## Current state

The ledger has **~1,400 behavioral entries** from real agent sessions. Prediction accuracy improves with scale — the network effect becomes visible above 10,000 entries. This is early, but the Akashic infrastructure is production-grade (Cloudflare Workers + D1, Merkle-verified, globally distributed).

Precise status: AIOS is kernel-complete, self-maintaining locally, world-service-objective-ready, and has live public infrastructure. Public-product readiness still needs real-user validation. See [`docs/AIOS_CANONICAL_SHAPE.md`](docs/AIOS_CANONICAL_SHAPE.md) for the required vocabulary.

If you run AI agents regularly, contributing your session patterns (opt-in, tool names only) is the fastest way to make the predictions useful.

---

## Learn more

- [docs/RESEARCH_GROUNDING.md](docs/RESEARCH_GROUNDING.md) — the research spine: which design decisions come from which papers, and what our own experiments (including the negatives) showed
- [`docs/AIOS_MINIMUM_KERNEL_AUDIT.md`](docs/AIOS_MINIMUM_KERNEL_AUDIT.md) — what the kernel actually does
- [`docs/AIOS_CANONICAL_SHAPE.md`](docs/AIOS_CANONICAL_SHAPE.md) — what "AIOS", "complete", "production", and "service" mean
- [`docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md`](docs/AIOS_AKASHIC_DISTRIBUTED_DESIGN.md) — ledger design and roadmap
- [`CLAUDE.md`](CLAUDE.md) / [`AGENTS.md`](AGENTS.md) — operator entry points
