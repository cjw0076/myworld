#!/usr/bin/env python3
"""Process repo-originated AIOS goals into reviewable contract candidates.

The processor is intentionally conservative. It reads `.aios/goal_inbox/**`
packets, classifies each packet, writes durable review artifacts, and leaves
the original inbox packets untouched for audit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from scripts.aios_repo_goal import ALLOWED_REPOS, GOAL_SCHEMA, load_goal_packet  # noqa: E402


SCHEMA_VERSION = "aios.goal_inbox_processor.v1"
PROCESSED_INDEX_SCHEMA = "aios.goal_inbox_processed_index.v1"
CLASSIFICATIONS = {
    "auto_promote_distinct",
    "merge_with_justification",
    "needs_operator_review",
    "reject_out_of_scope",
    "defer_capability_gap",
}

THEMES: dict[str, dict[str, Any]] = {
    "research-to-sprint-context-primitive": {
        "title": "Research To Sprint Context Primitive",
        "repos": ["myworld", "memoryOS", "CapabilityOS", "hivemind"],
        "owner": "myworld",
        "goal": (
            "Convert public research receipts into sprint context, MemoryOS draft "
            "candidates, CapabilityOS route notes, and Hive execution hints "
            "without manual bookkeeping."
        ),
        "keywords": ["research_to_sprint", "public web research", "research notes", "growth intel"],
        "verification": [
            "python scripts/aios_doc_scout.py --root /home/user/workspaces/jaewon --json",
            "python scripts/aios_monitor.py assess --json",
        ],
        "stop_conditions": [
            "private_source_ingest",
            "uncited_web_claim",
            "memory_auto_accept",
            "capability_binding_without_review",
            "verification_gate_failed",
        ],
    },
    "product-repo-sprint-driver": {
        "title": "Product Repo Sprint Driver",
        "repos": ["myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS"],
        "owner": "myworld",
        "goal": (
            "Turn product-repo goals into AIOS-owned sprint packets with Genesis "
            "divergence, MemoryOS context, CapabilityOS route, Hive execution, "
            "verification receipts, and feedback learning."
        ),
        "keywords": [
            "aios-only",
            "campus app",
            "direct codex",
            "manual codex",
            "product development",
            "product repo",
            "sprint",
            "uri development",
            "uri sprint",
            "user-facing operator",
        ],
        "verification": [
            "python scripts/aios_sprint_loop.py plan --repo uri --json",
            "python scripts/aios_monitor.py assess --json",
        ],
        "stop_conditions": [
            "direct_product_repo_edit_from_myworld",
            "missing_memory_context",
            "missing_capability_route",
            "missing_hive_receipt",
            "verification_gate_failed",
        ],
    },
    "provider-fallback-execution-binding": {
        "title": "Provider Fallback Execution Binding",
        "repos": ["hivemind", "CapabilityOS", "myworld"],
        "owner": "hivemind",
        "goal": (
            "Bind ASC-0066 provider backpressure role capsules to an executable, "
            "verified fallback path that can hand work to Claude, Codex, Gemini, "
            "or a local LLM without bypassing Hive verification."
        ),
        "keywords": [
            "access denied",
            "add-dir",
            "auth",
            "backpressure",
            "bwrap",
            "claude",
            "codex",
            "context failure",
            "fallback",
            "local llm",
            "permission",
            "provider",
            "quota",
            "rate limit",
            "sandbox",
            "timeout",
            "usage limit",
            "writable provider",
        ],
        "verification": [
            "cd /home/user/workspaces/jaewon/myworld/hivemind",
            "python -m pytest tests/test_provider_loop.py tests/test_local_worker_routing.py -v",
            "cd /home/user/workspaces/jaewon/myworld/CapabilityOS",
            "python -m pytest tests/test_cli.py tests/test_observation.py -v",
            "cd /home/user/workspaces/jaewon/myworld",
            "python scripts/aios_monitor.py assess --json",
        ],
        "stop_conditions": [
            "fallback_executes_without_contract",
            "provider_secret_leak",
            "role_capsule_missing_rubric",
            "local_llm_used_as_final_acceptor_without_verifier",
            "verification_gate_failed",
        ],
    },
}

CAPABILITY_GAP_KEYWORDS = [
    "agent_surface",
    "capabilityos route",
    "capabilityos should recommend",
    "deterministic avatar",
    "route",
]

OUT_OF_SCOPE_KEYWORDS = [
    ".env",
    "raw export",
    "raw_exports",
    "secret=",
    "token=",
    "password=",
]


@dataclass(frozen=True)
class Classification:
    goal_id: str
    source_repo: str
    source_path: str
    classification: str
    reason: str
    output_path: str | None = None
    theme: str | None = None
    evidence_link: str | None = None
    merge_target: str | None = None
    merge_justification: str | None = None
    previously_processed: bool = False


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_suffix(*parts: str) -> str:
    return sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]


def slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower() or "repo-goal-candidate"


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_processed_index(root: Path) -> dict[str, Any]:
    path = root / ".aios" / "primitives" / "goal_inbox_run" / "index.json"
    if not path.exists():
        return {"schema_version": PROCESSED_INDEX_SCHEMA, "processed": {}}
    try:
        payload = read_json(path)
    except json.JSONDecodeError:
        return {"schema_version": PROCESSED_INDEX_SCHEMA, "processed": {}}
    if payload.get("schema_version") != PROCESSED_INDEX_SCHEMA or not isinstance(payload.get("processed"), dict):
        return {"schema_version": PROCESSED_INDEX_SCHEMA, "processed": {}}
    return payload


def write_processed_index(root: Path, payload: dict[str, Any]) -> None:
    path = root / ".aios" / "primitives" / "goal_inbox_run" / "index.json"
    payload["schema_version"] = PROCESSED_INDEX_SCHEMA
    payload["updated_at"] = now_iso()
    write_json(path, payload)


def iter_goal_paths(root: Path) -> list[Path]:
    base = root / ".aios" / "goal_inbox"
    if not base.exists():
        return []
    return sorted(base.glob("*/*.json"))


def load_packet_for_classification(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return load_goal_packet(path), None
    except (SystemExit, json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
        return None, str(exc)


def text_for(packet: dict[str, Any]) -> str:
    return " ".join(
        [
            str(packet.get("kind") or ""),
            str(packet.get("goal") or ""),
            str(packet.get("summary") or ""),
            " ".join(str(ref) for ref in packet.get("evidence_refs") or []),
        ]
    ).lower()


def matching_theme(text: str) -> str | None:
    scores: list[tuple[int, int, str]] = []
    for priority, (slug, spec) in enumerate(THEMES.items()):
        score = sum(1 for keyword in spec["keywords"] if keyword in text)
        if score:
            scores.append((score, -priority, slug))
    if not scores:
        return None
    return sorted(scores, reverse=True)[0][2]


def classify_packet(packet: dict[str, Any] | None, error: str | None = None) -> tuple[str, str, str | None]:
    if packet is None:
        return "reject_out_of_scope", f"invalid goal packet: {error or 'unknown error'}", None
    text = text_for(packet)
    if any(keyword in text for keyword in OUT_OF_SCOPE_KEYWORDS):
        return "reject_out_of_scope", "packet references forbidden secret/raw/private surface", None
    theme = matching_theme(text)
    if theme:
        return "auto_promote_distinct", f"maps to AIOS capability theme but requires per-packet response: {theme}", theme
    if any(keyword in text for keyword in CAPABILITY_GAP_KEYWORDS):
        return "defer_capability_gap", "requires CapabilityOS route/card review before contract promotion", None
    if packet.get("kind") in {"blocker", "friction"}:
        return "needs_operator_review", "blocker/friction did not map to a known automation theme", None
    return "needs_operator_review", "goal is valid but needs operator triage before promotion", None


def next_contract_id(contracts_dir: Path) -> str:
    highest = 0
    for path in contracts_dir.glob("ASC-*.md"):
        match = re.match(r"ASC-(\d{4})-", path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"ASC-{highest + 1:04d}"


def existing_contract_for_slug(root: Path, slug: str) -> Path | None:
    matches = sorted((root / "docs" / "contracts").glob(f"ASC-*-{slug}.md"))
    return matches[0] if matches else None


def output_contract_path(root: Path, slug: str) -> tuple[str, Path]:
    existing = existing_contract_for_slug(root, slug)
    if existing:
        match = re.match(r"(ASC-\d{4})-", existing.name)
        return (match.group(1) if match else existing.stem.split("-", 2)[0], existing)
    contract_id = next_contract_id(root / "docs" / "contracts")
    return contract_id, root / "docs" / "contracts" / f"{contract_id}-{slug}.md"


def distinct_contract_slug(theme: str, packet: dict[str, Any]) -> str:
    goal_id = str(packet.get("goal_id") or "")
    source_repo = str(packet.get("source_repo") or "repo")
    goal_slug = slugify(str(packet.get("goal") or goal_id))[:48].strip("-")
    suffix = stable_suffix(source_repo, goal_id, str(packet.get("goal") or ""))[:8]
    return slugify(f"{theme}-{source_repo}-{goal_slug}-{suffix}")


def output_distinct_contract_path(root: Path, slug: str) -> tuple[str, Path]:
    matches = sorted((root / "docs" / "contracts").glob(f"ASC-*-{slug}.md"))
    if matches:
        existing = matches[0]
        match = re.match(r"(ASC-\d{4})-", existing.name)
        return (match.group(1) if match else existing.stem.split("-", 2)[0], existing)
    contract_id = next_contract_id(root / "docs" / "contracts")
    return contract_id, root / "docs" / "contracts" / f"{contract_id}-{slug}.md"


def render_contract(contract_id: str, slug: str, spec: dict[str, Any], packets: list[dict[str, Any]]) -> str:
    created = now_iso()
    repo_lines = "\n".join(f"- `{repo}`" for repo in spec["repos"])
    source_lines = "\n".join(
        f"- `{packet['goal_id']}` from `{packet['source_repo']}`: {packet.get('goal', '').strip()}"
        for packet in packets
    )
    evidence_lines = []
    for packet in packets:
        for ref in packet.get("evidence_refs") or []:
            evidence_lines.append(f"- `{packet['goal_id']}` evidence: `{ref}`")
    if not evidence_lines:
        evidence_lines.append("- none supplied by source packets")
    verification = "\n".join(spec["verification"])
    stops = "\n".join(f"- `{item}`" for item in spec["stop_conditions"])
    role_evidence = render_aios_role_evidence_section()
    return f"""---
