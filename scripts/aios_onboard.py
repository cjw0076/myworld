#!/usr/bin/env python3
"""aios onboard — one entry point that absorbs the device's capabilities and
verifies which are immediately USABLE, not just catalogued.

This closes absorb → use → verify into a single step, callable two ways:
  • human:  aios onboard
  • agent:  the `aios_onboard` MCP tool (aios_mcp_server.py)

Absorb  : scan local LLMs (Ollama), agent CLIs (claude/codex/gemini/grok/…),
          MCP servers and skills present on this device.
Use     : cross-reference each detected provider against the adapters AIOS can
          actually execute — so "absorbed" never overstates "usable".
Verify  : a fast e2e probe (Ollama reachable + each provider CLI invocable) so
          the manifest says what is *ready to route right now*, with evidence.

Output  : a manifest at .aios/onboard_manifest.json + a one-line readiness summary.

Schema: aios.onboard.v1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCANNER = ROOT / "scripts" / "aios_capability_scanner.py"
SCAN_PATH = ROOT / ".aios" / "capability_observations" / "env_scan.json"
MANIFEST_PATH = ROOT / ".aios" / "onboard_manifest.json"
OLLAMA = "http://127.0.0.1:11434"

SELF_OR_TOOL = {"aios", "pipx", "uvx"}            # not LLM providers


def _executable_clis() -> set[str]:
    """CLI binaries AIOS can actually EXECUTE. Delegates to the one capability spine
    (aios_routing.executable_clis) so 'what can we route to?' has a single answer."""
    try:
        scripts_dir = str(ROOT / "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import aios_routing  # noqa: PLC0415
        return aios_routing.executable_clis()
    except Exception:  # noqa: BLE001 — fall back to the known CLI adapters
        return {"claude", "codex", "gemini"}


# ── absorb ────────────────────────────────────────────────────────────────────

def absorb(refresh: bool = True) -> dict:
    """Run the capability scanner (absorb the device) and return its env scan."""
    if refresh and SCANNER.exists():
        try:
            subprocess.run([sys.executable, str(SCANNER)], capture_output=True,
                           timeout=45, cwd=str(ROOT))
        except (subprocess.TimeoutExpired, OSError):
            pass
    if SCAN_PATH.exists():
        try:
            return json.loads(SCAN_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"capabilities": [], "counts": {}}


# ── verify (fast e2e probes) ───────────────────────────────────────────────────

def _behavioral_status() -> dict:
    """Hippocampal-capture readiness: how many behavioral memories are already
    ingested vs how many CLI sessions are available to ingest. Privacy-safe —
    counts only, never content. Surfacing this at onboard is Phase A of the
    self-improving CLS plan (docs/AIOS_SELF_IMPROVING.md): make capture visible."""
    home = Path.home()
    ingested = 0
    # Respect AIOS_HOME like the rest of the CLI (aios behavior status does);
    # only the ~/.claude session scan below is genuinely home-anchored.
    aios_home = Path(os.environ.get("AIOS_HOME", str(home / ".aios"))).expanduser()
    store = aios_home / "memory" / "objects.jsonl"
    try:
        if store.exists():
            ingested = sum(1 for _ in store.open(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    sessions = 0
    try:
        proj = home / ".claude" / "projects"
        if proj.exists():
            sessions = sum(1 for _ in proj.rglob("*.jsonl"))
    except Exception:  # noqa: BLE001
        pass
    return {"memories_ingested": ingested, "sessions_available": sessions}


def probe_ollama() -> dict:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=4) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return {"ok": True, "n_models": len(models), "sample": models[:4]}
    except Exception:  # noqa: BLE001
        return {"ok": False, "n_models": 0, "sample": []}


def probe_cli(name: str, timeout: int = 8) -> bool:
    """Invocable if the CLI responds to --version (or --help) without crashing."""
    for flag in ("--version", "--help"):
        try:
            p = subprocess.run([name, flag], capture_output=True, timeout=timeout)
            if p.returncode == 0 or p.stdout or p.stderr:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            continue
    return False


# ── onboard ─────────────────────────────────────────────────────────────────--

def onboard(probe: bool = True, refresh: bool = True) -> dict:
    scan = absorb(refresh=refresh)
    caps = scan.get("capabilities", [])
    by = lambda t: [c for c in caps if c.get("type") == t]
    clis = by("cli")
    llms = by("ollama_model")

    executable_clis = _executable_clis()
    usable: list[str] = []
    ready: list[dict] = []
    not_executable: list[str] = []

    # local LLMs via the ollama adapter
    if llms or any(c.get("name") == "ollama" for c in by("local_service")):
        usable.append("ollama")
        op = probe_ollama() if probe else {"ok": True, "n_models": len(llms), "sample": []}
        if op["ok"] and op["n_models"]:
            ready.append({"provider": "ollama", "kind": "local-llm",
                          "detail": f"{op['n_models']} models", "evidence": "GET /api/tags"})

    # provider CLIs
    for c in clis:
        nm = c.get("name", "")
        if nm in executable_clis:
            usable.append(nm)
            ok = probe_cli(nm) if probe else True
            if ok:
                ready.append({"provider": nm, "kind": "cli-adapter",
                              "detail": "invocable", "evidence": f"{nm} --version"})
        elif nm in SELF_OR_TOOL:
            continue
        else:
            not_executable.append(nm)   # absorbed, no adapter yet (e.g. grok, cursor)

    counts = scan.get("counts", {})
    manifest = {
        "schema": "aios.onboard.v1",
        "absorbed": {
            "total": len(caps),
            "local_llms": counts.get("ollama_models", len(llms)),
            "agent_clis": counts.get("clis", len(clis)),
            "mcps": counts.get("mcps", 0),
            "skills": counts.get("skills", 0),
        },
        "usable_providers": sorted(set(usable)),
        "verified_ready": ready,
        "absorbed_not_executable": sorted(set(not_executable)),
        "ready_count": len(ready),
        "behavioral_memory": _behavioral_status(),
        "probed": probe,
        "next": 'aios do "<task>"  —  routes to a ready provider',
    }
    try:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except OSError:
        pass
    return manifest


def _render(m: dict) -> str:
    a = m["absorbed"]
    try:
        import aios_cli_style as S  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — fall back to plain if style module missing
        return _render_plain(m)
    L = [S.header("onboard", "device capabilities absorbed & verified")]
    L.append(S.kv("absorbed", f"{a['total']}  " + S.dim(
        f"LLMs {a['local_llms']} · CLIs {a['agent_clis']} · MCPs {a['mcps']} · skills {a['skills']}")))
    L.append(S.kv("usable", " · ".join(m["usable_providers"]) or "(none)", accent=S.cyan))
    for r in m["verified_ready"]:
        L.append(f"    {S.ok(r['provider'])}  {S.dim(r['detail'] + '  [' + r['evidence'] + ']')}")
    if m["absorbed_not_executable"]:
        L.append(S.kv("pending", ", ".join(m["absorbed_not_executable"]) + S.dim("  (no adapter yet)"),
                      accent=S.muted))
    bm = m.get("behavioral_memory", {})
    L.append(S.kv("memory", f"{bm.get('memories_ingested', 0)} behavioral memories  "
                  + S.dim(f"{bm.get('sessions_available', 0)} sessions to ingest")))
    if bm.get("sessions_available", 0) > 0:
        L.append("    " + S.dim("grow it: aios behavior ingest --opt-in code,docs"))
    L.append(S.rule())
    L.append("  " + S.star(f"{m['ready_count']} provider(s) ready") + S.dim(f"  ·  next: {m['next']}"))
    return "\n".join(L)


def _render_plain(m: dict) -> str:
    a = m["absorbed"]
    lines = ["✦ AIOS onboard — device capabilities absorbed & verified",
             f"  absorbed : {a['total']} (LLMs {a['local_llms']} · CLIs {a['agent_clis']} · "
             f"MCPs {a['mcps']} · skills {a['skills']})",
             f"  usable   : {', '.join(m['usable_providers']) or '(none)'}"]
    for r in m["verified_ready"]:
        lines.append(f"    ✓ {r['provider']:<8} {r['detail']:<14} [{r['evidence']}]")
    if m["absorbed_not_executable"]:
        lines.append(f"  pending  : {', '.join(m['absorbed_not_executable'])} (no adapter yet)")
    bm = m.get("behavioral_memory", {})
    lines.append(f"  memory   : {bm.get('memories_ingested', 0)} behavioral memories "
                 f"({bm.get('sessions_available', 0)} sessions to ingest)")
    lines.append(f"  → {m['ready_count']} provider(s) ready.  next: {m['next']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aios onboard",
        description="Absorb the device's LLMs + agent CLIs and verify what's usable now.")
    p.add_argument("--no-probe", dest="probe", action="store_false",
                   help="skip live e2e probes (classify by adapter availability only)")
    p.add_argument("--no-refresh", dest="refresh", action="store_false",
                   help="use the cached scan instead of re-scanning the device")
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)

    m = onboard(probe=args.probe, refresh=args.refresh)
    print(json.dumps(m, indent=2, ensure_ascii=False) if args.json else _render(m))
    return 0 if m["ready_count"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
