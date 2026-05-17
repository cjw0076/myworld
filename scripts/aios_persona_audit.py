#!/usr/bin/env python3
"""Advisory audit for AIOS 5-persona cognitive architecture usage."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.persona_audit.v1"
PERSONA_KEYS = (
    "wrapper_score",
    "retriever_score",
    "router_score",
    "philosophy_score",
    "sovereign_score",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data, text[end + 5 :]


def contract_number(path: Path) -> int:
    match = re.search(r"ASC-(\d+)", path.name)
    return int(match.group(1)) if match else -1


def closed_contracts(root: Path, window: int) -> list[tuple[Path, dict[str, str], str]]:
    rows: list[tuple[Path, dict[str, str], str]] = []
    for path in sorted((root / "docs" / "contracts").glob("ASC-*.md"), key=contract_number):
        fm, body = parse_frontmatter(path)
        if fm.get("status") == "closed":
            rows.append((path, fm, body))
    return rows[-window:] if window > 0 else rows


def mentions(text: str, *terms: str) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def provider_mentions(text: str) -> set[str]:
    lower = text.lower()
    providers = {"claude", "codex", "gemini", "ollama", "local llm", "local-llm", "local"}
    return {provider for provider in providers if provider in lower}


def score_contract(path: Path, frontmatter: dict[str, str], body: str, root: Path) -> dict[str, Any]:
    text = f"{frontmatter}\n{body}"
    lower = text.lower()
    providers = provider_mentions(text)
    wrapper = len(providers) >= 2 or mentions(lower, "single-provider", "single provider justified")
    retriever = bool(re.search(r"rtrace_[a-z0-9]+", text)) and bool(
        re.search(r"signal_coverage\s*(=|>|:)\s*(0\.[1-9]|1\.0|1|positive)", lower)
    )
    router = mentions(lower, "capabilityos") and mentions(lower, "recommend", "route", "routing") and mentions(
        lower, "top route", "deviation", "follow", "fallback"
    )
    philosophy = mentions(lower, "genesisos", "genesis") and mentions(lower, "critic", "branches", "alternatives", "escape vector")
    acceptance = frontmatter.get("acceptance_authority", "") + " " + frontmatter.get("accepted", "")
    operator_pair = mentions(acceptance, "operator", "claude@myworld", "codex@myworld", "founder")
    vision_keywords = mentions(lower, "sovereign", "founder", "dna", "living organism", "government", "cognitive architecture")
    founder_gate = mentions(lower, "founder", "human_approved: true", "human approved", "operator override")
    sovereign = operator_pair and (not vision_keywords or founder_gate)
    scores = {
        "wrapper_score": 1.0 if wrapper else 0.0,
        "retriever_score": 1.0 if retriever else 0.0,
        "router_score": 1.0 if router else 0.0,
        "philosophy_score": 1.0 if philosophy else 0.0,
        "sovereign_score": 1.0 if sovereign else 0.0,
    }
    return {
        "contract_id": frontmatter.get("contract_id") or path.stem.split("-", 1)[0],
        "path": path.relative_to(root).as_posix(),
        "signals": {
            "providers": sorted(providers),
            "rtrace": bool(re.search(r"rtrace_[a-z0-9]+", text)),
            "capability_route": router,
            "genesis_philosophy": philosophy,
            "operator_pair": operator_pair,
            "vision_keywords": vision_keywords,
            "founder_gate": founder_gate,
        },
        "scores": scores,
    }


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def build_report(root: Path, *, window: int = 20) -> dict[str, Any]:
    root = root.resolve()
    rows = [score_contract(path, fm, body, root) for path, fm, body in closed_contracts(root, window)]
    scores = {
        key: mean([float(row["scores"][key]) for row in rows])
        for key in PERSONA_KEYS
    }
    scores["persona_composite"] = mean([scores[key] for key in PERSONA_KEYS])
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "authority": "advisory_only",
        "window": window,
        "contracts_scored": len(rows),
        "scores": scores,
        "per_contract": rows,
        "relationship_to_governance_axis": "orthogonal_advisory_axis",
    }


def require_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    def has_key(value: Any, key: str) -> bool:
        if isinstance(value, dict):
            if key in value:
                return True
            return any(has_key(child, key) for child in value.values())
        if isinstance(value, list):
            return any(has_key(child, key) for child in value)
        return False

    return [key for key in keys if not has_key(payload, key)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--window", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--assert-keys", default="", help="comma-separated keys that must appear in JSON output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = build_report(Path(args.root), window=args.window)
    missing = require_keys(payload, [key.strip() for key in args.assert_keys.split(",") if key.strip()])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        scores = payload["scores"]
        print(f"persona_composite={scores['persona_composite']} contracts={payload['contracts_scored']}")
    if missing:
        print(f"missing required keys: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
