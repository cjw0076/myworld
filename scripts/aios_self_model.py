#!/usr/bin/env python3
"""aios self-model — AIOS's structured representation of itself (자기인식 구조).

Founder thesis (2026-05-17): AIOS should not just do one task and stop — it
should have "a self-awareness structure" (자기인식 구조). An agent that knows
the user, the device, and the web well, and works deeply and long, needs a
model of *itself* to reason with.

AIOS already measures fragments of itself — readiness, sovereignty, the
completion check, the device profile — but never composes them into one
queryable self-representation. The 2026-05-17 internal audit was a one-off,
human-driven version of this. This organ makes it standing and queryable.

It does NOT duplicate the scorers (CapabilityOS route confirmed: build on
the readiness scorer, do not re-implement). It composes them, adds AIOS's
fixed identity (the five OS and their roles), and synthesizes a plain-language
self-assessment — the answer to "what am I, in what condition, missing what."

  aios self-model build      compose and print the self-model
  aios self-model build --json

Read-only: it aggregates other organs' output. It changes no state.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# AIOS's fixed identity — the five OS and their solidified one-line roles
# (canonical, per docs/AIOS_INTERNAL_STATE_AUDIT_2026-05-17.md).
IDENTITY = {
    "what": "AIOS — a local-first agent operating layer that wraps provider "
            "agent CLIs in symbiosis (it does not compete with them) and is "
            "spreading from single-model-multifunction toward "
            "multi-model-multifunction on local LLMs.",
    "os": {
        "myworld": "the control plane — contracts, dispatch, the deterministic "
                   "kernel, the always-on autopoietic loop.",
        "hivemind": "the execution layer — a local-first blackboard harness "
                    "that turns 'run an agent' into a contracted, verifiable, "
                    "replayable run.",
        "memoryOS": "the memory substrate — an append-only, provenance-stamped "
                    "graph that turns every conversation and outcome into "
                    "retrievable, reviewed memory.",
        "CapabilityOS": "the capability map — a recommendation-only catalog "
                        "that ranks which capability fits a task and observes "
                        "what worked.",
        "GenesisOS": "the divergence layer — forces reasoning to be re-framed "
                     "across fixed axes and borrows across domains.",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _run_json(root: Path, script: str, args: list[str], timeout: int = 90) -> dict[str, Any]:
    """Run a self-measurement organ and parse its JSON; never raise."""
    path = root / "scripts" / script
    if not path.exists():
        return {"_error": f"{script} not present"}
    try:
        proc = subprocess.run([sys.executable, path.as_posix(), *args, "--json"],
                              cwd=root, capture_output=True, text=True, timeout=timeout)
        return json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
        return {"_error": f"{script}: {type(exc).__name__}"}


def build_self_model(root: Path) -> dict[str, Any]:
    readiness = _run_json(root, "aios_readiness.py", [])
    sovereignty = _run_json(root, "aios_sovereignty.py", [])
    completion = _run_json(root, "aios_completion.py", ["--root", root.as_posix()])
    device = _run_json(root, "aios_device_profile.py", ["--root", root.as_posix(), "recommend"])

    condition = {
        "readiness_level": readiness.get("level"),
        "readiness_name": readiness.get("level_name"),
        "ready": readiness.get("ready"),
        "sovereignty_verdict": sovereignty.get("verdict"),
        "hard_dependency_readiness": sovereignty.get("hard_dependency_readiness"),
        "completion_verdict": completion.get("verdict"),
        "self_maintaining": completion.get("self_maintaining"),
        "device_profile": device.get("profile"),
        "dream_phase1": device.get("dream_phase1_embed"),
        "dream_phase2": device.get("dream_phase2_adapter"),
    }

    # gaps — composed from the readiness scorer and the device profile notes.
    # Scorer gaps can embed long evidence dumps (full contract lists); keep
    # only the headline clause so the self-model stays legible.
    def _clean(text: str) -> str:
        s = str(text)
        for cut in (" closed=[", " pending=[", "; closed", ", closed"):
            idx = s.find(cut)
            if idx != -1:
                s = s[:idx]
        return s.strip().rstrip(",;") + ("…" if len(str(text)) > len(s) + 2 else "")

    gaps: list[str] = []
    for g in readiness.get("gaps", []) or []:
        gaps.append(_clean(g))
    for n in device.get("notes", []) or []:
        if "runs the full" not in n:
            gaps.append(f"device: {n}")

    # plain-language self-assessment — the answer the founder asked for
    assessment = (
        f"I am AIOS on a {condition['device_profile']}-class host. "
        f"My readiness is {condition['readiness_name'] or 'unknown'} "
        f"(level {condition['readiness_level']}); my completion verdict is "
        f"\"{condition['completion_verdict']}\"; sovereignty: "
        f"{condition['sovereignty_verdict']}. "
        f"My autopoietic loop runs and dream phase 1 (memory consolidation) is "
        f"{'on' if condition['dream_phase1'] else 'off'}; "
        f"parametric dream phase 2 is '{condition['dream_phase2']}'. "
        + (f"I have {len(gaps)} known open gap(s)." if gaps
           else "I have no scorer-reported open gaps.")
    )

    return {
        "schema": "aios.self_model.v1",
        "generated_at": now_iso(),
        "identity": IDENTITY,
        "condition": condition,
        "open_gaps": gaps,
        "self_assessment": assessment,
        "sources": ["aios_readiness", "aios_sovereignty", "aios_completion",
                    "aios_device_profile"],
        "boundary": "read-only composition — this organ measures AIOS, it "
                    "changes no state; the operator and the dream cycle consult it",
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS self-model — 자기인식 구조")
    p.add_argument("--root", default=".")
    p.add_argument("action", nargs="?", default="build", choices=["build"])
    p.add_argument("--json", action="store_true")
    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    model = build_self_model(root)
    if args.json:
        print(json.dumps(model, indent=2, ensure_ascii=False))
        return 0

    print("AIOS self-model")
    print(f"  {model['identity']['what']}")
    print("  five OS:")
    for name, role in model["identity"]["os"].items():
        print(f"    - {name}: {role}")
    print("  condition:")
    for k, v in model["condition"].items():
        print(f"    {k}: {v}")
    if model["open_gaps"]:
        print(f"  open gaps ({len(model['open_gaps'])}):")
        for g in model["open_gaps"][:12]:
            print(f"    - {g}")
    print(f"  self-assessment: {model['self_assessment']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
