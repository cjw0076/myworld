#!/usr/bin/env python3
"""AIOS memory bridge — close the cognition loop.

The kernel (aios_contract_runner) executes governed actions and produces
receipts, but those traces evaporate: the next run starts as ignorant as the
last. This bridge makes the head *grow from its own execution traces* — the
property that lets a composite system's effective intelligence compound even
when the underlying model is frozen (project_aios_kernel_not_workflow,
project_prompt_dependency_and_composite_self).

Two halves:
  writeback(contract) -> emit a draft-first memory of what the run did
  retrieve(goal)      -> recall relevant prior traces before planning

DESIGN CONSTRAINTS
  - DRAFT-FIRST (DNA invariant 2): writeback lands a *reviewable draft*, never
    accepted memory. It uses memoryOS's canonical `drafts import-review-request`
    path (aios.memory_draft_review_request.v1). No auto-accept, ever.
  - CHILD-REPO BOUNDARY: this bridge only *calls* the memoryOS CLI. It never
    edits memoryOS source. memoryOS owns its own ingest.
  - NAMED EXIT (DNA invariant 4): if memoryOS is unavailable, the packet stays
    in a local outbox queue (.aios/runtime/memory_out/) so codex@memoryOS can
    ingest later. The loop still closes via the queue for retrieval.
  - DI runner: the subprocess runner is injected so the bridge is unit-testable
    without a live memoryOS.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# (argv, cwd, timeout) -> (returncode, stdout, stderr)
Runner = Callable[[list[str], str, int], "tuple[int, str, str]"]

REVIEW_SCHEMA = "aios.memory_draft_review_request.v1"


def _real_runner(argv: list[str], cwd: str, timeout: int) -> tuple[int, str, str]:
    try:
        r = subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                           timeout=timeout, check=False)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except OSError as exc:
        return 127, "", str(exc)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _stable(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def _outbox(root: Path) -> Path:
    d = root / ".aios" / "runtime" / "memory_out"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _memoryos_root(root: Path) -> Path | None:
    cand = root / "memoryOS"
    return cand if (cand / "memoryos" / "cli.py").exists() else None


# --- writeback ----------------------------------------------------------------

# Paths that indicate external-product value (outside AIOS internal governance)
_EXTERNAL_PATH_SIGNALS = (
    "/cherry/", "/competitions/", "/uri/", "/dipeen/", "/prizehunter/",
    "/fire/", "/dacon/", "/ablation/",
)
_EXTERNAL_GOAL_KEYWORDS = (
    "공모전", "기획안", "경연", "competition", "contest", "proposal",
    "제출", "캠페인", "외부", "user", "product", "서비스",
)


def _classify_origin_confidence(goal: str, artifacts: list[str]) -> tuple[str, float]:
    """Infer origin + confidence from contract goal and produced artifacts.

    Rules (in priority order):
      1. Artifacts touch external product paths → external_product_value, 0.85
      2. Goal contains external/product keywords → external_product_value, 0.78
      3. Default → aios_contract_runner, 0.60
    """
    all_paths = " ".join(artifacts).lower()
    if any(sig in all_paths for sig in _EXTERNAL_PATH_SIGNALS):
        return "external_product_value", 0.85
    goal_lower = goal.lower()
    if any(kw in goal_lower for kw in _EXTERNAL_GOAL_KEYWORDS):
        return "external_product_value", 0.78
    return "aios_contract_runner", 0.60


def build_review_packet(contract: Any, root: Path) -> tuple[dict[str, Any], Path]:
    """Build a draft-first review-request packet from a closed contract.

    Returns (packet, source_artifact_path). The source artifact is the contract
    closeout JSON written to the local outbox; memoryOS resolves it by absolute
    path. Content summarizes goal + receipts (evidence), never raw secrets.
    """
    ok = [r for r in contract.receipts if r.success]
    artifacts: list[str] = []
    for r in contract.receipts:
        artifacts.extend(a for a in (r.artifacts or []) if not a.endswith(".key"))
    summary_bits = [
        f"AIOS contract {contract.contract_id} ({contract.state}): {contract.goal}.",
        f"{len(ok)}/{len(contract.receipts)} steps succeeded.",
    ]
    for r in ok[:6]:
        summary_bits.append(f"- {r.step_id}: {r.summary}")
    content = " ".join(summary_bits)

    draft_id = _stable("co-draft", contract.contract_id, contract.goal)
    # source artifact = the contract closeout itself (provenance)
    src = _outbox(root) / f"{contract.contract_id}.closeout.json"
    src.write_text(contract.to_json(), encoding="utf-8")

    origin, confidence = _classify_origin_confidence(contract.goal, artifacts)
    packet = {
        "schema_version": REVIEW_SCHEMA,
        "request_id": _stable("mdrev", contract.contract_id),
        "draft_id": draft_id,
        "created_at": _now(),
        "project": "AIOS",
        "source_artifact": str(src.resolve()),  # absolute -> resolver accepts
        "draft": {
            "type": "decision",
            "origin": origin,
            "confidence": confidence,
            "content": content,
            "project": "AIOS",
            "raw_refs": artifacts[:12],
            "provenance": {
                "contract_id": contract.contract_id,
                "state": contract.state,
                "goal": contract.goal,
            },
        },
    }
    return packet, src


def writeback(contract: Any, root: Path, *, runner: Runner = _real_runner,
              reviewer: str = "aios-bridge") -> dict[str, Any]:
    """Emit a draft-first memory of this run. Returns where it landed."""
    if not contract.receipts:
        return {"status": "skipped", "reason": "no receipts to remember"}
    packet, _src = build_review_packet(contract, root)
    packet_path = _outbox(root) / f"{contract.contract_id}.review.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    mroot = _memoryos_root(root)
    if mroot is None:
        return {"status": "queued", "where": str(packet_path),
                "detail": "memoryOS not present; packet queued for later ingest"}
    code, out, err = runner(
        ["python", "-m", "memoryos", "--root", ".", "drafts",
         "import-review-request", str(packet_path.resolve()),
         "--reviewer", reviewer, "--json"],
        str(mroot), 120)
    if code != 0:
        # named exit: leave it queued, don't lose the trace
        return {"status": "queued", "where": str(packet_path),
                "detail": f"memoryOS ingest failed (rc={code}): {err.strip()[:200]}"}
    return {"status": "drafted", "where": str(packet_path),
            "draft_id": packet["draft_id"], "memoryos": out.strip()[:200]}


# --- retrieve -----------------------------------------------------------------

def _queue_snippets(root: Path, goal: str, limit: int) -> list[str]:
    """Fallback retrieval: keyword overlap against locally-queued packets."""
    terms = {w.lower() for w in goal.split() if len(w) > 2}
    hits: list[tuple[int, str]] = []
    for p in sorted(_outbox(root).glob("*.review.json")):
        try:
            pkt = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        content = str(pkt.get("draft", {}).get("content", ""))
        score = sum(1 for t in terms if t in content.lower())
        if score:
            hits.append((score, content))
    hits.sort(key=lambda x: -x[0])
    return [c for _s, c in hits[:limit]]


def retrieve(goal: str, root: Path, *, runner: Runner = _real_runner,
             limit: int = 5) -> list[str]:
    """Recall relevant prior traces for `goal`. memoryOS search first, then the
    local queue. Returns content snippets to inject into the planner."""
    mroot = _memoryos_root(root)
    if mroot is not None:
        code, out, _err = runner(
            ["python", "-m", "memoryos", "--root", ".", "search", goal,
             "--limit", str(limit), "--json"],
            str(mroot), 120)
        if code == 0 and out.strip():
            try:
                data = json.loads(out)
                rows = data.get("results") or data.get("objects") or data.get("matches") or []
                snippets = []
                for row in rows[:limit]:
                    if isinstance(row, dict):
                        text = row.get("content") or row.get("summary") or row.get("text")
                        if text:
                            snippets.append(str(text))
                if snippets:
                    return snippets
            except json.JSONDecodeError:
                pass
    # fallback: local queue
    return _queue_snippets(root, goal, limit)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="AIOS memory bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("retrieve")
    r.add_argument("goal")
    r.add_argument("--root", default=".")
    args = ap.parse_args()
    if args.cmd == "retrieve":
        print(json.dumps(retrieve(args.goal, Path(args.root).resolve()),
                         ensure_ascii=False, indent=2))
