#!/bin/sh
# AIOS devcontainer setup — runs once after the container is created.
# Installs Ollama and provisions the qwen3 models needed for `aios serve`.
# If GEMINI_API_KEY or ANTHROPIC_API_KEY is set (via Codespaces Secrets),
# the heavy model pull is skipped — AIOS will use the cloud provider instead.
set -eu

echo "[aios devcontainer] checking providers..."

# If a cloud API key is already available, skip the GB-sized model download.
if [ -n "${GEMINI_API_KEY:-}" ]; then
  echo "[aios devcontainer] GEMINI_API_KEY found — skipping Ollama model download."
  echo "[aios devcontainer] AIOS will use Gemini REST (free tier) as provider."
  echo ""
  echo "[aios devcontainer] Start AIOS: aios serve → http://localhost:8741/"
  exit 0
fi
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "[aios devcontainer] ANTHROPIC_API_KEY found — skipping Ollama model download."
  echo "[aios devcontainer] AIOS will use Anthropic REST as provider."
  echo ""
  echo "[aios devcontainer] Start AIOS: aios serve → http://localhost:8741/"
  exit 0
fi

echo "[aios devcontainer] no API key found — installing Ollama with local models..."
echo "[aios devcontainer] (tip: set GEMINI_API_KEY as a Codespaces Secret to skip this)"

curl -fsSL https://ollama.com/install.sh | sh || {
  echo "[aios devcontainer] Ollama install failed — set GEMINI_API_KEY or ANTHROPIC_API_KEY to use without GPU"
  exit 0
}

echo "[aios devcontainer] starting Ollama daemon..."
nohup ollama serve >/tmp/ollama.log 2>&1 &
sleep 3

echo "[aios devcontainer] pulling qwen3 models (may take a few minutes)..."
ollama pull qwen3:1.7b || echo "[aios devcontainer] qwen3:1.7b pull failed (skipped)"
ollama pull qwen3:8b   || echo "[aios devcontainer] qwen3:8b pull failed (skipped)"

echo ""
echo "[aios devcontainer] done! Start the AIOS chat UI with:"
echo "  aios serve"
echo "  → http://localhost:8741/ (auto-forwarded to your browser)"
