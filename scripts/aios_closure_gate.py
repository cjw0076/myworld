#!/usr/bin/env python3
"""ASC-0213 — Closure Quality Gate.

Mandatory pre-closure audit. Combines:
- `aios_convergence_audit.py` (challenge vs footprint scores)
- `aios_boundary_probe.py` (GenesisOS critic prison signatures +
  cross-domain probes)

Verdict (advisory, never auto-block):
- `pass`  : real_challenge verdict, 0 prison signatures
- `warn`  : mixed verdict OR 1-2 prison signatures (closure allowed)
- `block` : footprint_consensus verdict OR 3+ prison signatures
            (closure blocked unless contract frontmatter contains
             `closure_gate_override: <reason>`)

Output: `aios.closure_gate.v1`. Exit code 0 = pass/warn, 1 = block.

Peer override: a contract whose frontmatter declares
`closure_gate_override: <reason>` is *never* blocked. Per
[[feedback_hiding_is_peer_agency]] — gate suggests, peers decide.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read_frontmatter(contract_path: Path) -> dict[str, str]:
    text = contract_path.read_text(encoding="utf-8", errors="replace")
    fm: dict[str, str] = {}
    if not text.startswith("---"):
        return fm
    parts = text.split("---", 2)
    if len(parts) < 3:
        return fm
    cur_key = None
    cur_lines: list[str] = []
    for line in parts[1].splitlines():
        m = re.match(r"^([a-zA-Z_][\w_]*):\s*(.*)$", line)
        if m:
            if cur_key is not None:
                fm[cur_key] = "\n".join(cur_lines).strip()
            cur_key = m.group(1)
            cur_lines = [m.group(2)]
        else:
            cur_lines.append(line)
    if cur_key is not None:
        fm[cur_key] = "\n".join(cur_lines).strip()
    return fm


def run_convergence_audit(contract_path: Path) -> dict[str, Any]:
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "aios_convergence_audit.py"),
         str(contract_path), "--json"],
        capture_output=True, text=True, check=False,
        cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:500]}
    return json.loads(r.stdout)


def run_boundary_probe(contract_path: Path) -> dict[str, Any]:
    r = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "aios_boundary_probe.py"),
         "--target", str(contract_path),
         "--cross-domain-n", "0",  # only prison signatures, no domain probes
         "--dry-run", "--json"],
        capture_output=True, text=True, check=False,
        cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        return {"error": r.stderr.strip()[:500]}
    return json.loads(r.stdout)


def evaluate(contract_path: Path) -> dict[str, Any]:
    fm = _read_frontmatter(contract_path)
    override_reason = fm.get("closure_gate_override", "").strip()

    audit = run_convergence_audit(contract_path)
    audit_row = (audit.get("rows") or [{}])[0]
    audit_verdict = audit_row.get("verdict", "indeterminate")
    challenge_score = audit_row.get("challenge_score", 0)
    footprint_score = audit_row.get("footprint_score", 0)

    probe = run_boundary_probe(contract_path)
    prison_drafts = [d for d in (probe.get("drafts") or [])
                     if (d.get("draft", {}).get("provenance", {}) or {}).get("kind") == "prison_signature"]
    prison_count = len(prison_drafts)
    prison_signatures = [
        (d.get("draft", {}).get("provenance", {}) or {}).get("signature", "")
        for d in prison_drafts
    ]

    # Verdict logic
    if audit_verdict == "footprint_consensus" or prison_count >= 3:
        verdict = "block"
    elif audit_verdict == "real_challenge" and prison_count == 0:
        verdict = "pass"
    else:
        verdict = "warn"

    overridden = bool(override_reason)
    if verdict == "block" and overridden:
        effective = "pass_with_override"
    else:
        effective = verdict

    return {
        "schema_version": "aios.closure_gate.v1",
        "contract": fm.get("contract_id") or contract_path.stem,
        "contract_path": str(contract_path),
        "audit_verdict": audit_verdict,
        "challenge_score": challenge_score,
        "footprint_score": footprint_score,
        "prison_count": prison_count,
        "prison_signatures": prison_signatures,
        "verdict": verdict,
        "effective": effective,
        "override_reason": override_reason or None,
        "rationale": {
            "pass": "real_challenge verdict and 0 prison signatures",
            "warn": "mixed verdict or 1-2 prison signatures — closure allowed; peer should still skim",
            "block": "footprint_consensus or 3+ prison signatures — frame likely a trap; reframe or override",
            "pass_with_override": "would block, but contract frontmatter declares closure_gate_override",
        }[effective],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ASC-0213 closure quality gate")
    p.add_argument("contract", type=Path,
                   help="contract markdown path")
    p.add_argument("--json", action="store_true")
    p.add_argument("--allow-block", action="store_true",
                   help="even when verdict=block (and no override), exit 0 — for diagnostic-only use")
    args = p.parse_args(argv)

    result = evaluate(args.contract)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"{result['contract']}: {result['effective']}")
        print(f"  audit_verdict={result['audit_verdict']} ch={result['challenge_score']} fp={result['footprint_score']}")
        print(f"  prison_signatures={result['prison_signatures']} (count={result['prison_count']})")
        if result["override_reason"]:
            print(f"  override: {result['override_reason']}")
        print(f"  rationale: {result['rationale']}")

    if result["effective"] == "block" and not args.allow_block:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