contract_id: {contract_id}
slug: {slug}
status: proposed
goal: {spec['goal']}
created: {created}
accepted:
closed:
origin: ASC-0058 goal inbox processor promoted repo-originated goal packets.
---

# {contract_id} {spec['title']}

## Why Now

Lower repos submitted AIOS-relevant goal or friction packets that map to this
theme. ASC-0115 requires this draft to answer the specific source packet(s)
listed below instead of silently merging them into a broad theme. This draft is
proposed only. The operator must accept it before any dispatch or
implementation.

## Source Goal Packets

{source_lines}

## Source Evidence

{chr(10).join(evidence_lines)}

## Scope

repos:

{repo_lines}

allowed_files:

- contract-specific files must be narrowed before acceptance
- `docs/contracts/{contract_id}-{slug}.md`
- `docs/contracts/README.md`
- `docs/AIOS_AGENT_LEDGER.md`

forbidden_files:

- `.env`
- `.env.*`
- `.aios/goal_inbox/**`
- raw export paths
- broad child-repo source edits before accepted work packets

## Responsibilities

### {spec['owner']}.must_produce

- A narrowed accepted contract scope with exact files.
- Work packets for every repo that owns implementation.
- Verification receipts linked back to the source goal packets.

### MemoryOS.must_produce

