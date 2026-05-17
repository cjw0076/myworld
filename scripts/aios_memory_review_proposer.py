#!/usr/bin/env python3
"""Build recommendation-only review proposals for MemoryOS draft backlog."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.memory_review_proposals.v1"
ALLOWED_ACTIONS = {"accept", "reject", "needs_more_evidence"}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_memoryos_drafts(root: Path, *, project: str = "", draft_type: str = "", origin: str = "") -> list[dict[str, Any]]:
    memory_root = root / "memoryOS"
    command = [sys.executable, "-m", "memoryos.cli", "--root", memory_root.as_posix(), "drafts", "list", "--json"]
    if project:
        command.extend(["--project", project])
    if draft_type:
        command.extend(["--type", draft_type])
    if origin:
        command.extend(["--origin", origin])
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr or result.stdout)
    payload = json.loads(result.stdout)
    if not isinstance(payload, list):
        raise SystemExit("memoryos drafts list did not return a list")
    return [row for row in payload if isinstance(row, dict)]


def draft_text(row: dict[str, Any]) -> str:
    return " ".join(str(row.get(key, "") or "") for key in ("content", "content_snippet", "title", "summary")).strip()


def bounded(text: str, limit: int = 200) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def propose(row: dict[str, Any]) -> dict[str, Any]:
    content = draft_text(row)
    confidence = float(row.get("confidence", 0.0) or 0.0)
    raw_refs = [str(ref) for ref in (row.get("raw_refs") or [])]
    attrs = row.get("attrs") if isinstance(row.get("attrs"), dict) else {}
    has_provenance = bool(raw_refs or attrs.get("source_refs") or attrs.get("contract_id"))
    lower = content.lower()

    action = "needs_more_evidence"
    rationale = "Needs operator review before memory acceptance."
    if len(content) < 30 or "pending founder go" in lower or 'to "teach' in lower:
        action = "needs_more_evidence"
        rationale = "Content is too terse or noisy for safe acceptance."
    elif confidence >= 0.8 and has_provenance:
        action = "accept"
        rationale = "High-confidence draft with provenance; suitable for operator approval."
    elif confidence < 0.5:
        action = "needs_more_evidence"
        rationale = "Low-confidence draft should not be accepted without more evidence."
    elif has_provenance:
        action = "accept"
        rationale = "Moderate-confidence draft has traceable provenance."

    return {
        "memory_id": row.get("id"),
        "action": action,
        "rationale": bounded(rationale),
        "confidence": confidence,
        "project": row.get("project"),
        "type": row.get("type"),
        "origin": row.get("origin"),
        "captured_at": row.get("captured_at"),
        "content_snippet": bounded(content, 160),
        "raw_refs": raw_refs[:5],
        "operator_command": None
        if action == "needs_more_evidence"
        else f"python -m memoryos.cli --root memoryOS drafts approve {row.get('id')} --reviewer aios-operator --note '<review note>'",
    }


def build_batch(root: Path, rows: list[dict[str, Any]], *, limit: int) -> dict[str, Any]:
    candidates = [row for row in rows if row.get("status", "draft") in {"draft", "reviewed"}]
    candidates.sort(key=lambda row: (str(row.get("captured_at") or ""), str(row.get("id") or "")))
    selected = candidates[:limit] if limit > 0 else candidates
    proposals = [propose(row) for row in selected]
    counts = {action: sum(1 for row in proposals if row["action"] == action) for action in sorted(ALLOWED_ACTIONS)}
    batch_id = "mrev_" + stable_id(now_iso(), ",".join(str(row.get("id")) for row in selected))
    return {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch_id,
        "created_at": now_iso(),
        "recommendation_only": True,
        "auto_apply": False,
        "root": root.as_posix(),
        "input_count": len(rows),
        "selected_count": len(selected),
        "counts": counts,
        "stop_conditions": [
            "operator_review_required",
            "no_auto_accept",
            "no_remote_llm",
        ],
        "proposals": proposals,
    }


def validate_batch(batch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if batch.get("recommendation_only") is not True:
        errors.append("recommendation_only must be true")
    if batch.get("auto_apply") is not False:
        errors.append("auto_apply must be false")
    for index, row in enumerate(batch.get("proposals") or []):
        if row.get("action") not in ALLOWED_ACTIONS:
            errors.append(f"proposals[{index}].action invalid")
        if len(str(row.get("rationale") or "")) > 200:
            errors.append(f"proposals[{index}].rationale too long")
        command = str(row.get("operator_command") or "")
        if "drafts approve" in command and row.get("action") != "accept":
            errors.append(f"proposals[{index}].operator_command mismatches action")
    return errors


def output_path(root: Path, batch_id: str, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        return path if path.is_absolute() else root / path
    return root / ".aios" / "memory_review_proposals" / f"{batch_id}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input-json", type=Path, help="test fixture or preloaded drafts JSON")
    parser.add_argument("--project", default="")
    parser.add_argument("--type", dest="draft_type", default="")
    parser.add_argument("--origin", default="")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    rows = load_json(args.input_json) if args.input_json else run_memoryos_drafts(root, project=args.project, draft_type=args.draft_type, origin=args.origin)
    if not isinstance(rows, list):
        raise SystemExit("--input-json must contain a list")
    batch = build_batch(root, rows, limit=args.limit)
    errors = validate_batch(batch)
    if errors:
        raise SystemExit("; ".join(errors))
    path = output_path(root, batch["batch_id"], args.output)
    if not args.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(batch, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        batch["output_path"] = path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix()
    if args.json:
        print(json.dumps(batch, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"memory_review_proposals batch={batch['batch_id']} selected={batch['selected_count']} counts={batch['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
