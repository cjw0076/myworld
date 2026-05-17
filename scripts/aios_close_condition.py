#!/usr/bin/env python3
"""Evaluate whether an AIOS contract closeout actually met its criteria."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.close_condition.v1"
CLOSE_TYPES = {
    "closed_goal_met",
    "closed_partial_with_followup",
    "closed_goal_unmet_documented",
}


@dataclass(frozen=True)
class CriterionResult:
    text: str
    status: str
    reason: str

    def to_json(self) -> dict[str, str]:
        return {"text": self.text, "status": self.status, "reason": self.reason}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    current: str | None = None
    for raw in text[4:end].splitlines():
        if not raw.strip():
            continue
        if raw.startswith((" ", "\t")) and current:
            data[current] = f"{data[current]} {raw.strip()}".strip()
            continue
        key, sep, value = raw.partition(":")
        if sep:
            current = key.strip()
            data[current] = value.strip()
    return data, text[end + 5 :]


def contract_id_from(path: Path, frontmatter: dict[str, str]) -> str:
    return frontmatter.get("contract_id") or path.stem.split("-", 1)[0]


def section_after(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bullet_lines(text: str) -> list[str]:
    bullets: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            if current:
                bullets.append(current)
            current = stripped[2:].strip()
        elif current and raw.startswith((" ", "\t")) and stripped:
            current = f"{current} {stripped}"
        elif current and not stripped:
            bullets.append(current)
            current = None
    if current:
        bullets.append(current)
    return bullets


def extract_pass_criteria(body: str) -> list[str]:
    section = section_after(body, "Verification Gate")
    if section:
        criteria_match = re.search(r"^\s*Pass criteria(?:\s*\([^)]*\))?:\s*$", section, flags=re.IGNORECASE | re.MULTILINE)
        if criteria_match:
            return bullet_lines(section[criteria_match.end() :])
    criteria_match = re.search(r"^\s*Pass criteria(?:\s*\([^)]*\))?:\s*$", body, flags=re.IGNORECASE | re.MULTILINE)
    if criteria_match:
        rest = body[criteria_match.end() :]
        next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
        return bullet_lines(rest[: next_heading.start()] if next_heading else rest)
    return []


def run_command(command: str, cwd: Path) -> tuple[bool, str]:
    result = subprocess.run(command, cwd=cwd, shell=True, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return True, "command exited 0"
    summary = (result.stderr or result.stdout).strip().splitlines()
    return False, (summary[-1] if summary else f"command exited {result.returncode}")[:240]


def evaluate_criterion(root: Path, body: str, criterion: str) -> CriterionResult:
    lowered = criterion.lower()
    match = re.search(r"file_exists:([^\s`]+)", criterion)
    if match:
        target = root / match.group(1)
        if target.exists():
            return CriterionResult(criterion, "met", f"file exists: {match.group(1)}")
        return CriterionResult(criterion, "unmet", f"missing file: {match.group(1)}")

    match = re.search(r"must_contain:([^:]+)::(.+)$", criterion)
    if match:
        target = root / match.group(1).strip()
        needle = match.group(2).strip()
        if " — " in needle:
            needle = needle.split(" — ", 1)[0].strip()
        if target.exists() and needle in target.read_text(encoding="utf-8", errors="replace"):
            return CriterionResult(criterion, "met", "required text found")
        return CriterionResult(criterion, "unmet", "required text missing")

    command_match = re.search(r"`([^`]+)`", criterion)
    if command_match and any(token in lowered for token in ("command", "run", "exits 0", "passes")):
        ok, reason = run_command(command_match.group(1), root)
        return CriterionResult(criterion, "met" if ok else "unmet", reason)

    if "retrievable" in lowered and re.search(r"not verified|still needs|still broken|selected=0", body, flags=re.IGNORECASE):
        return CriterionResult(criterion, "unmet", "closeout body contains retrieval-not-verified evidence")

    if ("audit" in lowered or "retrieval rate" in lowered) and re.search(r"retrieval_rate\s*=\s*1\.0|hits=4/4|passed=true", body, flags=re.IGNORECASE):
        return CriterionResult(criterion, "met", "receipt reports passing retrieval audit")

    if "diagnostic json" in lowered and "drop_at_stage" in body:
        return CriterionResult(criterion, "met", "diagnostic field named in contract")

    return CriterionResult(criterion, "manual", "criterion is textual or requires domain-specific review")


def recommended_close_type(results: list[CriterionResult], body: str) -> str:
    if not any(result.status == "unmet" for result in results):
        return "closed_goal_met"
    if re.search(r"follow[- ]?up|partial|still needs|wp-\d+", body, flags=re.IGNORECASE):
        return "closed_partial_with_followup"
    return "closed_goal_unmet_documented"


def evaluate_contract(path: Path, root: Path | None = None) -> dict[str, Any]:
    root = root or path.resolve().parents[2]
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter, body = parse_frontmatter(text)
    criteria = extract_pass_criteria(body)
    results = [evaluate_criterion(root, body, criterion) for criterion in criteria]
    met = sum(1 for result in results if result.status == "met")
    unmet = sum(1 for result in results if result.status == "unmet")
    manual = sum(1 for result in results if result.status == "manual")
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": contract_id_from(path, frontmatter),
        "path": path.as_posix(),
        "status": frontmatter.get("status", "unknown"),
        "criteria": [result.to_json() for result in results],
        "met": met,
        "unmet": unmet,
        "manual": manual,
        "recommended_close_type": recommended_close_type(results, body),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate AIOS contract close conditions")
    parser.add_argument("contract")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    path = Path(args.contract)
    if not path.is_absolute():
        path = root / path
    payload = evaluate_contract(path, root=root)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['contract_id']} close_type={payload['recommended_close_type']} met={payload['met']} unmet={payload['unmet']} manual={payload['manual']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
