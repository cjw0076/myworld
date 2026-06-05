from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Goal:
    path: Path
    frontmatter: dict[str, str]
    body: str
    quality_function: list[str]
    anti_cheat_checks: list[str]
    preferred_next: list[str]

    @property
    def goal_id(self) -> str:
        return self.frontmatter.get("goal_id") or self.path.stem

    @property
    def status(self) -> str:
        return self.frontmatter.get("status") or "unknown"

    @property
    def slug(self) -> str:
        return self.frontmatter.get("slug") or self.path.stem


@dataclass(frozen=True)
class RadarRow:
    score: int
    domain: str
    path: str
    signals: dict[str, int]
    candidate_task: str


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    data: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        key, sep, value = raw.partition(":")
        if sep:
            data[key.strip()] = value.strip()
    return data, text[end + 5 :]


def section(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bullet_items(text: str) -> list[str]:
    items: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                items.append(current)
            current = stripped[2:].strip()
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
        elif current:
            items.append(current)
            current = None
    if current:
        items.append(current)
    return items


def load_goal(path: Path) -> Goal:
    if not path.exists():
        raise SystemExit(f"goal file not found: {path}")
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    goal = Goal(
        path=path,
        frontmatter=frontmatter,
        body=body,
        quality_function=bullet_items(section(body, "Quality Function")),
        anti_cheat_checks=bullet_items(section(body, "Anti-Cheat Checks")),
        preferred_next=bullet_items(section(body, "Preferred Next Improvements")),
    )
    if not goal.quality_function:
        raise SystemExit("goal lacks Quality Function bullets")
    return goal


def parse_signal_counts(raw: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in raw.strip().strip("`").split(","):
        key, sep, value = part.partition(":")
        if sep and value.strip().isdigit():
            counts[key.strip()] = int(value.strip())
    return counts


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def parse_radar(path: Path) -> list[RadarRow]:
    if not path.exists():
        return []
    rows: list[RadarRow] = []
    in_table = False
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = split_table_row(line)
        if not cells:
            if in_table and rows:
                break
            continue
        if cells[:5] == ["Score", "Domain", "Path", "Signals", "Candidate Task"]:
            in_table = True
            continue
        if not in_table or cells[0].startswith("---") or len(cells) < 5:
            continue
        if not cells[0].isdigit():
            continue
        rows.append(
            RadarRow(
                score=int(cells[0]),
                domain=cells[1],
                path=cells[2].strip("`"),
                signals=parse_signal_counts(cells[3]),
                candidate_task=cells[4],
            )
        )
    return rows


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    parts = path.parts
    if parts and parts[0] == root.name:
        return root.parent / path
    if parts and parts[0] == "myworld":
        return root.joinpath(*parts[1:])
    return root / path
