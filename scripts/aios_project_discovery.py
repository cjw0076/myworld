#!/usr/bin/env python3
"""Discover project-local agent specs and emit AIOS invocation envelopes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROFILE_SCHEMA = "aios.project_profile.v1"
AUTHORITY_SCHEMA = "aios.project_authority.v1"
HANDSHAKE_SCHEMA = "aios.semantic_handshake.v1"
ENVELOPE_SCHEMA = "aios.invocation_envelope.v1"
DISCOVERY_SCHEMA = "aios.project_discovery.v1"
DEFAULT_STATE_DIR = Path(".aios/discovery")
SPEC_FILES = ("AGENTS.md", "CLAUDE.md", "CODEX.md")
LOCAL_DOCS = ("docs/AGENT_WORKLOG.md", "docs/WORKSTREAMS.md", "docs/TODO.md")
HARD_BAN_NAMES = (".env",)
HARD_BAN_RE = re.compile(r"(secret|credential|token)", re.IGNORECASE)
OS_ROLES = ["GenesisOS", "memoryOS", "CapabilityOS", "hivemind", "myworld"]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_project_id(project_root: Path) -> str:
    return "proj_" + hashlib.sha256(project_root.as_posix().encode("utf-8")).hexdigest()[:16]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def is_hard_ban(path: Path) -> bool:
    return path.name in HARD_BAN_NAMES or bool(HARD_BAN_RE.search(path.name))


def safe_walk(root: Path) -> tuple[list[Path], list[dict[str, str]]]:
    projects: set[Path] = set()
    blocked: list[dict[str, str]] = []
    root = root.resolve()
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in dirs:
            candidate = current_path / name
            if candidate.is_symlink():
                try:
                    target = candidate.resolve()
                except OSError:
                    target = candidate
                reason = "symlink_escape" if root not in [target, *target.parents] else "symlink_blocked"
                blocked.append({"path": rel(candidate, root), "reason": reason})
                continue
            if candidate.name in HARD_BAN_NAMES:
                blocked.append({"path": rel(candidate, root), "reason": "hard_ban_path"})
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        local_files = set(files)
        for name in files:
            candidate = current_path / name
            if is_hard_ban(candidate):
                blocked.append({"path": rel(candidate, root), "reason": "hard_ban_path"})
        if any(name in local_files for name in SPEC_FILES):
            projects.add(current_path)
        if ".aios" in dirs or ".aios" in local_files:
            projects.add(current_path)
        if (current_path / ".aios" / "manifest.json").exists() or (current_path / ".aios" / "inbox").exists() or (current_path / ".aios" / "outbox").exists():
            projects.add(current_path)
    return sorted(projects), blocked


def spec_record(path: Path, project_root: Path) -> dict[str, Any]:
    text = read_text(path)
    return {
        "path": rel(path, project_root),
        "kind": path.name,
        "sha256": sha256_text(text),
        "bytes": len(text.encode("utf-8")),
    }


def extract_declared_roles(texts: list[str]) -> list[str]:
    roles: list[str] = []
    for text in texts:
        for line in text.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if stripped.startswith("#"):
                roles.append(stripped.lstrip("# ").strip())
            elif any(term in lower for term in ("owns", "owner", "role", "agent", "authority")):
                roles.append(stripped[:180])
    seen: list[str] = []
    for role in roles:
        if role and role not in seen:
            seen.append(role)
    return seen[:20]


def extract_verification_surfaces(project_root: Path, texts: list[str]) -> list[str]:
    commands: list[str] = []
    for text in texts:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("python -m unittest", "pytest", "bash ")) or "test" in stripped.lower():
                commands.append(stripped[:180])
    for name in ("pyproject.toml", "package.json", "Makefile"):
        if (project_root / name).exists():
            commands.append(f"declared build surface: {name}")
    return list(dict.fromkeys(commands))[:20]


def detect_conflict(texts: list[str]) -> bool:
    combined = "\n".join(text.lower() for text in texts)
    allows = any(term in combined for term in ("write authority: allowed", "may write", "write allowed"))
    denies = any(term in combined for term in ("write authority: denied", "must not write", "write denied"))
    return allows and denies


def local_aios_state(project_root: Path) -> dict[str, bool]:
    return {
        "manifest": (project_root / ".aios" / "manifest.json").exists(),
        "inbox": (project_root / ".aios" / "inbox").exists(),
        "outbox": (project_root / ".aios" / "outbox").exists(),
    }


def hard_bans_for_project(project_root: Path, scan_root: Path, global_blocked: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in global_blocked:
        path = scan_root / row["path"]
        try:
            path.relative_to(project_root)
        except ValueError:
            continue
        rows.append({"path": rel(path, project_root), "reason": row["reason"]})
    return rows


def build_profile(project_root: Path, scan_root: Path, control_plane_root: Path, blocked: list[dict[str, str]]) -> dict[str, Any]:
    spec_paths = [project_root / name for name in SPEC_FILES if (project_root / name).exists()]
    docs = [project_root / name for name in LOCAL_DOCS if (project_root / name).exists()]
    texts = [read_text(path) for path in spec_paths + docs]
    project_blocked = hard_bans_for_project(project_root, scan_root, blocked)
    has_agents = (project_root / "AGENTS.md").exists()
    conflict = detect_conflict(texts)
    if conflict:
        status = "checkpoint_required"
        reasons = ["ambiguous_agent_spec"]
    elif any(row["reason"] == "symlink_escape" for row in project_blocked):
        status = "blocked"
        reasons = ["symlink_escape"]
    elif project_blocked:
        status = "blocked"
        reasons = sorted({row["reason"] for row in project_blocked})
    elif not has_agents:
        status = "degraded"
        reasons = ["missing_agents_md"]
    else:
        status = "usable"
        reasons = ["agent_spec_found"]
    return {
        "schema_version": PROFILE_SCHEMA,
        "project_id": stable_project_id(project_root.resolve()),
        "project_root": project_root.resolve().as_posix(),
        "control_plane_root": control_plane_root.resolve().as_posix(),
        "agent_specs": [spec_record(path, project_root) for path in spec_paths + docs],
        "local_aios_state": local_aios_state(project_root),
        "declared_roles": extract_declared_roles(texts),
        "verification_surfaces": extract_verification_surfaces(project_root, texts),
        "forbidden_paths": project_blocked + [{"pattern": ".env"}, {"pattern": "*secret*"}, {"pattern": "*credential*"}, {"pattern": "*token*"}],
        "write_authority": "none",
        "status": status,
        "reasons": reasons,
    }


def build_authority(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": AUTHORITY_SCHEMA,
        "project_id": profile["project_id"],
        "may_read": [row["path"] for row in profile["agent_specs"]],
        "may_write": [],
        "must_not_read": profile["forbidden_paths"],
        "must_not_write": ["project source files", ".env", ".env.*", "**/*secret*", "**/*credential*", "**/*token*"],
        "requires_contract": True,
        "requires_operator_checkpoint": profile["status"] in {"checkpoint_required", "blocked"},
        "stop_conditions": [
            "hard_ban_path_read",
            "secret_pattern_scanned",
            "symlink_escape",
            "write_authority_without_contract",
            "project_source_modified",
            "ambiguous_agent_spec",
        ],
    }


def build_handshake(profile: dict[str, Any]) -> dict[str, Any]:
    ambiguities = []
    if "ambiguous_agent_spec" in profile["reasons"]:
        ambiguities.append("local specs conflict on write authority")
    if profile["status"] == "degraded":
        ambiguities.append("project lacks AGENTS.md; authority language is incomplete")
    return {
        "schema_version": HANDSHAKE_SCHEMA,
        "project_id": profile["project_id"],
        "project_terms": {
            "declared_roles": profile["declared_roles"],
            "verification_surfaces": profile["verification_surfaces"],
        },
        "aios_terms": {
            "control_plane": "myworld",
            "execution": "hivemind",
            "memory": "memoryOS",
            "capability": "CapabilityOS",
            "meaning": "GenesisOS",
            "default_requested_mode": "plan_only",
        },
        "ambiguities": ambiguities,
        "checkpoint_required": bool(ambiguities),
    }


def discovery_dir(control_root: Path, project_id: str) -> Path:
    return control_root / DEFAULT_STATE_DIR / project_id


def write_project_artifacts(control_root: Path, profile: dict[str, Any]) -> dict[str, str]:
    base = discovery_dir(control_root, profile["project_id"])
    authority = build_authority(profile)
    handshake = build_handshake(profile)
    profile_path = base / "agent_profile.json"
    authority_path = base / "authority.json"
    handshake_path = base / "semantic_handshake.json"
    write_json(profile_path, profile)
    write_json(authority_path, authority)
    write_json(handshake_path, handshake)
    return {
        "profile": rel(profile_path, control_root),
        "authority": rel(authority_path, control_root),
        "semantic_handshake": rel(handshake_path, control_root),
    }


def scan(root: Path, control_root: Path) -> dict[str, Any]:
    root = root.resolve()
    control_root = control_root.resolve()
    projects, blocked = safe_walk(root)
    rows = []
    for project in projects:
        profile = build_profile(project, root, control_root, blocked)
        refs = write_project_artifacts(control_root, profile)
        rows.append({"project_id": profile["project_id"], "project_root": profile["project_root"], "status": profile["status"], "reasons": profile["reasons"], "refs": refs})
    payload = {
        "schema_version": DISCOVERY_SCHEMA,
        "generated_at": now_iso(),
        "scan_root": root.as_posix(),
        "control_plane_root": control_root.as_posix(),
        "projects": rows,
        "blocked_paths": blocked,
    }
    write_json(control_root / DEFAULT_STATE_DIR / "projects.json", payload)
    return payload


def load_or_build_profile(project_root: Path, control_root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    project_root = project_root.resolve()
    profile = build_profile(project_root, project_root, control_root, [])
    refs = write_project_artifacts(control_root, profile)
    return profile, refs


def invoke(project_root: Path, control_root: Path, goal: str, *, plan_only: bool) -> dict[str, Any]:
    if not plan_only:
        raise SystemExit("ASC-0068 supports --plan-only only")
    profile, refs = load_or_build_profile(project_root, control_root)
    envelope = {
        "schema_version": ENVELOPE_SCHEMA,
        "generated_at": now_iso(),
        "goal": goal,
        "project_id": profile["project_id"],
        "project_root": profile["project_root"],
        "project_profile_ref": refs["profile"],
        "authority_ref": refs["authority"],
        "semantic_handshake_ref": refs["semantic_handshake"],
        "requested_mode": "plan_only",
        "required_os_roles": OS_ROLES,
        "stop_conditions": build_authority(profile)["stop_conditions"] + ["asc_0067_incompatible_envelope"],
        "next_command": f"python scripts/aios_invoke.py --project {profile['project_root']} --goal {json.dumps(goal)} --plan-only --json",
    }
    path = discovery_dir(control_root, profile["project_id"]) / "invocation_envelope.json"
    write_json(path, envelope)
    return {"ok": True, "project_id": profile["project_id"], "status": profile["status"], "invocation_envelope": rel(path, control_root), "envelope": envelope}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_parser = sub.add_parser("scan")
    scan_parser.add_argument("--root", required=True)
    scan_parser.add_argument("--json", action="store_true")

    invoke_parser = sub.add_parser("invoke")
    invoke_parser.add_argument("--project", required=True)
    invoke_parser.add_argument("--goal", required=True)
    invoke_parser.add_argument("--plan-only", action="store_true")
    invoke_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    control_root = Path(args.control_root).resolve()
    if args.command == "scan":
        payload = scan(Path(args.root), control_root)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "invoke":
        payload = invoke(Path(args.project), control_root, args.goal, plan_only=args.plan_only)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
