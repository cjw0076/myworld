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
NEXT_PRODUCT_DESIGN_STEPS: Final = {"ideate", "prototype"}
REQUIRED_STOP_CONDITIONS: Final = {
    "ui_implementation_before_visual_target",
    "serving_ui_reuses_operator_control_center",
    "user_memory_not_visible",
    "session_boundary_ambiguous",
    "approval_path_missing",
    "privacy_boundary_ambiguous",
    "world_readiness_claim_without_browser_proof",
}


def sorted_values(values: set[str]) -> list[str]:
    return sorted(values)


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
    next_step = nonempty_string(payload, "next_product_design_step", errors)
    if next_step and next_step not in NEXT_PRODUCT_DESIGN_STEPS:
        errors.append(f"next_product_design_step must be one of {', '.join(sorted(NEXT_PRODUCT_DESIGN_STEPS))}")
    if visual_target_type == "needs_ideation":
        if next_step and next_step != "ideate":
            errors.append("needs_ideation requires next_product_design_step=ideate")
        if payload.get("build_allowed") is not False:
            errors.append("needs_ideation requires build_allowed=false")
    elif visual_target_type:
        if next_step and next_step != "prototype":
            errors.append("concrete visual_target_type requires next_product_design_step=prototype")
        if payload.get("build_allowed") is not True:
            errors.append("concrete visual target requires build_allowed=true")
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
    return errors


def build_questions() -> dict[str, Any]:
    return {
        "schema_version": "aios.serving_design_gate.questions.v1",
        "target_artifact": DEFAULT_ARTIFACT.as_posix(),
        "questions": [
            {
                "id": "product_goal",
                "prompt": "What should the first AIOS serving surface let an end user do?",
                "required": True,
            },
            {
                "id": "visual_target_type",
                "prompt": "What visual source should it follow, or should AIOS ideate options first?",
                "required": True,
                "choices": sorted_values(VISUAL_TARGET_TYPES),
            },
            {
                "id": "visual_target_ref",
                "prompt": "If a visual source exists, provide the URL, screenshot path, Figma link, image path, or design-system reference.",
                "required_unless": {"visual_target_type": "needs_ideation"},
            },
            {
                "id": "interactivity_level",
                "prompt": "Should the first version be fully interactive or a faster static prototype?",
                "required": True,
                "choices": sorted_values(INTERACTIVITY_LEVELS),
            },
            {
                "id": "confirmed_by_user",
                "prompt": "Has the operator confirmed this brief?",
                "required": True,
                "choices": [False, True],
            },
        ],
        "required_stop_conditions": sorted(REQUIRED_STOP_CONDITIONS),
        "routing_rules": {
            "needs_ideation": {
                "next_product_design_step": "ideate",
                "build_allowed": False,
            },
            "concrete_visual_target": {
                "next_product_design_step": "prototype",
                "build_allowed": True,
            },
        },
    }


def build_draft(
    product_goal: str,
    visual_target_type: str,
    visual_target_ref: str,
    interactivity_level: str,
    confirmed_by_user: bool,
) -> dict[str, Any]:
    visual_type = visual_target_type.strip()
    next_step = "ideate" if visual_type == "needs_ideation" else "prototype"
    build_allowed = bool(confirmed_by_user and visual_type != "needs_ideation")
    return {
        "schema_version": SCHEMA_VERSION,
        "product_goal": product_goal.strip(),
        "visual_target_type": visual_type,
        "visual_target_ref": visual_target_ref.strip(),
        "interactivity_level": interactivity_level.strip(),
        "confirmed_by_user": confirmed_by_user,
        "next_product_design_step": next_step,
        "build_allowed": build_allowed,
        "stop_conditions": sorted(REQUIRED_STOP_CONDITIONS),
    }


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


def cmd_questions(args: argparse.Namespace) -> int:
    payload = build_questions()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for question in payload["questions"]:
            print(f"{question['id']}: {question['prompt']}")
    return 0


def cmd_draft(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    draft = build_draft(
        product_goal=args.product_goal,
        visual_target_type=args.visual_target_type,
        visual_target_ref=args.visual_target_ref or "",
        interactivity_level=args.interactivity_level,
        confirmed_by_user=args.confirmed_by_user,
    )
    errors = validate_gate(draft)
    output = {
        "schema_version": "aios.serving_design_gate.draft.v1",
        "ready": not errors,
        "status": "ready" if not errors else "incomplete",
        "errors": errors,
        "artifact_path": artifact_path(root, args.artifact).relative_to(root).as_posix(),
        "artifact": draft,
        "written": False,
    }
    if args.write:
        path = artifact_path(root, args.artifact)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(draft, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output["written"] = True
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"serving_design_gate_draft={output['status']} ready={output['ready']} written={output['written']}")
        for error in errors:
            print(f"- {error}")
    return 0 if args.json or not errors else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Assess AIOS serving Product Design gate readiness")
    sub = parser.add_subparsers(dest="cmd", required=True)
    questions_cmd = sub.add_parser("questions", help="print the Product Design intake questions for the serving gate")
    questions_cmd.add_argument("--json", action="store_true")
    questions_cmd.set_defaults(func=cmd_questions)

    draft_cmd = sub.add_parser("draft", help="build a candidate serving design gate artifact from answers")
    draft_cmd.add_argument("--root", default=".")
    draft_cmd.add_argument("--artifact")
    draft_cmd.add_argument("--product-goal", required=True)
    draft_cmd.add_argument("--visual-target-type", required=True, choices=sorted_values(VISUAL_TARGET_TYPES))
    draft_cmd.add_argument("--visual-target-ref", default="")
    draft_cmd.add_argument("--interactivity-level", required=True, choices=sorted_values(INTERACTIVITY_LEVELS))
    draft_cmd.add_argument("--confirmed-by-user", action="store_true")
    draft_cmd.add_argument("--write", action="store_true")
    draft_cmd.add_argument("--json", action="store_true")
    draft_cmd.set_defaults(func=cmd_draft)

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
