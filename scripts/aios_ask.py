#!/usr/bin/env python3
"""User-facing AIOS ask interface.

`ask` turns one natural-language goal into durable AIOS artifacts. It does not
execute child repo work by itself; it prepares the MemoryOS, CapabilityOS,
GenesisOS, Hive, praxis, and operator instruction surfaces needed for dispatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aios_invoke
from aios_work_praxis import SCHEMA_VERSION as PRAXIS_SCHEMA
from aios_work_praxis import draft_praxis, validate_praxis


ASK_SCHEMA = "aios.ask.v1"
RECEIPT_SCHEMA = "aios.ask.receipt.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_ask_dir(root: Path, goal: str, write: str | None) -> Path:
    base = (root / ".aios" / "asks").resolve()
    if write:
        candidate = (root / write).resolve() if not Path(write).is_absolute() else Path(write).resolve()
    else:
        stamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%dT%H%M%S")
        candidate = base / f"ask-{aios_invoke.stable_hash(goal)[:12]}-{stamp}"
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise SystemExit(f"ask output must stay under {base}") from exc
    return candidate


def read_json_artifact(root: Path, rel_path: str | None) -> dict[str, Any]:
    if not rel_path:
        return {}
    path = root / rel_path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def capability_routes_from(payload: dict[str, Any]) -> list[str]:
    routes = []
    for row in payload.get("recommendations") or []:
        if isinstance(row, dict) and row.get("id"):
            routes.append(f"aios://capability/{row['id']}")
    return routes


def genesis_frames_from(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    branches = [row for row in payload.get("branches") or [] if isinstance(row, dict)]
    frictions = []
    frames = []
    for branch in branches:
        premise = str(branch.get("premise") or "").strip()
        seed = str(branch.get("contract_seed") or branch.get("type") or "").strip()
        if premise and len(frictions) < 3:
            frictions.append(premise)
        if seed and len(frames) < 3:
            frames.append(seed)
    if not frictions:
        frictions = ["The ask interface must prevent direct implementation from skipping AIOS role separation."]
    if not frames:
        frames = ["Ask as production preflight", "Ask as OS-role instruction packet"]
    return frictions, frames


def build_praxis_from_invocation(root: Path, goal: str, invocation: dict[str, Any]) -> dict[str, Any]:
    artifact_paths = invocation.get("artifact_paths") or {}
    capability_payload = read_json_artifact(root, artifact_paths.get("capability"))
    genesis_payload = read_json_artifact(root, artifact_paths.get("genesis"))
    hive_payload = read_json_artifact(root, artifact_paths.get("hive"))
    draft = draft_praxis(goal)

    memory_refs = [
        ref
        for ref in [
            artifact_paths.get("memory_context_pack"),
            artifact_paths.get("memory_request"),
        ]
        if isinstance(ref, str) and ref
    ]
    routes = capability_routes_from(capability_payload)
    frictions, frames = genesis_frames_from(genesis_payload)
    hive_gate = hive_payload.get("verification_gate")
    if isinstance(hive_gate, list):
        hive_gate_text = " && ".join(str(item) for item in hive_gate)
    else:
        hive_gate_text = str(hive_gate or "python scripts/aios_monitor.py assess --json")

    draft["memory_context"] = {
        "status": "used",
        "owner": "MemoryOS",
        "evidence_refs": memory_refs or [str(artifact_paths.get("receipt") or "invocation_receipt_missing")],
    }
    draft["capability_routes"] = {
        "status": "used",
        "owner": "CapabilityOS",
        "routes": routes or ["aios://capability/cap_capabilityos_recommendation"],
        "evidence_refs": [artifact_paths.get("capability")] if artifact_paths.get("capability") else [],
    }
    draft["external_resource_check"] = {
        "status": "optional_with_reason",
        "reason": "Ask preparation used local AIOS role CLIs; external resources should be added by the generated contract when current public facts are required.",
    }
    draft["genesis_reframe"] = {
        "status": "used",
        "owner": "GenesisOS",
        "frictions": frictions,
        "alternative_frames": frames,
        "evidence_refs": [artifact_paths.get("genesis")] if artifact_paths.get("genesis") else [],
    }
    draft["hive_execution_plan"] = {
        "status": "planned",
        "owner": "Hive Mind",
        "verification_gate": hive_gate_text,
        "evidence_refs": [artifact_paths.get("hive")] if artifact_paths.get("hive") else [],
    }
    return draft


def build_instruction(goal: str, ask_id: str, invocation: dict[str, Any], praxis_ref: str) -> str:
    status = invocation.get("overall_status")
    next_action = invocation.get("next_action")
    return "\n".join(
        [
            f"# AIOS Ask {ask_id}",
            "",
            f"Goal: {goal}",
            "",
            "## AIOS Route",
            "",
            f"- invocation_status: `{status}`",
            f"- invocation_next_action: `{next_action}`",
            f"- praxis: `{praxis_ref}`",
            "",
            "## Operator Next Step",
            "",
            "1. Review the praxis envelope.",
            "2. Draft or select an accepted AIOS smart contract.",
            "3. Dispatch with `python scripts/aios_dispatch.py send --repo <repo> --agent <agent> --praxis <praxis>` when the contract sets `praxis_required: true`.",
            "",
            "## Stop Conditions",
            "",
            "- Do not treat this ask artifact as execution authority.",
            "- Do not bypass contract scope, repo ownership, or praxis validation.",
            "- If any AIOS role is degraded, repair that route or record why degraded planning is acceptable.",
            "",
        ]
    )


def slugify(text: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()[:80] or "ask-contract"


def render_aios_role_evidence_section() -> str:
    return """## AIOS Role Evidence

### MemoryOS

