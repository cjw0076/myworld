#!/usr/bin/env python3
"""Repair malformed AIOS dispatch JSONL without deleting raw evidence.

The tool keeps the committed surface privacy-safe: raw malformed line bodies
stay only in local `.aios/state/` quarantine files, never in stdout by default.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_LOG = Path(".aios/state/dispatches.jsonl")


def now_stamp() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S%z")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def scan_jsonl(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    if not path.exists():
        return [], []
    valid_lines: list[str] = []
    malformed: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            json.loads(raw_line)
        except json.JSONDecodeError as exc:
            malformed.append(
                {
                    "line": line_number,
                    "error": exc.msg,
                    "raw": raw_line,
                }
            )
        else:
            valid_lines.append(raw_line)
    return valid_lines, malformed


def write_repair(root: Path, valid_lines: list[str], malformed: list[dict[str, Any]]) -> dict[str, Any]:
    path = root / STATE_LOG
    stamp = now_stamp()
    backup_path = path.with_name(f"{path.name}.backup.{stamp}")
    quarantine_path = path.with_name(f"{path.name}.malformed.{stamp}")
    receipt_path = path.with_name(f"{path.name}.repair.{stamp}.json")

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    backup_path.write_text(original, encoding="utf-8")
    quarantine_path.write_text(
        "\n".join(str(entry["raw"]) for entry in malformed) + ("\n" if malformed else ""),
        encoding="utf-8",
    )
    path.write_text("\n".join(valid_lines) + ("\n" if valid_lines else ""), encoding="utf-8")

    receipt = {
        "schema_version": "aios.dispatch_log_repair.v1",
        "generated_at": now_iso(),
        "path": STATE_LOG.as_posix(),
        "backup_path": backup_path.relative_to(root).as_posix(),
        "quarantine_path": quarantine_path.relative_to(root).as_posix(),
        "valid_lines_preserved": len(valid_lines),
        "malformed_lines_quarantined": len(malformed),
        "malformed": [
            {
                "line": entry["line"],
                "error": entry["error"],
            }
            for entry in malformed
        ],
        "raw_line_policy": "raw malformed line bodies are preserved only in the local quarantine file",
    }
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt["receipt_path"] = receipt_path.relative_to(root).as_posix()
    return receipt


def repair(root: Path, apply: bool) -> dict[str, Any]:
    path = root / STATE_LOG
    valid_lines, malformed = scan_jsonl(path)
    payload: dict[str, Any] = {
        "schema_version": "aios.dispatch_log_repair.preview.v1",
        "generated_at": now_iso(),
        "path": STATE_LOG.as_posix(),
        "exists": path.exists(),
        "apply": apply,
        "valid_lines": len(valid_lines),
        "malformed_lines": len(malformed),
        "malformed": [{"line": entry["line"], "error": entry["error"]} for entry in malformed],
    }
    if apply and malformed:
        payload.update(write_repair(root, valid_lines, malformed))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair malformed .aios/state/dispatches.jsonl safely")
    parser.add_argument("--apply", action="store_true", help="write backup, quarantine, receipt, and repaired log")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args()

    payload = repair(Path.cwd().resolve(), apply=args.apply)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        mode = "applied" if args.apply else "preview"
        print(
            f"{mode}: valid_lines={payload['valid_lines']} "
            f"malformed_lines={payload['malformed_lines']}"
        )
        if payload.get("receipt_path"):
            print(f"receipt={payload['receipt_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
