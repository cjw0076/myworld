"""CapabilityOS Environment Scanner — discovers actual capabilities in the local environment.

Scans:
  - Claude MCPs registered in ~/.claude.json
  - Claude skills in ~/.claude/skills/
  - Ollama models running on :11434
  - Installed CLIs (gemini, codex, aider, cursor, etc.)
  - Running local services (AIOS, Ollama ports)
  - Gemini MCP tools (if gemini CLI available)

Output: .aios/capability_observations/env_scan.json
Cache: 1 hour (re-scan if older)

Usage:
  python scripts/aios_capability_scanner.py          # scan + save
  python scripts/aios_capability_scanner.py --json   # print JSON
  python scripts/aios_capability_scanner.py --force  # ignore cache
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / ".aios" / "capability_observations" / "env_scan.json"
CACHE_TTL = 3600  # 1 hour


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def _run(cmd: list[str], timeout: int = 5) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def scan_mcps() -> list[dict]:
    cfg_path = Path.home() / ".claude.json"
    if not cfg_path.exists():
        return []
    try:
        cfg = json.loads(cfg_path.read_text())
        mcps = cfg.get("mcpServers", {})
        result = []
        for name, spec in mcps.items():
            result.append({
                "id": f"mcp_{name}",
                "name": name,
                "type": "mcp",
                "command": spec.get("command", ""),
                "args": spec.get("args", [])[:3],
                "env_keys": list((spec.get("env") or {}).keys()),
                "available": True,
            })
        return result
    except Exception:
        return []


def scan_skills() -> list[dict]:
    skills_dir = Path.home() / ".claude" / "skills"
    if not skills_dir.exists():
        return []
    result = []
    for entry in sorted(skills_dir.iterdir()):
        name = entry.name
        if name.startswith("_"):
            continue
        # Try to read description from skill file
        desc = ""
        skill_file = entry / "skill.md" if entry.is_dir() else entry
        if skill_file.exists() and skill_file.is_file():
            try:
                first_lines = skill_file.read_text(encoding="utf-8", errors="replace")[:400]
                for line in first_lines.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and len(line) > 10:
                        desc = line[:100]
                        break
            except Exception:
                pass
        result.append({
            "id": f"skill_{name.replace('-', '_')}",
            "name": name,
            "type": "claude_skill",
            "description": desc or f"Claude skill: {name}",
            "available": True,
        })
    return result


def scan_ollama_models() -> list[dict]:
    out = _run(["ollama", "list"], timeout=5)
    if not out:
        return []
    result = []
    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        size = parts[2] if len(parts) > 2 else "?"
        # Classify capability
        caps = []
        nl = name.lower()
        if "embed" in nl:
            caps = ["embedding"]
        elif "coder" in nl or "code" in nl or "deepseek" in nl:
            caps = ["code", "reasoning"]
        elif "qwen3" in nl and ("30b" in nl or "14b" in nl):
            caps = ["reasoning", "analysis", "code", "multilingual"]
        elif "qwen" in nl:
            caps = ["reasoning", "multilingual", "general"]
        else:
            caps = ["general"]
        result.append({
            "id": f"ollama_{name.replace(':', '_').replace('.', '_')}",
            "name": name,
            "type": "ollama_model",
            "size": size,
            "capabilities": caps,
            "cost": "free",
            "available": True,
        })
    return result


def scan_clis() -> list[dict]:
    cli_defs = [
        ("claude",  "Anthropic Claude Code CLI — agentic coding, hooks, MCP, skills"),
        ("codex",   "OpenAI Codex CLI — code generation, autonomous agent"),
        ("gemini",  "Google Gemini CLI — multimodal AI, web search, code, files"),
        ("grok",    "xAI Grok CLI — chat, code, reasoning"),
        ("cursor",  "Cursor — AI-native code editor (headless invoke possible)"),
        ("aider",   "Aider — AI pair programmer, git-aware code editing"),
        ("aios",    "AIOS kernel head — 5-OS organic pipeline, goal runner"),
        ("pipx",    "pipx — isolated Python tool installer"),
        ("uvx",     "uv tool runner — fast Python package execution"),
    ]
    result = []
    for cmd, desc in cli_defs:
        path = _which(cmd)
        if path:
            result.append({
                "id": f"cli_{cmd}",
                "name": cmd,
                "type": "cli",
                "path": path,
                "description": desc,
                "available": True,
            })
    return result


def scan_services() -> list[dict]:
    services = []
    # Ollama
    out = _run(["curl", "-s", "--max-time", "1", "http://localhost:11434/api/tags"], timeout=3)
    if out:
        try:
            models = [m["name"] for m in json.loads(out).get("models", [])][:5]
        except Exception:
            models = []
        services.append({
            "id": "service_ollama",
            "name": "ollama",
            "type": "local_service",
            "url": "http://localhost:11434",
            "description": f"Ollama local LLM runtime ({len(models)} models loaded)",
            "models": models,
            "available": True,
        })
    # AIOS serving
    out2 = _run(["curl", "-s", "--max-time", "1", "http://localhost:8741/status"], timeout=3)
    if out2:
        services.append({
            "id": "service_aios_serving",
            "name": "aios-serve",
            "type": "local_service",
            "url": "http://localhost:8741",
            "description": "AIOS serving API — organic pipeline, neural map, SSE streaming",
            "available": True,
        })
    return services


def run_scan() -> dict:
    import datetime
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    mcps = scan_mcps()
    skills = scan_skills()
    models = scan_ollama_models()
    clis = scan_clis()
    services = scan_services()

    all_caps = mcps + skills + models + clis + services
    return {
        "schema": "aios.capability_scan.v1",
        "scanned_at": ts,
        "total": len(all_caps),
        "counts": {
            "mcps": len(mcps),
            "skills": len(skills),
            "ollama_models": len(models),
            "clis": len(clis),
            "services": len(services),
        },
        "capabilities": all_caps,
    }


def load_cached() -> dict | None:
    if not CACHE_PATH.exists():
        return None
    age = time.time() - CACHE_PATH.stat().st_mtime
    if age > CACHE_TTL:
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="CapabilityOS environment scanner")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--force", action="store_true", help="ignore cache")
    parser.add_argument("--summary", action="store_true", help="one-line summary only")
    args = parser.parse_args()

    if not args.force:
        cached = load_cached()
        if cached:
            if args.json:
                print(json.dumps(cached, ensure_ascii=False, indent=2))
                return 0
            if args.summary:
                c = cached["counts"]
                print(f"[cap-scan] cached: {cached['total']} caps "
                      f"({c['mcps']} MCPs, {c['skills']} skills, "
                      f"{c['ollama_models']} models, {c['clis']} CLIs, "
                      f"{c['services']} services)")
                return 0

    data = run_scan()
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    c = data["counts"]
    print(f"[cap-scan] scanned: {data['total']} capabilities")
    print(f"  MCPs:         {c['mcps']}")
    print(f"  Skills:       {c['skills']}")
    print(f"  Ollama models:{c['ollama_models']}")
    print(f"  CLIs:         {c['clis']}")
    print(f"  Services:     {c['services']}")
    if not args.summary:
        print(f"\nTop capabilities:")
        for cap in data["capabilities"][:10]:
            print(f"  [{cap['type']:15s}] {cap['name']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
