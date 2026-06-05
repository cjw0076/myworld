from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aios_goal_sources import resolve_path


HIVE_PRODUCT_EVAL_PATH = "myworld/hivemind/docs/HIVE_PRODUCT_EVALUATION.md"


def concrete_product_eval_candidate(root: Path, base: dict[str, Any]) -> dict[str, Any] | None:
    if base.get("path") != HIVE_PRODUCT_EVAL_PATH:
        return None
    match = first_open_numbered_item(resolve_path(root, HIVE_PRODUCT_EVAL_PATH), "Next Product P0")
    if match is None:
        return None
    index, item = match
    refined = dict(base)
    refined["path"] = f"{HIVE_PRODUCT_EVAL_PATH}#next-product-p0-{index}"
    refined["candidate_task"] = item.rstrip(".")
    refined["goal_score"] = int(base.get("goal_score") or 0) + 50
    refined["policy_reason"] = "refined from Hive product evaluation to first concrete P0"
    refined["alignment_reasons"] = list(base.get("alignment_reasons") or []) + ["concrete_product_eval_p0"]
    refined["source_path"] = base.get("path")
    return refined


def first_open_numbered_item(path: Path, heading: str) -> tuple[int, str] | None:
    if not path.exists():
        return None
    in_section = False
    current_index = 0
    item: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped == f"## {heading}":
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            return open_item(current_index, item)
        if not in_section:
            continue
        match = re.match(r"(\d+)\.\s+(.+)", stripped)
        if match:
            ready = open_item(current_index, item)
            if ready is not None:
                return ready
            current_index = int(match.group(1))
            item = [match.group(2).strip()]
            continue
        if item and stripped:
            item.append(stripped)
    return open_item(current_index, item)


def open_item(index: int, parts: list[str]) -> tuple[int, str] | None:
    if not index or not parts:
        return None
    item = " ".join(parts)
    lower = item.lower()
    if lower.startswith("[closed") or lower.startswith("[x]") or "closed via" in lower:
        return None
    return index, item
