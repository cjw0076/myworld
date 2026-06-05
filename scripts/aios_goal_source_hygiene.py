from __future__ import annotations

from pathlib import Path

from aios_goal_sources import parse_frontmatter, resolve_path


PRIVATE_PREFIXES = ("_from_desktop/", "dain/", "minyoung/")
HISTORY_SOURCE_NAMES = {"AGENT_WORKLOG.md", "comms_log.md", "COMPACT_HANDOFF.md"}
INDEX_SOURCE_NAMES = {"VISION_GRAPH.md"}
LEGACY_SURFACE_SOURCE_NAMES = {"TUI_HARNESS.md"}
INDEX_SOURCE_PATHS = {"docs/AIOS_AGENT_LEDGER.md", "docs/contracts/README.md"}
REFERENCE_SOURCE_PATHS = {
    "docs/AIOS_BUILD_METHOD.md",
    "docs/AIOS_DEFINITION.md",
    "docs/AIOS_NORTHSTAR.md",
    "docs/AIOS_SMART_CONTRACT.md",
    "docs/AIOS_WORK_DISPATCH.md",
    "docs/WORKSTREAMS.md",
}


def is_private_path(path: str) -> bool:
    return path.startswith(PRIVATE_PREFIXES) or any(f"/{part}/" in f"/{path}" for part in ("dain", "minyoung"))


def contract_status(path: Path) -> str | None:
    if not path.exists() or not path.name.startswith("ASC-"):
        return None
    frontmatter, _ = parse_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    return frontmatter.get("status")


def is_closed_contract_source(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    return "contracts" in path.parts and contract_status(path) in {"closed", "superseded"}


def is_history_or_index_source(root: Path, raw_path: str) -> str | None:
    path = resolve_path(root, raw_path)
    if path.name in HISTORY_SOURCE_NAMES:
        return "history_source_requires_triage"
    if path.name in INDEX_SOURCE_NAMES:
        return "index_source_requires_triage"
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = raw_path
    if rel in INDEX_SOURCE_PATHS:
        return "index_source_requires_triage"
    if rel in REFERENCE_SOURCE_PATHS:
        return "reference_source_requires_contract"
    return None


def is_provider_transcript_source(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    if not path.exists() or path.suffix != ".md":
        return False
    try:
        head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:80])
    except OSError:
        return False
    lower = head.lower()
    provider_markers = ("chatgpt", "claude", "gemini", "perplexity")
    attachment_markers = ("파일", ".pdf", ".md")
    thinking_markers = ("동안 생각함", "thinking")
    return (
        any(marker in lower for marker in provider_markers)
        and any(marker in head for marker in attachment_markers)
        and any(marker in lower for marker in thinking_markers)
    )


def is_legacy_surface_source(root: Path, raw_path: str) -> bool:
    path = resolve_path(root, raw_path)
    if not path.exists() or path.suffix != ".md":
        return False
    if path.name in LEGACY_SURFACE_SOURCE_NAMES:
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    lower = text.lower()
    legacy_markers = ("retire `hive tui`", "legacy terminal", "legacy composer", "retired legacy")
    return "hive tui" in lower and any(marker in lower for marker in legacy_markers)
