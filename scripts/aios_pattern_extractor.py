#!/usr/bin/env python3
"""Extract draft user behavior patterns from AIOS-local activity evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import aios_founder_capture
except ModuleNotFoundError:  # imported as scripts.aios_pattern_extractor in tests
    from scripts import aios_founder_capture  # type: ignore


SCHEMA_VERSION = "aios.user_pattern.v1"
PATTERN_MEMORY_SCHEMA = "aios.user_pattern.memory_drafts.v1"
PRIVATE_MARKERS = ("_from_desktop", "/dain/", "/minyoung/", ".env", "credential", "secret", "token", "api key", "pin")
KOREAN_RE = re.compile(r"[가-힣]")
ENGLISH_RE = re.compile(r"[A-Za-z]")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(*parts: str) -> str:
    return "upat_" + hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def has_private_marker(text: str) -> bool:
    lower = text.lower()
    return any(marker.lower() in lower for marker in PRIVATE_MARKERS)


def safe_text(text: str, *, limit: int = 420) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    cleaned = re.sub(r"AIza[0-9A-Za-z_-]+", "[REDACTED_KEY]", cleaned)
    cleaned = re.sub(r"sk-[A-Za-z0-9_-]+", "[REDACTED_KEY]", cleaned)
    cleaned = re.sub(r"q1q1e3e3", "[REDACTED_PIN]", cleaned, flags=re.IGNORECASE)
    for marker in PRIVATE_MARKERS:
        cleaned = cleaned.replace(marker, "[REDACTED_PATH]")
    return cleaned[:limit].rstrip()


def chat_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    chat_root = root / ".aios" / "chat"
    if not chat_root.exists():
        return rows
    for path in sorted(chat_root.glob("*/messages.jsonl")):
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for index, line in enumerate(lines, start=1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict) and isinstance(row.get("content"), str):
                content = safe_text(row["content"])
                if content and not has_private_marker(content):
                    rows.append({**row, "content": content, "raw_ref": f"{rel}:{index}"})
    return rows


def self_observation_rows(root: Path) -> list[dict[str, Any]]:
    path = root / "docs" / "AIOS_CLAUDE_SELF_OBSERVATION_LOG.md"
    if not path.exists():
        return []
    rows = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for index, line in enumerate(lines, start=1):
        if any(term in line.lower() for term in ("pattern", "founder", "operator", "loop", "monitor", "handoff")):
            content = safe_text(line)
            if content and not has_private_marker(content):
                rows.append({"role": "observation", "content": content, "raw_ref": f"docs/AIOS_CLAUDE_SELF_OBSERVATION_LOG.md:{index}"})
    return rows[:80]


def founder_rows(root: Path) -> list[dict[str, Any]]:
    payload = aios_founder_capture.build_payload(root, aios_founder_capture.default_sources(root))
    rows = []
    for directive in payload.get("directives") or []:
        text = safe_text(str(directive.get("directive_text") or ""))
        refs = directive.get("raw_refs") or []
        if text and refs and not has_private_marker(text):
            rows.append(
                {
                    "role": "founder_directive",
                    "content": text,
                    "reframe_class": directive.get("reframe_class"),
                    "raw_ref": str(refs[0]),
                }
            )
    return rows


def evidence_contains(rows: list[dict[str, Any]], terms: tuple[str, ...], limit: int = 4) -> list[dict[str, str]]:
    evidence = []
    lower_terms = tuple(term.lower() for term in terms)
    for row in rows:
        content = str(row.get("content") or "")
        lower = content.lower()
        if any(term in lower for term in lower_terms):
            evidence.append({"ref": str(row.get("raw_ref")), "quote": safe_text(content, limit=220)})
        if len(evidence) >= limit:
            break
    return evidence


def language_pattern(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    text = "\n".join(str(row.get("content") or "") for row in rows)
    korean = len(KOREAN_RE.findall(text))
    english = len(ENGLISH_RE.findall(text))
    if korean + english == 0:
        return None
    ratio = round(korean / max(1, korean + english), 3)
    if ratio >= 0.12 or korean >= 40:
        content = "Prefer Korean for operator-facing coordination, with English technical identifiers preserved."
    else:
        content = "Prefer concise English unless the operator has used Korean in the active thread."
    return pattern("language_preference", "Language Preference", content, evidence_contains(rows, ("AIOS", "계속", "작업", "진행", "operator")), 0.78)


def pattern(kind: str, title: str, content: str, evidence: list[dict[str, str]], confidence: float) -> dict[str, Any]:
    refs = [item["ref"] for item in evidence if item.get("ref")]
    return {
        "id": stable_id(kind, content, *refs),
        "kind": kind,
        "title": title,
        "content": content,
        "status": "draft",
        "origin": "pattern_extracted",
        "confidence": confidence,
        "evidence_refs": refs,
        "examples": evidence[:2],
    }


def build_patterns(root: Path, user_id: str = "founder") -> dict[str, Any]:
    rows = founder_rows(root) + chat_rows(root) + self_observation_rows(root)
    patterns: list[dict[str, Any]] = []
    lang = language_pattern(rows)
    if lang:
        patterns.append(lang)
    candidates = [
        (
            "control_plane_first",
            "Control Plane First",
            "Route substantial work through AIOS contracts, packets, ledgers, and verification before broad implementation.",
            ("contract", "dispatch", "ledger", "control plane", "작업 지시", "계약"),
            0.86,
        ),
        (
            "continuous_loop",
            "Continuous Loop Bias",
            "Prefer continuing the autonomous loop: monitor, pick the next contract, execute, verify, record, and continue.",
            ("계속", "loop", "monitor", "멈추지", "진행"),
            0.84,
        ),
        (
            "os_role_separation",
            "OS Role Separation",
            "Keep Hive, MemoryOS, CapabilityOS, and GenesisOS in distinct roles instead of collapsing all work into one agent.",
            ("hivemind", "memoryOS", "CapabilityOS", "GenesisOS", "역할", "전문"),
            0.85,
        ),
        (
            "evidence_before_close",
            "Evidence Before Close",
            "Treat tests, receipts, concrete file paths, and monitor/self-check output as required evidence before closing work.",
            ("verify", "검증", "evidence", "receipt", "test", "self_check"),
            0.8,
        ),
        (
            "interface_becomes_aios",
            "AIOS As Interface",
            "Move the user toward one AIOS-facing interface that absorbs provider CLIs behind routing and memory.",
            ("interface", "chat", "CLI", "흡수", "최종 인터페이스"),
            0.78,
        ),
        (
            "discomfort_as_signal",
            "Discomfort As Product Signal",
            "When the operator says a workflow feels wrong, preserve that friction as a design signal instead of only answering literally.",
            ("불편", "friction", "wrong", "감옥", "창의"),
            0.72,
        ),
    ]
    for kind, title, content, terms, confidence in candidates:
        evidence = evidence_contains(rows, terms)
        if evidence:
            patterns.append(pattern(kind, title, content, evidence, confidence))
    if len(patterns) < 5:
        counts = Counter(str(row.get("reframe_class") or row.get("role") or "activity") for row in rows)
        for label, _count in counts.most_common():
            evidence = [row for row in rows if str(row.get("reframe_class") or row.get("role") or "activity") == label][:2]
            converted = [{"ref": str(row.get("raw_ref")), "quote": safe_text(str(row.get("content") or ""), limit=220)} for row in evidence]
            if converted:
                patterns.append(pattern(f"observed_{label}", f"Observed {label.title()} Pattern", f"Preserve observed {label} behavior as draft user-pattern context.", converted, 0.55))
            if len(patterns) >= 5:
                break
    memory_drafts = [
        {
            "type": "user_pattern",
            "origin": "pattern_extracted",
            "status": "draft",
            "project": "AIOS",
            "confidence": item["confidence"],
            "content": f"{item['title']}: {item['content']}",
            "raw_refs": item["evidence_refs"],
        }
        for item in patterns
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "user_id": user_id,
        "generated_at": now_iso(),
        "source_counts": {
            "founder_directives": len([row for row in rows if row.get("role") == "founder_directive"]),
            "chat_messages": len([row for row in rows if row.get("schema_version") == "aios.chat.message.v1"]),
            "self_observations": len([row for row in rows if row.get("role") == "observation"]),
        },
        "patterns": patterns,
        "memory_drafts": {
            "schema_version": PATTERN_MEMORY_SCHEMA,
            "memory_drafts": memory_drafts,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--user", default="founder")
    parser.add_argument("--write", help="write extracted patterns JSON")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    payload = build_patterns(root, args.user)
    if args.write:
        out = root / args.write
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(canonical_json(payload) + "\n", encoding="utf-8")
    if args.json or not args.write:
        print(canonical_json(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
