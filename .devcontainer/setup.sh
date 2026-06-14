#!/bin/sh
# AIOS devcontainer setup — runs once after the container is created.
# Installs Ollama and provisions the qwen3 models needed for `aios serve`.
set -eu

echo "[aios devcontainer] installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh || {
  echo "[aios devcontainer] Ollama install failed — aios serve will run without local models"
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
