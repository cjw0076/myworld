#!/usr/bin/env bash
# aios_install.sh — Bootstrap AIOS on a new machine.
#
# Usage:
#   git clone <myworld-repo> ~/aios && cd ~/aios && bash scripts/aios_install.sh
#   AIOS_PROFILE=~/.config/aios bash scripts/aios_install.sh  # custom profile dir
#
# What this does:
#   1. Detect AIOS_ROOT (repo root)
#   2. Install Python dependencies
#   3. Wire Claude Code hooks (.claude/settings.json already in repo)
#   4. Wire Gemini CLI hooks (profile-level .gemini/settings.json)
#   5. Configure AIOS_ROOT env var (adds to shell profile)
#   6. Verify install with aios_provider.py status
#
# DNA invariant #7: never writes secrets — vault must be initialized separately
set -euo pipefail

# ── detect root ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AIOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export AIOS_ROOT

echo "=== AIOS Install ==="
echo "AIOS_ROOT: $AIOS_ROOT"
echo ""

# ── python deps ───────────────────────────────────────────────────────────────
echo "→ Installing Python dependencies..."
pip install --quiet cryptography argon2-cffi keyring 2>/dev/null || {
    pip3 install --quiet cryptography argon2-cffi keyring 2>/dev/null || true
}
echo "  ✓ cryptography, argon2-cffi, keyring"

# ── claude code hooks ─────────────────────────────────────────────────────────
CLAUDE_SETTINGS="$AIOS_ROOT/.claude/settings.json"
if [ -f "$CLAUDE_SETTINGS" ]; then
    echo "→ Claude Code hooks: settings.json exists in repo ✓"
else
    echo "  ⚠ $CLAUDE_SETTINGS not found — hooks not wired for Claude Code"
fi

# ── gemini cli hooks ──────────────────────────────────────────────────────────
GEMINI_PROFILE="${XDG_CONFIG_HOME:-$HOME}/.gemini"
GEMINI_SETTINGS="$GEMINI_PROFILE/settings.json"

if command -v gemini >/dev/null 2>&1; then
    echo "→ Gemini CLI: found $(gemini --version 2>/dev/null || echo '?')"
    mkdir -p "$GEMINI_PROFILE"

    if [ -f "$GEMINI_SETTINGS" ]; then
        # Merge hooks into existing settings
        python3 - "$GEMINI_SETTINGS" "$AIOS_ROOT" <<'PY'
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
aios_root = sys.argv[2]

settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}

hooks = {
    "SessionStart": [{"hooks": [{"type": "command",
        "command": f'bash "{aios_root}/scripts/aios_session_brief.sh" 2>/dev/null || true'}]}],
    "BeforeTool": [{"matcher": "run_shell_command|replace|write_file", "hooks": [{"type": "command",
        "command": f'python3 "{aios_root}/scripts/aios_guard_hook.py" 2>/dev/null || true'}]}],
    "AfterTool": [{"matcher": "run_shell_command|replace|write_file", "hooks": [{"type": "command",
        "command": f'python3 "{aios_root}/scripts/aios_hive_verify_hook.py" 2>/dev/null || true'}]}],
    "AfterAgent": [{"hooks": [{"type": "command",
        "command": f'bash "{aios_root}/scripts/aios_stop_hook.sh" 2>/dev/null || true'}]}],
    "BeforeAgent": [{"hooks": [{"type": "command",
        "command": f'python3 "{aios_root}/scripts/aios_education_hook.py" 2>/dev/null || true'}]}],
}

# Only add mcpServers if not already present
if "mcpServers" not in settings:
    settings["mcpServers"] = {}
if "aios" not in settings.get("mcpServers", {}):
    settings.setdefault("mcpServers", {})["aios"] = {
        "command": "python3",
        "args": [f"{aios_root}/scripts/aios_mcp_server.py"]
    }

