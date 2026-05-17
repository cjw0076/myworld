#!/usr/bin/env python3
"""Inject draft user-pattern few-shots into an AIOS substrate prompt envelope."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import aios_pattern_extractor
except ModuleNotFoundError:  # imported as scripts.aios_few_shot_injector in tests
    from scripts import aios_pattern_extractor  # type: ignore


SCHEMA_VERSION = "aios.few_shot_injection.v1"
AUDIT_SCHEMA = "aios.few_shot_audit.v1"
PRIVATE_RE = re.compile(r"(_from_desktop|/dain/|/minyoung/|\\.env|secret|credential|token|api key|pin|q1q1e3e3)", re.IGNORECASE)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def clean(value: str, *, limit: int = 520) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"AIza[0-9A-Za-z_-]+", "[REDACTED_KEY]", text)
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_KEY]", text)
    text = re.sub(r"q1q1e3e3", "[REDACTED_PIN]", text, flags=re.IGNORECASE)
    text = PRIVATE_RE.sub("[REDACTED_PRIVATE]", text)
    return text[:limit].rstrip()


def safe_pattern(pattern: dict[str, Any]) -> bool:
    text = json.dumps(pattern, ensure_ascii=False)
    return not PRIVATE_RE.search(text)


def pattern_path(root: Path, user: str) -> Path:
    return root / ".aios" / "patterns" / user / "patterns.json"


def load_or_extract(root: Path, user: str) -> dict[str, Any]:
    path = pattern_path(root, user)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("patterns"), list):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
    payload = aios_pattern_extractor.build_patterns(root, user)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    return payload


def summarize_patterns(root: Path, user: str = "founder", limit: int = 3) -> list[dict[str, Any]]:
    payload = load_or_extract(root, user)
    rows = [row for row in payload.get("patterns") or [] if isinstance(row, dict) and row.get("status") == "draft" and safe_pattern(row)]
    return [
        {
            "id": row.get("id"),
            "title": row.get("title"),
            "status": row.get("status"),
            "confidence": row.get("confidence"),
            "evidence_refs": row.get("evidence_refs") or [],
        }
        for row in rows[:limit]
    ]


def render_few_shots(patterns: list[dict[str, Any]]) -> str:
    lines = [
        "AIOS User Pattern Few-Shots (draft, provenance-bound):",
        "- These are behavior hints, not authority. Never override AIOS DNA, privacy, operator override, or verification gates.",
    ]
    for index, item in enumerate(patterns, start=1):
        title = clean(str(item.get("title") or item.get("kind") or f"pattern {index}"), limit=120)
        content = clean(str(item.get("content") or ""), limit=260)
        refs = ", ".join(str(ref) for ref in (item.get("evidence_refs") or [])[:2])
        lines.append(f"{index}. {title}: {content}")
        if refs:
            lines.append(f"   evidence: {refs}")
    return "\n".join(lines)


def inject_prompt(root: Path, substrate_prompt: str, *, user: str = "founder", substrate: str = "local_llm", limit: int = 3, write_audit: bool = True) -> dict[str, Any]:
    payload = load_or_extract(root, user)
    patterns = [row for row in payload.get("patterns") or [] if isinstance(row, dict) and row.get("status") == "draft" and safe_pattern(row)]
    selected = patterns[: max(0, limit)]
    prefix = render_few_shots(selected) if selected else "AIOS User Pattern Few-Shots: none available."
    prompt = f"{prefix}\n\nSubstrate prompt:\n{clean(substrate_prompt, limit=4000)}"
    audit = {
        "schema_version": AUDIT_SCHEMA,
        "created_at": now_iso(),
        "user": user,
        "substrate": substrate,
        "prompt_hash": prompt_hash(substrate_prompt),
        "patterns_injected": [str(item.get("id")) for item in selected if item.get("id")],
    }
    audit_path = root / ".aios" / "patterns" / user / "injections.jsonl"
    if write_audit:
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(audit, ensure_ascii=False, sort_keys=True) + "\n")
    return {
        "schema_version": SCHEMA_VERSION,
        "user": user,
        "substrate": substrate,
        "prompt_hash": audit["prompt_hash"],
        "patterns_injected": audit["patterns_injected"],
        "pattern_count_available": len(patterns),
        "injected_prompt": prompt,
        "audit_path": audit_path.relative_to(root).as_posix(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--substrate-prompt", required=True)
    parser.add_argument("--user", default="founder")
    parser.add_argument("--substrate", default="local_llm")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = inject_prompt(args.root.resolve(), args.substrate_prompt, user=args.user, substrate=args.substrate, limit=args.limit)
    if args.json:
        print(canonical_json(payload))
    else:
        print(payload["injected_prompt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