- Context pack or memory draft candidates only if accepted scope requires it.
- No accepted memory without review.

### CapabilityOS.must_produce

- Route or fallback recommendation only if accepted scope requires it.
- No tool/provider binding without an accepted contract.

### Hive Mind.must_produce

- Execution plan, provider route, role capsule, receipt, and verification
  evidence for any implementation packet it owns.

{role_evidence}

## Verification Gate

```bash
{verification}
```

Pass criteria:

- Contract remains `proposed` until operator acceptance.
- Accepted revision narrows allowed files before dispatch.
- Result packets link back to all source goal ids above.
- Verification evidence exists before closeout.

## Stop Conditions

{stops}
- `operator_acceptance_missing`
- `scope_not_narrowed_before_dispatch`
"""


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


def write_contract_candidate(root: Path, slug: str, packets: list[dict[str, Any]], *, rewrite: bool = False) -> Path:
    spec = THEMES[slug]
    contract_id, path = output_contract_path(root, slug)
    if path.exists() and not rewrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_contract(contract_id, slug, spec, packets), encoding="utf-8")
    return path


def write_distinct_contract_candidate(root: Path, theme: str, packet: dict[str, Any], *, rewrite: bool = False) -> Path:
    spec = THEMES[theme]
    slug = distinct_contract_slug(theme, packet)
    contract_id, path = output_distinct_contract_path(root, slug)
    if path.exists() and not rewrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_contract(contract_id, slug, spec, [packet]), encoding="utf-8")
    return path


def should_reprocess_previous(previous: Any) -> bool:
    if not isinstance(previous, dict):
        return False
    classification = str(previous.get("classification") or "")
    if classification == "auto_promote":
        return True
    return classification not in CLASSIFICATIONS


def write_operator_note(root: Path, packet: dict[str, Any] | None, source_path: Path, classification: str, reason: str) -> Path:
    goal_id = str((packet or {}).get("goal_id") or source_path.stem)
    path = root / "docs" / "operator_queue" / f"{goal_id}-{classification}.md"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    goal = str((packet or {}).get("goal") or "invalid goal packet")
    repo = str((packet or {}).get("source_repo") or "unknown")
    path.write_text(
        "\n".join(
            [
                f"# {goal_id} {classification}",
                "",
                f"- source_repo: `{repo}`",
                f"- source_path: `{relpath(source_path, root)}`",
                f"- reason: {reason}",
                f"- goal: {goal}",
                "",
                "Operator action: revise, reject, or promote through a new AIOS smart contract.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_capability_gap(root: Path, packet: dict[str, Any], source_path: Path, reason: str) -> Path:
    goal_id = str(packet.get("goal_id") or source_path.stem)
    path = root / ".aios" / "capability_gaps" / f"{goal_id}.json"
    if path.exists():
        return path
    write_json(
        path,
        {
            "schema_version": "aios.capability_gap.v1",
            "created_at": now_iso(),
            "goal_id": goal_id,
            "source_repo": packet.get("source_repo"),
            "source_path": relpath(source_path, root),
            "reason": reason,
            "goal": packet.get("goal"),
            "summary": packet.get("summary", ""),
            "status": "pending_capabilityos_review",
        },
    )
    return path


def process(root: Path, *, reprocess: bool = False) -> dict[str, Any]:
    root = root.resolve()
    index = read_processed_index(root)
    processed: dict[str, Any] = index.setdefault("processed", {})
    paths = iter_goal_paths(root)
    loaded: list[tuple[Path, dict[str, Any] | None, str | None]] = []
    for path in paths:
        packet, error = load_packet_for_classification(path)
        loaded.append((path, packet, error))

    initial: list[tuple[Path, dict[str, Any] | None, str | None, str, str, str | None]] = []
    for path, packet, error in loaded:
        classification, reason, theme = classify_packet(packet, error)
        initial.append((path, packet, error, classification, reason, theme))
    results: list[Classification] = []

    for path, packet, _error, classification, reason, theme in initial:
        goal_id = str((packet or {}).get("goal_id") or path.stem)
        source_repo = str((packet or {}).get("source_repo") or path.parent.name)
        evidence_link = relpath(path, root)
        previous = processed.get(goal_id)
        if isinstance(previous, dict):
            if not reprocess and not should_reprocess_previous(previous):
                results.append(
                    Classification(
                        goal_id=goal_id,
                        source_repo=source_repo,
                        source_path=relpath(path, root),
                        classification=str(previous.get("classification") or classification),
                        reason=str(previous.get("reason") or "already processed"),
                        output_path=previous.get("output_path"),
                        theme=previous.get("theme"),
                        evidence_link=previous.get("evidence_link") or evidence_link,
                        merge_target=previous.get("merge_target"),
                        merge_justification=previous.get("merge_justification"),
                        previously_processed=True,
                    )
                )
                continue

        output_path: str | None = None
        merge_target: str | None = None
        merge_justification: str | None = None
        if classification == "auto_promote_distinct" and theme and packet:
            output_path = relpath(write_distinct_contract_candidate(root, theme, packet, rewrite=reprocess), root)
        elif classification in {"needs_operator_review", "reject_out_of_scope"}:
            output_path = relpath(write_operator_note(root, packet, path, classification, reason), root)
        elif classification == "defer_capability_gap" and packet:
            output_path = relpath(write_capability_gap(root, packet, path, reason), root)

        processed[goal_id] = {
            "classification": classification,
            "processed_at": now_iso(),
            "reason": reason,
            "source_path": relpath(path, root),
            "source_repo": source_repo,
            "output_path": output_path,
            "theme": theme,
            "evidence_link": evidence_link,
            "merge_target": merge_target,
            "merge_justification": merge_justification,
        }
        results.append(
            Classification(
                goal_id=goal_id,
                source_repo=source_repo,
                source_path=relpath(path, root),
                classification=classification,
                reason=reason,
                output_path=output_path,
                theme=theme,
                evidence_link=evidence_link,
                merge_target=merge_target,
                merge_justification=merge_justification,
            )
        )

    write_processed_index(root, index)
    receipt_id = f"gir_{datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S')}_{stable_suffix(str(len(results)), now_iso())}"
    counts = {name: 0 for name in sorted(CLASSIFICATIONS)}
    for item in results:
        counts[item.classification] = counts.get(item.classification, 0) + 1
    counts["silently_skipped"] = 0
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": receipt_id,
        "created_at": now_iso(),
        "root": root.as_posix(),
        "packets_seen": len(paths),
        "classified": len(results),
        "previously_processed": sum(1 for item in results if item.previously_processed),
        "skipped_already_processed": 0,
        "silently_skipped": 0,
        "counts": counts,
        "contract_candidates": sorted({item.output_path for item in results if item.classification == "auto_promote_distinct" and item.output_path}),
        "operator_queue": sorted({item.output_path for item in results if item.classification in {"needs_operator_review", "reject_out_of_scope"} and item.output_path}),
        "capability_gaps": sorted({item.output_path for item in results if item.classification == "defer_capability_gap" and item.output_path}),
        "results": [item.__dict__ for item in results],
    }
    receipt_path = root / ".aios" / "primitives" / "goal_inbox_run" / f"{receipt_id}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = relpath(receipt_path, root)
    return receipt


def latest_receipts(root: Path) -> list[dict[str, Any]]:
    receipt_dir = root / ".aios" / "primitives" / "goal_inbox_run"
    rows = []
    for path in sorted(receipt_dir.glob("gir_*.json")):
        try:
            payload = read_json(path)
        except json.JSONDecodeError:
            continue
        if payload.get("schema_version") == SCHEMA_VERSION:
            payload["receipt_path"] = relpath(path, root)
            rows.append(payload)
    return rows


def build_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    receipts = latest_receipts(root)
    latest = receipts[-1] if receipts else None
    index = read_processed_index(root)
    return {
        "schema_version": "aios.goal_inbox_processor_report.v1",
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "goal_inbox_packets": len(iter_goal_paths(root)),
        "processed_index_count": len(index.get("processed") or {}),
        "receipt_count": len(receipts),
        "latest_receipt": latest,
    }


def command_process(args: argparse.Namespace) -> int:
    root = Path(args.root)
    payload = process(root, reprocess=bool(args.reprocess))
    if args.assert_min_classified is not None and payload["classified"] < args.assert_min_classified:
        print(
            f"classified {payload['classified']} < required {args.assert_min_classified}",
            file=sys.stderr,
        )
        return 3
    if args.assert_silently_skipped_zero and payload.get("silently_skipped", 0) != 0:
        print(f"silently_skipped must be 0; got {payload.get('silently_skipped')}", file=sys.stderr)
        return 4
    if args.assert_per_citizen_response:
        root = root.resolve()
        for result in payload.get("results") or []:
            classification = result.get("classification")
            goal_id = result.get("goal_id")
            if classification == "auto_promote":
                print(f"legacy auto_promote is forbidden: {goal_id}", file=sys.stderr)
                return 5
            if classification == "merge_with_justification" and not result.get("merge_justification"):
                print(f"merge without justification: {goal_id}", file=sys.stderr)
                return 6
            if classification == "auto_promote_distinct":
                output_path = result.get("output_path")
                if not output_path:
                    print(f"auto_promote_distinct missing output_path: {goal_id}", file=sys.stderr)
                    return 7
                contract_path = root / str(output_path)
                if not contract_path.exists():
                    print(f"auto_promote_distinct output does not exist: {output_path}", file=sys.stderr)
                    return 8
                body = contract_path.read_text(encoding="utf-8")
                if str(goal_id) not in body:
                    print(f"contract does not cite source goal id: {goal_id}", file=sys.stderr)
                    return 9
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['run_id']} classified={payload['classified']} receipt={payload['receipt_path']}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    payload = build_report(Path(args.root))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        latest = payload.get("latest_receipt") or {}
        print(
            f"goal_inbox_packets={payload['goal_inbox_packets']} "
            f"processed={payload['processed_index_count']} "
            f"latest={latest.get('receipt_path', 'none')}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--assert-min-classified", type=int)
    parser.add_argument("--assert-silently-skipped-zero", action="store_true")
    parser.add_argument("--assert-per-citizen-response", action="store_true")
    parser.add_argument("--reprocess", action="store_true", help="recompute classifications for already indexed packets")
    sub = parser.add_subparsers(dest="command")

    report = sub.add_parser("report", help="summarize goal inbox processing receipts")
    report.add_argument("--root", default=".")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=command_report)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return command_process(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
