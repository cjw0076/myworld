#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from scripts.aios_goal_evolution import build_plan  # noqa: E402
from scripts.aios_boundary_classifier import payload as boundary_payload  # noqa: E402


SCHEMA_VERSION = "aios.contract_autodraft.v1"
REPO_NAMES = {"myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS"}


def now_kst_label() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")


def next_contract_id(contracts_dir: Path) -> str:
    highest = 0
    for path in contracts_dir.glob("ASC-*.md"):
        match = re.match(r"ASC-(\d{4})-", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ASC-{highest + 1:04d}"


def slugify(text: str) -> str:
    text = text.removeprefix("goal:")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "goal-contract"


def draft_contract(plan: dict[str, Any], contract_id: str) -> dict[str, Any]:
    stops = plan.get("stop_conditions") or []
    rec = plan.get("recommendation")
    if stops:
        raise ValueError(f"goal plan has stop conditions: {', '.join(stops)}")
    if not isinstance(rec, dict):
        raise ValueError("goal plan has no recommendation")
    if rec.get("blocked"):
        raise ValueError("recommended candidate is blocked")

    slug = slugify(str(rec.get("path") or rec.get("candidate_task") or "goal-contract"))
    task = " ".join(str(rec.get("candidate_task") or "").split())
    if not task:
        raise ValueError("recommended candidate has no task")
    boundary = boundary_payload(task)
    domain = str(rec.get("domain") or "myworld")
    repos = contract_repos(domain, str(boundary["owner_repo"]))

    body = render_contract_body(plan, contract_id, slug, repos, task, boundary)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": contract_id,
        "slug": slug,
        "status": "proposed",
        "goal": task,
        "repos": repos,
        "path": f"docs/contracts/{contract_id}-{slug}.md",
        "body": body,
        "source_plan_generated_at": plan.get("generated_at"),
        "source_recommendation": rec,
        "auto_accept": False,
    }


def contract_repos(domain: str, boundary_owner: str) -> list[str]:
    selected: list[str] = []
    if domain in REPO_NAMES:
        selected.append(domain)
    else:
        selected.append("myworld")
    if boundary_owner in REPO_NAMES and boundary_owner not in selected:
        selected.append(boundary_owner)
    return selected


def render_contract_body(
    plan: dict[str, Any],
    contract_id: str,
    slug: str,
    repos: list[str],
    task: str,
    boundary: dict[str, str | list[str]],
) -> str:
    rec = plan["recommendation"]
    evidence = plan.get("evidence") or {}
    repo_lines = "\n".join(f"- `{repo}`" for repo in repos)
    allowed_lines = "\n".join(default_allowed_files(repos))
    forbidden_lines = "\n".join(
        [
            "- `.aios/logs/**`",
            "- `.aios/state/**`",
            "- `.aios/inbox/**`",
            "- `.aios/outbox/**`",
            "- `.env`",
            "- raw export paths",
        ]
    )
    role_evidence = render_aios_role_evidence_section()
    boundary_gate = render_boundary_gate(task, boundary, str(rec.get("domain") or "myworld"))
    return f"""---
contract_id: {contract_id}
slug: {slug}
status: proposed
goal: {task}
created: {now_kst_label()}
accepted:
closed:
---

# {contract_id} {title_from_slug(slug)}

## Why Now

Goal evolution selected this unblocked recommendation:

- path: `{rec.get('path')}`
- domain: `{rec.get('domain')}`
- policy_decision: `{rec.get('policy_decision')}`
- reason: {rec.get('policy_reason')}

This draft is proposed only. Operator acceptance must flip frontmatter status
before dispatch.

## Scope

repos:

{repo_lines}

allowed_files:

{allowed_lines}

forbidden_files:

{forbidden_lines}

## Responsibilities

### myworld.must_produce

- A narrowed implementation plan for: {task}
- Exact allowed files before acceptance if the defaults above are too broad.
- Verification commands that prove the contract closed.
- Dispatch, result packet, release, and ledger evidence after acceptance.

### child repos

- No source role unless the accepted contract explicitly assigns one.

{boundary_gate}

{role_evidence}

## Verification Gate

```bash
python -m unittest discover -s tests -p 'test_aios_*.py'
python scripts/aios_monitor.py assess --json
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- Scope names exact repos and avoids child-repo source edits unless assigned.
- Verification evidence is linked before closeout.
- Monitor remains clear.

## Stop Conditions

- `operator_acceptance_missing`
- `scope_ambiguous`
- `allowed_files_too_broad`
- `child_repo_source_edit`
- `verification_gate_failed`
- `monitor_not_clear`

## Source Plan Evidence

- generated_at: `{plan.get('generated_at')}`
- monitor_health: `{evidence.get('monitor_health')}`
- readiness: `{evidence.get('readiness_level_name')}`
- alignment_reasons: `{', '.join(rec.get('alignment_reasons') or [])}`
- blocked_reasons: `{', '.join(rec.get('blocked_reasons') or [])}`
"""