- context_pack: `pending_or_not_required`
- retrieval_trace: `pending_or_not_required`
- accepted_memory_ids: `pending_or_not_required`
- draft_memory_policy: `draft_first_no_auto_accept`

### CapabilityOS

- route: `pending_or_not_required`
- recommended_tools: `pending_or_not_required`
- fallback_plan: `pending_or_not_required`
- authority: `recommendation_only`

### GenesisOS

- branch_set: `pending_or_not_required`
- assumption_mutations: `pending_or_not_required`
- semantic_alignment_notes: `pending_or_not_required`
- authority: `advisory_only`

### Hive Mind

- execution_plan: `pending_after_acceptance`
- provider_route: `pending_after_acceptance`
- verification_receipt: `pending_after_execution`
- degraded_or_fallback_receipt: `pending_if_triggered`
"""


def render_contract_seed(goal: str, ask_id: str, praxis_ref: str, instruction_ref: str) -> str:
    slug = slugify(goal)
    role_evidence = render_aios_role_evidence_section()
    return f"""---
contract_id: ASC-XXXX
slug: {slug}
status: proposed
goal: {goal}
created: {now_iso()}
accepted:
closed:
praxis_required: true
praxis_ref: {praxis_ref}
origin: AIOS ask {ask_id}
---

# ASC-XXXX {slug.replace("-", " ").title()}

## Why Now

This proposed contract was generated from AIOS ask `{ask_id}`.

- ask_instruction: `{instruction_ref}`
- praxis: `{praxis_ref}`

Operator must assign the final ASC id, narrow scope, and accept before
dispatch.

## Scope

repos:

- `myworld`

allowed_files:

- `docs/contracts/ASC-XXXX-{slug}.md`
- `docs/praxis/<accepted-praxis>.json`
- `docs/AGENT_WORKLOG.md`

forbidden_files:

- `.env`
- raw exports
- private provider auth files
- child repo implementation files unless explicitly assigned

## Responsibilities

### myworld

must_produce:

- Review ask instruction and praxis envelope.
- Narrow owner repo and allowed files before acceptance.
- Dispatch only with `--praxis {praxis_ref}`.
- Collect result packet and release only after verification evidence.

{role_evidence}

## Verification Gate

```bash
cd .
python scripts/aios_work_praxis.py validate {praxis_ref} --json
python scripts/aios_monitor.py assess --json
```

## Stop Conditions

- `operator_acceptance_missing`
- `scope_ambiguous`
- `praxis_invalid`
- `owner_repo_unclear`
- `verification_gate_missing`
- `monitor_not_clear`

## Receipts

Pending.
"""


def build_ask(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    goal = args.goal_text
    ask_dir = resolve_ask_dir(root, goal, args.write)
    ask_id = ask_dir.name
    invocation_dir = root / ".aios" / "invocations" / ask_id
    invocation_args = aios_invoke.build_parser().parse_args(
        [
            "--root",
            root.as_posix(),
            "--goal",
            goal,
            "--write",
            relative(invocation_dir, root),
            "--plan-only",
            "--json",
        ]
    )
    invocation = aios_invoke.build_invocation(root, invocation_args)
    praxis = build_praxis_from_invocation(root, goal, invocation)
    praxis_errors = validate_praxis(praxis)

    ask_goal = {
        "schema_version": ASK_SCHEMA,
        "ask_id": ask_id,
        "goal": goal,
        "goal_hash": aios_invoke.stable_hash(goal),
        "created_at": now_iso(),
        "mode": "plan_only",
    }
    write_json(ask_dir / "goal.json", ask_goal)
    write_json(ask_dir / "praxis.json", praxis)
    instruction = build_instruction(goal, ask_id, invocation, relative(ask_dir / "praxis.json", root))
    write_text(ask_dir / "instruction.md", instruction)
    contract_seed_path = ask_dir / "contract_seed.md"
    if getattr(args, "draft_contract", False):
        write_text(
            contract_seed_path,
            render_contract_seed(
                goal,
                ask_id,
                relative(ask_dir / "praxis.json", root),
                relative(ask_dir / "instruction.md", root),
            ),
        )

    status = "passed" if not praxis_errors and invocation.get("overall_status") in {"passed", "degraded"} else "held"
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "ask_id": ask_id,
        "goal": goal,
        "status": status,
        "created_at": now_iso(),
        "artifact_paths": {
            "goal": relative(ask_dir / "goal.json", root),
            "instruction": relative(ask_dir / "instruction.md", root),
            "praxis": relative(ask_dir / "praxis.json", root),
            "invocation_receipt": invocation.get("artifact_paths", {}).get("receipt"),
            "contract_seed": relative(contract_seed_path, root) if contract_seed_path.exists() else None,
        },
        "invocation_status": invocation.get("overall_status"),
        "invocation_role_statuses": invocation.get("role_statuses"),
        "praxis_errors": praxis_errors,
        "next_action": "review_instruction_and_dispatch" if status == "passed" else "repair_praxis_or_role_artifacts",
    }
    write_json(ask_dir / "receipt.json", receipt)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create an AIOS ask artifact from one natural-language goal")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", help="output directory under .aios/asks")
    parser.add_argument("--draft-contract", action="store_true", help="also write a proposed contract seed for operator review")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("goal", nargs="+", help="natural-language goal")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.goal_text = " ".join(args.goal).strip()
    if not args.goal_text:
        parser.error("goal is required")
    root = args.root.resolve()
    receipt = build_ask(root, args)
    if args.json:
        print(canonical_json(receipt))
    else:
        print(f"{receipt['schema_version']} status={receipt['status']} ask_id={receipt['ask_id']}")
        print(receipt["artifact_paths"]["instruction"])
    return 0 if receipt.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
