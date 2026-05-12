#!/usr/bin/env python3
"""Evaluate proposed AIOS actions against governance policy."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.action_policy.v1"
DECISIONS = {"allow", "hold", "deny", "escalate"}
FORBIDDEN_ACTION_TYPES = {
    "illegal_access",
    "credential_theft",
    "secret_exfiltration",
    "coercion",
    "deception",
    "raw_private_export_publish",
    "bypass_child_repo_ownership",
}
HIGH_IMPACT_FIELDS = (
    "irreversible",
    "external_effect",
    "uses_credentials",
    "public_communication",
    "legal_or_safety_impact",
    "real_world_authority",
)


EXAMPLES: dict[str, dict[str, Any]] = {
    "low_risk_local": {
        "action_type": "local_verification",
        "target_repo": "myworld",
        "authority": "delegated_operator",
        "risk": "low",
        "privacy": "local",
        "cost": "free",
        "has_contract": True,
        "evidence_refs": ["docs/contracts/ASC-0034-governance-action-policy-engine.md"],
        "human_approved": False,
        "irreversible": False,
        "external_effect": False,
        "uses_credentials": False,
        "public_communication": False,
        "legal_or_safety_impact": False,
        "real_world_authority": False,
    },
    "missing_contract": {
        "action_type": "child_repo_edit",
        "target_repo": "hivemind",
        "authority": "delegated_operator",
        "risk": "medium",
        "privacy": "local",
        "cost": "free",
        "has_contract": False,
        "evidence_refs": [],
    },
    "forbidden": {
        "action_type": "secret_exfiltration",
        "target_repo": "external",
        "authority": "none",
        "risk": "high",
        "privacy": "remote",
        "cost": "unknown",
        "has_contract": True,
        "evidence_refs": ["operator_request"],
    },
    "public_authority": {
        "action_type": "public_statement",
        "target_repo": "external",
        "authority": "delegated_operator",
        "risk": "high",
        "privacy": "remote",
        "cost": "free",
        "has_contract": True,
        "evidence_refs": ["docs/AIOS_GOVERNANCE_MODEL.md"],
        "human_approved": False,
        "public_communication": True,
        "real_world_authority": True,
    },
}


@dataclass(frozen=True)
class ActionPolicyResult:
    decision: str
    reason_codes: list[str]
    required_checkpoint: bool
    allowed_to_execute: bool

    def to_json(self, action: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "decision": self.decision,
            "allowed_to_execute": self.allowed_to_execute,
            "required_checkpoint": self.required_checkpoint,
            "reason_codes": self.reason_codes,
            "action": action,
        }


def evaluate_action(action: dict[str, Any]) -> ActionPolicyResult:
    reason_codes: list[str] = []
    action_type = str(action.get("action_type") or "").strip()
    risk = str(action.get("risk") or "").strip().lower()
    privacy = str(action.get("privacy") or "").strip().lower()
    cost = str(action.get("cost") or "").strip().lower()
    target_repo = str(action.get("target_repo") or "").strip()
    evidence_refs = action.get("evidence_refs")
    human_approved = bool(action.get("human_approved"))

    if action_type in FORBIDDEN_ACTION_TYPES:
        return ActionPolicyResult("deny", [f"forbidden_action:{action_type}"], True, False)

    if target_repo in {"hivemind", "memoryOS", "CapabilityOS", "uri"} and action.get("direct_child_repo_edit") and not action.get("has_contract"):
        return ActionPolicyResult("deny", ["child_repo_ownership_bypass"], True, False)

    high_impact = [field for field in HIGH_IMPACT_FIELDS if bool(action.get(field))]
    if high_impact and not human_approved:
        return ActionPolicyResult(
            "escalate",
            [f"human_checkpoint_required:{field}" for field in high_impact],
            True,
            False,
        )

    if risk == "high" and not human_approved:
        return ActionPolicyResult("escalate", ["human_checkpoint_required:risk_high"], True, False)
    if cost in {"medium", "high", "paid", "unknown"} and not human_approved:
        return ActionPolicyResult("escalate", [f"human_checkpoint_required:cost_{cost}"], True, False)
    if privacy in {"remote", "mixed"} and action.get("sends_private_data") and not human_approved:
        return ActionPolicyResult("escalate", ["human_checkpoint_required:private_remote_data"], True, False)

    if not action.get("has_contract"):
        reason_codes.append("missing_contract")
    if not target_repo:
        reason_codes.append("missing_target_repo")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        reason_codes.append("missing_evidence_refs")
    if risk not in {"low", "medium", "high"}:
        reason_codes.append("missing_or_invalid_risk")
    if privacy not in {"local", "remote", "mixed"}:
        reason_codes.append("missing_or_invalid_privacy")
    if reason_codes:
        return ActionPolicyResult("hold", reason_codes, False, False)

    if risk == "low" and privacy == "local":
        return ActionPolicyResult("allow", ["low_risk_local_contract_evidence"], False, True)

    return ActionPolicyResult("hold", ["requires_more_specific_policy"], False, False)


def load_action(args: argparse.Namespace) -> dict[str, Any]:
    if args.example:
        if args.example not in EXAMPLES:
            raise ValueError(f"unknown example: {args.example}")
        return dict(EXAMPLES[args.example])
    if args.path:
        data = json.loads(Path(args.path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("action file must contain a JSON object")
        return data
    if args.inline:
        data = json.loads(args.inline)
        if not isinstance(data, dict):
            raise ValueError("--inline must be a JSON object")
        return data
    raise ValueError("provide --example, --path, or --inline")


def cmd_evaluate(args: argparse.Namespace) -> int:
    action = load_action(args)
    result = evaluate_action(action)
    payload = result.to_json(action)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['decision']} allowed={payload['allowed_to_execute']} checkpoint={payload['required_checkpoint']}")
        for reason in payload["reason_codes"]:
            print(f"- {reason}")
    return 0 if payload["decision"] in DECISIONS else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate proposed AIOS actions")
    sub = parser.add_subparsers(dest="cmd", required=True)
    evaluate = sub.add_parser("evaluate")
    source = evaluate.add_mutually_exclusive_group(required=True)
    source.add_argument("--example", choices=sorted(EXAMPLES))
    source.add_argument("--path")
    source.add_argument("--inline")
    evaluate.add_argument("--json", action="store_true")
    evaluate.set_defaults(func=cmd_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
