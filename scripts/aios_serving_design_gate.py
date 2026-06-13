#!/usr/bin/env python3
"""Assess the Product Design gate for the first AIOS end-user serving surface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Final


SCHEMA_VERSION: Final = "aios.serving_design_gate.v1"
DEFAULT_ARTIFACT: Final = Path(".aios/serving/design_gate.json")
INTERACTIVITY_LEVELS: Final = {"full", "static"}
VISUAL_TARGET_TYPES: Final = {"url", "screenshot", "figma", "image", "design_system", "needs_ideation"}
REQUIRED_STOP_CONDITIONS: Final = {
    "ui_implementation_before_visual_target",
    "serving_ui_reuses_operator_control_center",
    "user_memory_not_visible",
    "session_boundary_ambiguous",
    "approval_path_missing",
    "privacy_boundary_ambiguous",
    "world_readiness_claim_without_browser_proof",
}


def artifact_path(root: Path, raw_path: str | None = None) -> Path:
    path = Path(raw_path) if raw_path else DEFAULT_ARTIFACT
    return path if path.is_absolute() else root / path


def load_artifact(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, [f"missing artifact: {path.as_posix()}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return None, ["artifact must be a JSON object"]
    return payload, []


def nonempty_string(payload: dict[str, Any], field: str, errors: list[str]) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field} is required")
        return ""
    return value.strip()


def validate_gate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    nonempty_string(payload, "product_goal", errors)
    visual_target_type = nonempty_string(payload, "visual_target_type", errors)
    if visual_target_type and visual_target_type not in VISUAL_TARGET_TYPES:
        errors.append(f"visual_target_type must be one of {', '.join(sorted(VISUAL_TARGET_TYPES))}")
    visual_target_ref = payload.get("visual_target_ref")
    if visual_target_type != "needs_ideation":
        if not isinstance(visual_target_ref, str) or not visual_target_ref.strip():
            errors.append("visual_target_ref is required unless visual_target_type is needs_ideation")
    interactivity = nonempty_string(payload, "interactivity_level", errors)
    if interactivity and interactivity not in INTERACTIVITY_LEVELS:
        errors.append(f"interactivity_level must be one of {', '.join(sorted(INTERACTIVITY_LEVELS))}")
    if payload.get("confirmed_by_user") is not True:
        errors.append("confirmed_by_user must be true")
    stop_conditions = payload.get("stop_conditions")
    if not isinstance(stop_conditions, list) or not all(isinstance(item, str) for item in stop_conditions):
        errors.append("stop_conditions must be a list of strings")
    else:
        missing = sorted(REQUIRED_STOP_CONDITIONS.difference(stop_conditions))
        if missing:
            errors.append(f"stop_conditions missing required values: {', '.join(missing)}")
    if payload.get("build_allowed") is not True:
        errors.append("build_allowed must be true")
    return errors


def assess(root: Path, raw_path: str | None = None) -> dict[str, Any]:
    path = artifact_path(root, raw_path)
    payload, load_errors = load_artifact(path)
    errors = list(load_errors)
    if payload is not None:
        errors.extend(validate_gate(payload))
    ready = not errors
    return {
        "schema_version": "aios.serving_design_gate.assessment.v1",
        "artifact_path": path.relative_to(root).as_posix() if path.is_relative_to(root) else path.as_posix(),
        "ready": ready,
        "status": "ready" if ready else "missing" if payload is None else "incomplete",
        "errors": errors,
        "next_action": "ASC-0253" if ready else "product_design_get_context",
        "artifact": payload if ready else None,
    }


def cmd_assess(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    result = assess(root, args.artifact)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    else:
        print(f"serving_design_gate={result['status']} ready={result['ready']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["ready"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess AIOS serving Product Design gate readiness")
    sub = parser.add_subparsers(dest="cmd", required=True)
    assess_cmd = sub.add_parser("assess", help="assess serving design gate artifact")
    assess_cmd.add_argument("--root", default=".")
    assess_cmd.add_argument("--artifact")
    assess_cmd.add_argument("--json", action="store_true")
    assess_cmd.set_defaults(func=cmd_assess)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