settings["hooks"] = hooks
settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2))
print(f"  ✓ {settings_path} updated with AIOS hooks + MCP server")
PY
    else
        # Write fresh settings
        python3 - "$GEMINI_SETTINGS" "$AIOS_ROOT" <<'PY'
import json, sys
from pathlib import Path

settings_path = Path(sys.argv[1])
aios_root = sys.argv[2]

settings = {
    "mcpServers": {"aios": {"command": "python3", "args": [f"{aios_root}/scripts/aios_mcp_server.py"]}},
    "hooks": {
        "SessionStart": [{"hooks": [{"type": "command",
            "command": f'bash "{aios_root}/scripts/aios_session_brief.sh" 2>/dev/null || true'}]}],
        "BeforeTool": [{"matcher": "run_shell_command|replace|write_file", "hooks": [{"type": "command",
            "command": f'python3 "{aios_root}/scripts/aios_guard_hook.py" 2>/dev/null || true'}]}],
        "AfterTool": [{"matcher": "run_shell_command|replace|write_file", "hooks": [{"type": "command",
            "command": f'python3 "{aios_root}/scripts/aios_hive_verify_hook.py" 2>/dev/null || true'}]}],
        "AfterAgent": [{"hooks": [{"type": "command",
            "command": f'bash "{aios_root}/scripts/aios_stop_hook.sh" 2>/dev/null || true'}]}],
        "BeforeAgent": [{"hooks": [{"type": "command",
            "command": f'python3 "{aios_root}/scripts/aios_education_hook.py" 2>/dev/null || true'}]}],
    }
}
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=2))
print(f"  ✓ {settings_path} created with AIOS hooks + MCP server")
PY
    fi
else
    echo "  ℹ Gemini CLI not found — skipping Gemini hooks (install with: npm install -g @google/gemini-cli)"
fi

# ── shell env ─────────────────────────────────────────────────────────────────
SHELL_RC="${HOME}/.bashrc"
[ -f "${HOME}/.zshrc" ] && SHELL_RC="${HOME}/.zshrc"

if ! grep -q "AIOS_ROOT" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# AIOS" >> "$SHELL_RC"
    echo "export AIOS_ROOT=\"$AIOS_ROOT\"" >> "$SHELL_RC"
    echo "  ✓ AIOS_ROOT added to $SHELL_RC"
else
    echo "  ✓ AIOS_ROOT already in $SHELL_RC"
fi

# ── ollama (optional) ─────────────────────────────────────────────────────────
if command -v ollama >/dev/null 2>&1 || [ -f "$AIOS_ROOT/hivemind/.local/ollama/bin/ollama" ]; then
    echo "→ ollama: found"
    echo "  To enable local LLM: ollama pull qwen3-coder:30b  (~18GB)"
else
    echo "  ℹ ollama not found — local LLM unavailable (optional)"
fi

# ── vault init reminder ───────────────────────────────────────────────────────
VAULT_DIR="${AIOS_VAULT_DIR:-$HOME/.aios/vault}"
if [ ! -f "$VAULT_DIR/vault.enc" ]; then
    echo ""
    echo "  ⚠ Credential vault not initialized."
    echo "    Run: python3 $AIOS_ROOT/scripts/aios_vault.py init"
fi

# ── verify ────────────────────────────────────────────────────────────────────
echo ""
echo "→ Provider status:"
python3 "$AIOS_ROOT/scripts/aios_provider.py" status 2>/dev/null | sed 's/^/  /'

echo ""
echo "=== AIOS install complete ==="
echo "  AIOS_ROOT=$AIOS_ROOT"
echo "  Reload shell: source $SHELL_RC"
echo ""
echo "Quick start:"
echo "  python3 $AIOS_ROOT/scripts/aios_multi_substrate.py run --task 'hello world test' --emit"
echo "  python3 $AIOS_ROOT/scripts/aios_checkpoint.py list"
echo "  python3 $AIOS_ROOT/scripts/aios_provider.py status"
