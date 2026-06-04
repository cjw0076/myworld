---
name: local-llm-agent
description: >-
  Use the high-end LOCAL LLMs on this machine as a real agent/coding substrate
  (not just Claude). Dual RTX 5090 (64GB VRAM) + ollama already installed and
  serving. Best agentic-coding local model: qwen3-coder:30b. Covers how to pull,
  run, call (CLI / HTTP / OpenAI-compatible / function-calling), route through
  the AIOS provider harness, and use as a heterogeneous arm in absorption-probe.
  Per feedback_use_all_substrates_not_own_head — don't solve from one model.
---

# Local LLM as Agent Substrate

This box is a serious local-inference machine. Use it — a frozen provider is not
always the right (or private, or free) substrate.

## Hardware & runtime (verified 2026-06-05)

- **2× NVIDIA RTX 5090 = 64 GB VRAM** (Blackwell), 251 GB RAM, ~676 GB disk free.
- **ollama already installed & serving** — no install needed:
  - binary: `hivemind/.local/ollama/bin/ollama` (v0.22.1)
  - server: `http://127.0.0.1:11434` (used by memoryOS for `nomic-embed-text`)
- VRAM budget: a 30B-MoE Q4 (~18 GB) fits ONE 5090. Don't co-load two 30B on the
  same card; ollama schedules across both GPUs. Check free VRAM:
  `nvidia-smi --query-gpu=memory.free --format=csv,noheader`.

## Models (pull once, then they're assets)

```bash
OLLAMA=hivemind/.local/ollama/bin/ollama
$OLLAMA list                       # what's already local
$OLLAMA pull qwen3-coder:30b       # BEST agentic coding: 30B MoE/3.3B active, 256K ctx
```
Already cached on this machine: `qwen3-coder:30b` (agentic coding, primary),
`qwen3:30b-a3b` (general), `deepseek-coder-v2:16b`, `qwen3:8b`, `nomic-embed-text`.
Bigger flagships (Kimi K2.6, GLM-5.1, DeepSeek-V4) are enterprise-scale — do NOT
fit 64 GB; use a hosted provider for those.

## How to call it

```bash
OLLAMA=hivemind/.local/ollama/bin/ollama
# 1. CLI one-shot
$OLLAMA run qwen3-coder:30b "Write a Python function that …"

# 2. Native HTTP (non-streaming)
curl -s http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen3-coder:30b","prompt":"…","stream":false}' | jq -r .response

# 3. OpenAI-compatible chat (drop-in for any openai client)
curl -s http://127.0.0.1:11434/v1/chat/completions \
  -d '{"model":"qwen3-coder:30b","messages":[{"role":"user","content":"…"}]}'
```

### Function-calling / tool use (this is what makes it an *agent*)

qwen3-coder supports OpenAI-style `tools`. Pass tool schemas; the model returns
`tool_calls` you execute and feed back:
```bash
curl -s http://127.0.0.1:11434/v1/chat/completions -d '{
  "model":"qwen3-coder:30b",
  "messages":[{"role":"user","content":"List files then read README"}],
  "tools":[{"type":"function","function":{"name":"bash","description":"run a shell cmd",
    "parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"]}}}]
}' | jq '.choices[0].message.tool_calls'
```

## Route it through AIOS (preferred over raw curl for real work)

Register a local provider so the hive harness can route to it
(`hivemind/config/providers.yaml`, shape from `providers.example.yaml`):
```yaml
providers:
  local_ollama:
    kind: openai_compatible
    base_url: http://127.0.0.1:11434/v1
    api_key_env: OLLAMA_DUMMY_KEY   # any value; ollama ignores it
    models: [qwen3-coder:30b, qwen3:30b-a3b, deepseek-coder-v2:16b]
```
Also reachable as an AIOS local helper via `aios_helper_run`, and for embeddings
memoryOS already uses ollama `nomic-embed-text`.

## When to use local vs hosted

- **Local (this skill):** privacy-gated data (stays on box), bulk/cheap/offline
  work, a *heterogeneous* arm in [[absorption-probe]] (so it isn't all-Claude),
  embeddings, draft/triage where frontier quality isn't required.
- **Hosted (codex/gemini/claude):** frontier reasoning, final-quality artifacts.

## Hard rules

- Local LLM is a **substrate, not the operator** — route real execution through
  the hive harness with verification; don't let it self-approve actions.
- **Mind VRAM** — one 30B per card; `$OLLAMA ps` shows what's loaded; unload with
  `$OLLAMA stop <model>` before loading another big one.
- Don't assume a model is present — `$OLLAMA list` first; `pull` is a one-time
  ~18 GB download, not per-use.

## Related

- memory feedback_use_all_substrates_not_own_head · [[absorption-probe]]
- `hivemind/docs/PROVIDER_HARNESS_GUIDE.md` · `hivemind/config/providers.example.yaml`
