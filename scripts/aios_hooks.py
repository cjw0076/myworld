#!/usr/bin/env python3
"""aios hooks — deterministic enforcement layer for AIOS (ASC-0184).

AIOS has 8 DNA invariants and per-contract scope, but they were honored by
convention — a well-intentioned model still drifts, a prompt-pressured model
can be steered past a guideline. ASC-0122 already named the gap: a policy
specified but not enforced is not binding.

This is Claude Code's hook idea, ported. A *hook* is deterministic code that
inspects a proposed action and returns allow / block / escalate. A `block` is
final regardless of model intent — the action does not happen. The engine is
the mechanism that turns the DNA invariants from documented into enforced.

Built-in hooks (ship enabled):
  - privacy-boundary  (Invariant 7) — fail-CLOSED: any error blocks
  - contract-scope                  — fail-OPEN to escalate, never silent
  - append-only-audit (Invariant 3) — fail-OPEN to escalate

Operator override (Invariant 6): an action carrying an explicit, logged
`operator_override` turns a block into `allow_overridden` — the override
itself is audited.

  aios hooks check --kind write --path <p> [--path <p>] [--contract ASC-NNNN]
  aios hooks list
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Invariant 7 — privacy boundary.
# PRIVACY_SEGMENTS: a path component equal to one of these is gated.
# PRIVACY_SUBSTRINGS: appearing anywhere in the path is gated.
PRIVACY_SEGMENTS = ("dain", "minyoung", "_from_desktop")
PRIVACY_SUBSTRINGS = (".env", "secret", "raw_export", "credentials", "auth.json")

HOOK_LOG = ".aios/hooks/log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --- built-in hooks ---------------------------------------------------------

def hook_privacy_boundary(root: Path, action: dict[str, Any]) -> dict[str, str]:
    """Invariant 7 — block any action touching a privacy-gated path.
    Fail-CLOSED: this hook is the one place an error must block, not allow."""
    for p in action.get("paths", []):
        low = str(p).lower()
        segments = set(re.split(r"[/\\]", low))
        for seg in PRIVACY_SEGMENTS:
            if seg in segments:
                return {"verdict": "block",
                        "reason": f"privacy boundary: path '{p}' has gated segment '{seg}'"}
        for marker in PRIVACY_SUBSTRINGS:
            if marker in low:
                return {"verdict": "block",
                        "reason": f"privacy boundary: path '{p}' matches '{marker}'"}
    return {"verdict": "allow", "reason": "no privacy-gated path"}


def _contract_scope(root: Path, contract_id: str) -> dict[str, list[str]] | None:
    """Parse allowed_files / forbidden_files bullet lists from a contract."""
    matches = sorted((root / "docs" / "contracts").glob(f"{contract_id}-*.md"))
    if not matches:
        return None
    text = matches[0].read_text(encoding="utf-8", errors="replace")
    out: dict[str, list[str]] = {"allowed": [], "forbidden": []}
    section: str | None = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"(allowed_files|forbidden_files)\s*:", s)
        if m:
            section = "allowed" if m.group(1) == "allowed_files" else "forbidden"
            continue
        if section:
            bullet = re.match(r"[-*]\s+`?([^`]+)`?\s*$", s)
            if bullet:
                out[section].append(bullet.group(1).strip())
            elif s and not s.startswith(("-", "*")):
                section = None  # section ended
    return out


def hook_contract_scope(root: Path, action: dict[str, Any]) -> dict[str, str]:
    """Block a write outside the action's contract scope. Fail-OPEN to
    escalate: if the contract or its scope can't be parsed, surface for
    review rather than block the loop or wave it through."""
    cid = action.get("contract_id")
    paths = action.get("paths", [])
    if not cid or not paths:
        return {"verdict": "allow", "reason": "no contract scope to enforce"}
    scope = _contract_scope(root, str(cid))
    if scope is None:
        return {"verdict": "escalate", "reason": f"contract {cid} not found — review"}
    if not scope["allowed"] and not scope["forbidden"]:
        return {"verdict": "escalate",
                "reason": f"contract {cid} declares no file scope — review"}
    for p in paths:
        rp = str(p)
        for fb in scope["forbidden"]:
            if fnmatch.fnmatch(rp, fb) or fnmatch.fnmatch(rp, f"*/{fb}"):
                return {"verdict": "block",
                        "reason": f"path '{rp}' matches forbidden_files '{fb}'"}
        if scope["allowed"]:
            ok = any(fnmatch.fnmatch(rp, a) or fnmatch.fnmatch(rp, f"*/{a}")
                     or rp == a for a in scope["allowed"])
            if not ok:
                return {"verdict": "block",
                        "reason": f"path '{rp}' outside contract {cid} allowed_files"}
    return {"verdict": "allow", "reason": f"within contract {cid} scope"}


def hook_append_only_audit(root: Path, action: dict[str, Any]) -> dict[str, str]:
    """Invariant 3 — block a destructive edit to an audit record: deleting or
    overwriting a ledger file or a closed contract."""
    kind = action.get("kind", "")
    if kind not in ("delete", "overwrite"):
        return {"verdict": "allow", "reason": "not a destructive operation"}
    for p in action.get("paths", []):
        rp = str(p)
        if "AIOS_AGENT_LEDGER" in rp or rp.endswith("LEDGER.md") \
                or "AGENT_WORKLOG" in rp:
            return {"verdict": "block",
                    "reason": f"{kind} of append-only audit file '{rp}' (Invariant 3)"}
        m = re.search(r"(ASC-\d+)-", rp)
        if m:
            matches = sorted((root / "docs" / "contracts").glob(f"{m.group(1)}-*.md"))
            if matches:
                head = matches[0].read_text(encoding="utf-8", errors="replace")[:600]
                if re.search(r"status:\s*closed", head):
                    return {"verdict": "block",
                            "reason": f"{kind} of closed contract '{rp}' (Invariant 3)"}
    return {"verdict": "allow", "reason": "no audit record destroyed"}


BUILTIN_HOOKS: list[tuple[str, bool, Callable[[Path, dict], dict]]] = [
    # (name, fail_closed, fn)
    ("privacy-boundary", True, hook_privacy_boundary),
    ("contract-scope", False, hook_contract_scope),
    ("append-only-audit", False, hook_append_only_audit),
]


# --- engine -----------------------------------------------------------------

def evaluate(root: Path, action: dict[str, Any]) -> dict[str, Any]:
    """Run every hook; block wins, then escalate, then allow. An explicit
    operator_override converts a block into allow_overridden (audited)."""
    results: list[dict[str, str]] = []
    for name, fail_closed, fn in BUILTIN_HOOKS:
        try:
            r = fn(root, action)
        except Exception as exc:  # noqa: BLE001
            r = ({"verdict": "block", "reason": f"hook error (fail-closed): {exc}"}
                 if fail_closed
                 else {"verdict": "escalate", "reason": f"hook error (fail-open): {exc}"})
        results.append({"hook": name, **r})

    verdicts = {r["verdict"] for r in results}
    if "block" in verdicts:
        final = "block"
    elif "escalate" in verdicts:
        final = "escalate"
    else:
        final = "allow"

    override = action.get("operator_override")
    if final == "block" and override and override.get("decision") == "allow":
        final = "allow_overridden"

    decision = {
        "schema": "aios.hooks.decision.v1",
        "evaluated_at": now_iso(),
        "action_kind": action.get("kind"),
        "verdict": final,
        "hook_results": results,
        "blocking": [r for r in results if r["verdict"] == "block"],
        "operator_override": override,
    }
    _log(root, decision)
    return decision


def _log(root: Path, decision: dict[str, Any]) -> None:
    path = root / HOOK_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"at": decision["evaluated_at"], "verdict": decision["verdict"],
                       "kind": decision["action_kind"],
                       "blocking": [b["reason"] for b in decision["blocking"]]},
                      ensure_ascii=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AIOS deterministic enforcement hooks")
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check")
    c.add_argument("--kind", default="write")
    c.add_argument("--path", action="append", default=[], dest="paths")
    c.add_argument("--contract", default="")
    c.add_argument("--override", default="", help="operator override reason")

    sub.add_parser("list")

    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "list":
        out = {"hooks": [{"name": n, "fail_closed": fc} for n, fc, _ in BUILTIN_HOOKS]}
        print(json.dumps(out, indent=2) if args.json else
              "\n".join(f"  {n} (fail_{'closed' if fc else 'open'})"
                        for n, fc, _ in BUILTIN_HOOKS))
        return 0

    action: dict[str, Any] = {"kind": args.kind, "paths": args.paths}
    if args.contract:
        action["contract_id"] = args.contract
    if args.override:
        action["operator_override"] = {"decision": "allow", "reason": args.override}

    decision = evaluate(root, action)
    if args.json:
        print(json.dumps(decision, indent=2, ensure_ascii=False))
    else:
        print(f"verdict: {decision['verdict']}")
        for r in decision["hook_results"]:
            print(f"  [{r['verdict']:18s}] {r['hook']}: {r['reason']}")
    # exit non-zero on block so callers can gate on it
    return 1 if decision["verdict"] == "block" else 0


if __name__ == "__main__":
    sys.exit(main())