def render_boundary_gate(task: str, boundary: dict[str, str | list[str]], domain: str) -> str:
    stop_conditions = list(boundary["stop_conditions"])
    if domain != boundary["owner_repo"]:
        stop_conditions.append("boundary_owner_differs_from_recommendation_domain")
    return f"""## Substrate / Surface / Knowledge Gate

- schema_version: `{boundary['schema_version']}`
- layer: `{boundary['layer']}`
- owner_repo: `{boundary['owner_repo']}`
- substrate_level: `{boundary['substrate_level']}`
- surface_type: `{boundary['surface_type']}`
- knowledge_scope: `{boundary['knowledge_scope']}`
- authority: `{boundary['authority']}`
- next_contract_kind: `{boundary['next_contract_kind']}`

required_receipts:

{bullet_lines(boundary["required_receipts"])}

boundary_stop_conditions:

{bullet_lines(stop_conditions)}
"""


def bullet_lines(values: list[str] | tuple[str, ...]) -> str:
    return "\n".join(f"- `{value}`" for value in values)


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


def default_allowed_files(repos: list[str]) -> list[str]:
    if repos == ["myworld"]:
        return [
            "- `scripts/<contract-specific>.py`",
            "- `tests/test_<contract-specific>.py`",
            "- `docs/contracts/<this-contract>.md`",
            "- `docs/contracts/README.md`",
            "- `docs/AIOS_AGENT_LEDGER.md`",
        ]
    return [f"- `{repo}/<contract-specific-path>`" for repo in repos]


def title_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def write_draft(path: Path, body: str, *, force: bool = False) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"contract draft already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def cmd_draft(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    if args.plan_json:
        plan = json.loads(Path(args.plan_json).read_text(encoding="utf-8"))
    else:
        goal = Path(args.goal)
        if not goal.is_absolute():
            goal = root / goal
        radar = Path(args.radar)
        if not radar.is_absolute():
            radar = root / radar
        plan = build_plan(root, goal, radar)
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    contract_id = args.contract_id or next_contract_id(output_dir)
    draft = draft_contract(plan, contract_id)
    output_path = output_dir / f"{draft['contract_id']}-{draft['slug']}.md"
    draft["path"] = output_path.relative_to(root).as_posix() if output_path.is_relative_to(root) else output_path.as_posix()
    if args.write:
        write_draft(output_path, draft["body"], force=args.force)
    if args.json:
        payload = {key: value for key, value in draft.items() if key != "body"}
        payload["written"] = bool(args.write)
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(draft["path"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Draft proposed AIOS smart contracts from goal evolution")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)
    draft = sub.add_parser("draft")
    draft.add_argument("--goal", default="docs/goals/AIOS-GOAL-0001-make-something-great.md")
    draft.add_argument("--radar", default="docs/AIOS_TASK_RADAR.md")
    draft.add_argument("--plan-json", help="use a precomputed goal evolution JSON plan")
    draft.add_argument("--output-dir", default="docs/contracts")
    draft.add_argument("--contract-id")
    draft.add_argument("--write", action="store_true")
    draft.add_argument("--force", action="store_true")
    draft.add_argument("--json", action="store_true")
    draft.set_defaults(func=cmd_draft)
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
    sys.exit(main())
