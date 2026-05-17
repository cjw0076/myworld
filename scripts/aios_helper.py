#!/usr/bin/env python3
"""aios helper — the AIOS Specialist Helper Layer (aios.specialist_helper.v1).

The local LLM is not one central daemon; it is a population of narrow
specialist helpers — callable "code parts" an agent uses (founder conception
2026-05-16, validated against Minsky's Society of Mind and NVIDIA's
"Small Language Models are the Future of Agentic AI").

Subcommands:
  list                       list registered specialist helpers
  route   --task <text>      ask which helper fits a task (delegates to CapabilityOS recommend)
  run     --helper <id> --input <text|@file>   invoke a helper (calls the local LLM)
  register ...               add a helper card to the catalog

CapabilityOS is recommendation-only and must not execute; this runner is the
thin invocation adapter. A helper is a TOOL — it computes/proposes, never an
authority (no memory accept, no contracts, no overriding frozen agents).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HELPER_SCHEMA = "aios.specialist_helper.v1"
CATALOG_REL = ".aios/helpers/catalog.json"
TIERS_REL = ".aios/helpers/model_tiers.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
OBSERVATIONS_REL = ".aios/helpers/observations.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def installed_models() -> list[str]:
    """Models actually available in the local runtime (Ollama). Empty on failure."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS_URL, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:  # noqa: BLE001
        return []


def resolve_model(root: Path, helper: dict[str, Any]) -> tuple[str, str]:
    """Model-agnostic resolution: pick the best installed model for a helper.

    A helper may declare a `tier` (fast/default/strong) and/or a `model` hint.
    The runner resolves against models actually installed — attach any model
    and the layer adapts; no single model is load-bearing.
    Returns (model_name, reason)."""
    available = installed_models()
    avail_set = set(available)

    # 1. tier-based resolution (preferred — model-agnostic)
    tier = helper.get("tier")
    if tier:
        tiers_path = root / TIERS_REL
        if tiers_path.exists():
            try:
                tiers = json.loads(tiers_path.read_text(encoding="utf-8")).get("tiers", {})
                prefer = tiers.get(tier, {}).get("prefer", [])
                for m in prefer:
                    if m in avail_set:
                        return m, f"tier:{tier} resolved to installed {m}"
            except (ValueError, OSError):
                pass

    # 2. explicit model hint
    hint = helper.get("model")
    if hint and hint in avail_set:
        return hint, f"model hint {hint} (installed)"

    # 3. graceful fallback — any installed model
    if available:
        return available[0], f"fallback: requested unavailable, using installed {available[0]}"

    # 4. last resort — return the hint and let the call surface the error
    return hint or "qwen3:8b", "no installed models detected — call will likely fail"


def catalog_path(root: Path) -> Path:
    return root / CATALOG_REL


def load_catalog(root: Path) -> dict[str, Any]:
    path = catalog_path(root)
    if not path.exists():
        return {"contract": "capabilityos.catalog.v1", "capabilities": []}
    return json.loads(path.read_text(encoding="utf-8"))


def find_helper(root: Path, helper_id: str) -> dict[str, Any] | None:
    for card in load_catalog(root).get("capabilities", []):
        if card.get("id") == helper_id:
            return card
    return None


def record_observation(root: Path, entry: dict[str, Any]) -> None:
    path = root / OBSERVATIONS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def hashlib_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_evolution_principles(root: Path, helper_id: str) -> str:
    """Distilled principles a helper has self-evolved from VERIFIED past
    outcomes (scripts/aios_self_evolve.py). Non-parametric self-evolution —
    the helper's accumulated 'what good looks like', fed back into its prompt."""
    path = root / ".aios" / "helpers" / "evolution" / f"{helper_id}.principles.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def _strip_think(text: str) -> str:
    """Remove qwen3 reasoning. qwen3:8b emits paired <think>...</think>;
    qwen3:30b-a3b emits reasoning prose then a bare </think> with no opening
    tag. Handle both — keep only what follows the reasoning."""
    import re as _re

    text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL)
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1]
    return text.strip()


def call_local_llm(model: str, prompt: str, *, num_predict: int = 3500) -> tuple[bool, str]:
    # Disable qwen3 reasoning two ways so the answer is not consumed by the
    # thinking budget: the `think: false` API param AND the `/no_think` soft
    # switch in the prompt (reliable across Ollama versions and qwen3 sizes).
    # Helpers are clerks — they answer, not muse.
    effective_prompt = prompt
    if "qwen3" in model.lower():
        effective_prompt = f"{prompt}\n/no_think"
    payload = json.dumps({
        "model": model,
        "prompt": effective_prompt,
        "stream": False,
        "think": False,
        "options": {"num_predict": num_predict},
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return True, _strip_think(str(data.get("response", "")))
    except Exception as exc:  # noqa: BLE001 — surface any runtime/transport error to the caller
        return False, f"local_llm_call_failed: {exc}"


def cmd_list(root: Path, json_mode: bool) -> int:
    cards = load_catalog(root).get("capabilities", [])
    helpers = [c for c in cards if isinstance(c.get("helper"), dict)]
    if json_mode:
        print(json.dumps({"schema": "aios.helper_list.v1", "count": len(helpers),
                          "helpers": helpers}, indent=2, ensure_ascii=False))
    else:
        if not helpers:
            print("no specialist helpers registered")
        for c in helpers:
            h = c["helper"]
            print(f"{c['id']}  [{h.get('model')}]  — {h.get('specialty')}")
    return 0


def cmd_route(root: Path, task: str, json_mode: bool) -> int:
    """Delegate routing to CapabilityOS recommend over the helper catalog."""
    capabilityos = root / "CapabilityOS"
    cat = catalog_path(root)
    proc = subprocess.run(
        [sys.executable, "-m", "capabilityos.cli", "--catalog", str(cat),
         "recommend", "--task", task, "--json"],
        cwd=capabilityos, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        print(f"route failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1
    rec = json.loads(proc.stdout)
    top = rec.get("recommendations", [])
    if json_mode:
        print(json.dumps({"schema": "aios.helper_route.v1", "task": task,
                          "recommendations": top[:3]}, indent=2, ensure_ascii=False))
    else:
        if not top:
            print(f"no helper matched: {task}")
        for r in top[:3]:
            print(f"{r['id']}  score={r.get('score', 0):.1f}  — {r.get('name')}")
    return 0


def cmd_run(root: Path, helper_id: str, raw_input: str, json_mode: bool) -> int:
    card = find_helper(root, helper_id)
    if card is None:
        print(f"error: helper {helper_id!r} not found in {CATALOG_REL}", file=sys.stderr)
        return 2
    helper = card.get("helper")
    if not isinstance(helper, dict) or helper.get("schema") != HELPER_SCHEMA:
        print(f"error: {helper_id!r} is not an {HELPER_SCHEMA} helper", file=sys.stderr)
        return 2

    if raw_input.startswith("@"):
        fpath = Path(raw_input[1:])
        if not fpath.is_absolute():
            fpath = (root / raw_input[1:]).resolve()
        if not fpath.exists():
            print(f"error: input file not found: {fpath}", file=sys.stderr)
            return 2
        text = fpath.read_text(encoding="utf-8")
        input_source = str(fpath)
    else:
        text = raw_input
        input_source = "inline"

    model, model_reason = resolve_model(root, helper)
    role = helper.get("role_prompt", "")
    # self-evolution: prepend the helper's distilled principles (from verified
    # past outcomes only — never raw self-distillation). Non-parametric evolution.
    principles = load_evolution_principles(root, helper_id)
    role_effective = f"{role}\n\n{principles}" if principles else role
    prompt = f"{role_effective}\n\n---\n{text}\n---"
    ok, result = call_local_llm(model, prompt)

    invocation_id = "inv_" + hashlib_sha(f"{helper_id}|{now_iso()}|{text[:80]}")
    record_observation(root, {
        "schema": "aios.helper_observation.v2",
        "invocation_id": invocation_id,
        "helper_id": helper_id,
        "model": model,
        "model_resolution": model_reason,
        "input_excerpt": text[:600],
        "output_excerpt": (result[:1200] if ok else ""),
        "verified": None,
        "evolution_principles_applied": bool(principles),
        "input_source": input_source,
        "input_chars": len(text),
        "ok": ok,
        "ran_at": now_iso(),
    })

    if not ok:
        print(result, file=sys.stderr)
        return 1

    if json_mode:
        print(json.dumps({
            "schema": "aios.helper_result.v1",
            "helper_id": helper_id,
            "invocation_id": invocation_id,
            "model": model,
            "model_resolution": model_reason,
            "specialty": helper.get("specialty"),
            "boundary": "tool_only — this output is a computed proposal, not an accepted record",
            "result": result,
        }, indent=2, ensure_ascii=False))
    else:
        print(result)
    return 0


def cmd_models(root: Path, json_mode: bool) -> int:
    """Show installed models and how each tier + helper resolves against them."""
    available = installed_models()
    tiers_path = root / TIERS_REL
    tiers = {}
    if tiers_path.exists():
        try:
            tiers = json.loads(tiers_path.read_text(encoding="utf-8")).get("tiers", {})
        except (ValueError, OSError):
            pass
    tier_resolution = {}
    for tier_name, spec in tiers.items():
        chosen = next((m for m in spec.get("prefer", []) if m in set(available)), None)
        tier_resolution[tier_name] = chosen or (available[0] if available else None)
    helpers = []
    for c in load_catalog(root).get("capabilities", []):
        h = c.get("helper")
        if isinstance(h, dict):
            model, reason = resolve_model(root, h)
            helpers.append({"id": c["id"], "tier": h.get("tier"), "resolved_model": model, "reason": reason})
    payload = {
        "schema": "aios.helper_models.v1",
        "installed_models": available,
        "tier_resolution": tier_resolution,
        "helpers": helpers,
    }
    if json_mode:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"installed models: {', '.join(available) or '(none — is Ollama running?)'}")
        for t, m in tier_resolution.items():
            print(f"  tier {t:8s} -> {m}")
        for h in helpers:
            print(f"  {h['id']}  (tier {h['tier']}) -> {h['resolved_model']}")
    return 0


def cmd_register(root: Path, args: argparse.Namespace) -> int:
    catalog = load_catalog(root)
    cards = catalog.setdefault("capabilities", [])
    if any(c.get("id") == args.id for c in cards):
        print(f"error: helper {args.id!r} already registered", file=sys.stderr)
        return 2
    card = {
        "id": args.id,
        "name": args.name,
        "kind": "skill",
        "description": args.description,
        "domains": [d.strip() for d in args.domains.split(",") if d.strip()] + ["helper", "specialist"],
        "actions": [a.strip() for a in args.actions.split(",") if a.strip()],
        "inputs": ["text"],
        "outputs": ["text"],
        "risk": "low", "cost": "free", "latency": "medium", "privacy": "local",
        "requires_network": False, "executes_tools": False, "status": "active",
        "confidence": 0.6,
        "evidence_refs": ["docs/schemas/aios_specialist_helper_v1.md"],
        "helper": {
            "schema": HELPER_SCHEMA,
            "tier": args.tier,
            "model": args.model,
            "specialty": args.specialty,
            "role_prompt": args.role_prompt,
            "boundary": "tool_only — computes/proposes, never an authority",
        },
    }
    cards.append(card)
    catalog_path(root).parent.mkdir(parents=True, exist_ok=True)
    catalog_path(root).write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"registered specialist helper {args.id!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS Specialist Helper Layer")
    p.add_argument("--root", default=".", help="AIOS control-plane root")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list registered specialist helpers")
    pl.add_argument("--json", action="store_true")

    pr = sub.add_parser("route", help="ask which helper fits a task")
    pr.add_argument("--task", required=True)
    pr.add_argument("--json", action="store_true")

    rn = sub.add_parser("run", help="invoke a helper")
    rn.add_argument("--helper", required=True)
    rn.add_argument("--input", required=True, help="text, or @path to a file")
    rn.add_argument("--json", action="store_true")

    rg = sub.add_parser("register", help="register a new specialist helper")
    rg.add_argument("--id", required=True)
    rg.add_argument("--name", required=True)
    rg.add_argument("--description", required=True)
    rg.add_argument("--domains", required=True, help="comma-separated task words")
    rg.add_argument("--actions", required=True, help="comma-separated verbs")
    rg.add_argument("--tier", default="default", choices=["fast", "default", "strong"],
                    help="model tier — resolved against installed models at call time")
    rg.add_argument("--model", default="", help="optional explicit model hint (tier is preferred)")
    rg.add_argument("--specialty", required=True)
    rg.add_argument("--role-prompt", dest="role_prompt", required=True)

    pm = sub.add_parser("models", help="show installed models and tier resolution")
    pm.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "list":
        return cmd_list(root, args.json)
    if args.cmd == "route":
        return cmd_route(root, args.task, args.json)
    if args.cmd == "run":
        return cmd_run(root, args.helper, args.input, args.json)
    if args.cmd == "register":
        return cmd_register(root, args)
    if args.cmd == "models":
        return cmd_models(root, args.json)
    return 2


if __name__ == "__main__":
    sys.exit(main())
