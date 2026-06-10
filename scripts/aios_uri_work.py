#!/usr/bin/env python3
"""aios uri-work — real, file-backed Uri Work job lifecycle.

This is NOT a mock. Every command writes to .aios/uri-work/*.jsonl.
State persists across sessions. attribution runs attribution math and
writes to the ledger — the result is queryable next session.

Stores (append-only JSONL, DNA invariant #3):
  .aios/uri-work/jobs.jsonl       — job state log (last per jobId = live state)
  .aios/uri-work/events.jsonl     — usage events (for attribution, by jobId)
  .aios/uri-work/ledger.jsonl     — attribution + settlement records

CLI:
  job create  --id JW-001 --task poster --price 30000 --requester "김회장" --org "IT동아리"
  job advance --id JW-001 --stage in_progress
  job event   --id JW-001 --contributor "agent:claude" --mode jump --ref "ref:draft-v2" [--weight 70]
  job close   --id JW-001 --paid [--evidence "ref:receipt"]
  job show    --id JW-001
  job list
  ledger show [--id JW-001]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _SCRIPT_DIR.parent


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _store_path(root: Path, name: str) -> Path:
    p = root / ".aios" / "uri-work" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _append(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_all(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # corrupted line — skip, never destroy
    return out


def _emit_primitive_event(root: Path, event_name: str, payload: dict) -> None:
    """Append one event to the AIOS primitive event bus (.aios/primitives/events.jsonl)."""
    bus_path = root / ".aios" / "primitives" / "events.jsonl"
    bus_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema_version": "aios.primitive_event.v1",
        "kind": "uri_work",
        "name": event_name,
        "ts_iso": now_iso(),
        "payload": {**payload, "eventType": event_name},
    }
    with bus_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _live_jobs(root: Path) -> dict[str, dict]:
    """Latest state per jobId — the live view of the append-only job log."""
    jobs: dict[str, dict] = {}
    for rec in _read_all(_store_path(root, "jobs.jsonl")):
        jobs[rec["jobId"]] = rec
    return jobs


# ---------------------------------------------------------------------------
# Attribution math (Python port of uri-ledger.ts — same invariants)
# ---------------------------------------------------------------------------

DEFAULT_NO_JUMP_CAP = 0.5


def attribute(job: dict, events: list[dict], no_jump_cap: float = DEFAULT_NO_JUMP_CAP) -> dict | None:
    """
    Evidence-gated attribution. Returns None when there is no usable evidence.
    Conservation: credits Σ = 1.0 (within fp epsilon).
    """
    job_id = job["jobId"]
    usable = [
        e for e in events
        if e.get("jobId") == job_id and str(e.get("evidenceRef", "")).strip()
    ]
    if not usable:
        return None

    jumps = [e for e in usable if e.get("mode") == "jump"]
    no_jumps = [
        e for e in usable
        if e.get("mode") == "no_jump"
        and isinstance(e.get("costSavedKrw"), (int, float))
        and e["costSavedKrw"] > 0
    ]

    if not jumps and not no_jumps:
        return None

    price = job.get("priceKrw") or 0
    saved_total = sum(e["costSavedKrw"] for e in no_jumps) if no_jumps else 0.0

    if jumps and price > 0 and no_jumps:
        no_jump_pool = min(saved_total / price, no_jump_cap)
    elif not jumps:
        no_jump_pool = 1.0
    else:
        no_jump_pool = 0.0

    credits: dict[str, float] = {}
    contributors: dict[str, dict] = {}

    def add(c: dict, v: float) -> None:
        credits[c["id"]] = credits.get(c["id"], 0.0) + v
        contributors[c["id"]] = c

    if no_jumps:
        for e in no_jumps:
            add(
                {"id": e["contributorId"], "kind": e.get("contributorKind", "agent")},
                no_jump_pool * (e["costSavedKrw"] / saved_total),
            )

    jump_pool = 1.0 - no_jump_pool
    if jumps:
        hints = [e.get("weightHint") for e in jumps]
        have_all = all(isinstance(h, (int, float)) and h > 0 for h in hints)
        total_hint = sum(hints) if have_all else float(len(jumps))
        for i, e in enumerate(jumps):
            w = (hints[i] / total_hint) if have_all else (1.0 / len(jumps))
            add(
                {"id": e["contributorId"], "kind": e.get("contributorKind", "agent")},
                jump_pool * w,
            )

    return {
        "jobId": job_id,
        "credits": credits,
        "contributors": contributors,
        "evidenceRefs": [e["evidenceRef"] for e in usable],
        "noJumpShare": no_jump_pool,
    }


def settle(job: dict, attribution: dict) -> list[dict] | None:
    """
    Largest-remainder integer KRW split. Σ amountKrw == priceKrw exactly.
    Returns None for non-paid jobs.
    """
    if job.get("stage") != "paid":
        return None
    price = job.get("priceKrw")
    if not isinstance(price, (int, float)) or price <= 0:
        return None
    if job["jobId"] != attribution["jobId"]:
        return None

    price = int(price)
    entries = list(attribution["credits"].items())  # [(id, credit), ...]
    raw = [(id_, credit, credit * price) for id_, credit in entries]
    floored = [(id_, credit, int(exact)) for id_, credit, exact in raw]

    remainder = price - sum(f for _, _, f in floored)

    # sort by largest fractional part, then alphabetical by id (deterministic)
    order = sorted(
        range(len(raw)),
        key=lambda i: (-(raw[i][2] - floored[i][2]), raw[i][0]),
    )

    result = list(floored)
    for i in order:
        if remainder <= 0:
            break
        id_, credit, amount = result[i]
        result[i] = (id_, credit, amount + 1)
        remainder -= 1

    return [
        {
            "jobId": job["jobId"],
            "contributorId": id_,
            "kind": attribution["contributors"][id_]["kind"],
            "credit": credit,
            "amountKrw": amount,
            "payee": "contributor" if attribution["contributors"][id_]["kind"] == "human" else "operator",
        }
        for id_, credit, amount in result
    ]


def build_ledger_entries(attribution: dict, settlements: list[dict], at: str) -> list[dict]:
    out = [
        {
            "at": at,
            "kind": "attribution",
            "jobId": attribution["jobId"],
            "payload": attribution,
            "evidenceRefs": attribution["evidenceRefs"],
        }
    ]
    if settlements:
        out.append(
            {
                "at": at,
                "kind": "settlement",
                "jobId": attribution["jobId"],
                "payload": settlements,
                "evidenceRefs": attribution["evidenceRefs"],
            }
        )
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_job_create(args: argparse.Namespace, root: Path) -> int:
    live = _live_jobs(root)
    if args.id in live:
        print(f"error: job {args.id} already exists (stage={live[args.id]['stage']})", file=sys.stderr)
        return 1
    rec = {
        "jobId": args.id,
        "requester": {
            "name": args.requester,
            "org": args.org,
            "orgType": args.org_type,
            "verifiedHow": args.verified_how,
        },
        "taskType": args.task,
        "stage": "requested",
        "priceKrw": args.price,
        "revisionsCount": 0,
        "agentContributionPct": None,
        "briefRef": args.brief_ref,
        "at": now_iso(),
        "updatedAt": now_iso(),
    }
    _append(_store_path(root, "jobs.jsonl"), rec)
    print(json.dumps({"ok": True, "jobId": args.id, "stage": "requested"}, ensure_ascii=False))
    return 0


def cmd_job_advance(args: argparse.Namespace, root: Path) -> int:
    live = _live_jobs(root)
    if args.id not in live:
        print(f"error: job {args.id} not found", file=sys.stderr)
        return 1
    job = dict(live[args.id])
    job["stage"] = args.stage
    job["updatedAt"] = now_iso()
    if args.stage == "paid":
        job["paidAt"] = now_iso()
    _append(_store_path(root, "jobs.jsonl"), job)
    print(json.dumps({"ok": True, "jobId": args.id, "stage": args.stage}, ensure_ascii=False))
    return 0


def cmd_job_event(args: argparse.Namespace, root: Path) -> int:
    """Record a usage event (contribution evidence) for a job."""
    live = _live_jobs(root)
    if args.id not in live:
        print(f"error: job {args.id} not found", file=sys.stderr)
        return 1
    event: dict[str, Any] = {
        "jobId": args.id,
        "contributorId": args.contributor,
        "contributorKind": args.kind,
        "mode": args.mode,
        "evidenceRef": args.ref,
        "at": now_iso(),
    }
    if args.weight is not None:
        event["weightHint"] = args.weight
    if args.cost_saved is not None:
        event["costSavedKrw"] = args.cost_saved
    _append(_store_path(root, "events.jsonl"), event)
    print(json.dumps({"ok": True, "event": event}, ensure_ascii=False))
    return 0


def cmd_job_close(args: argparse.Namespace, root: Path) -> int:
    """Mark as paid, run attribution, write ledger. This is the first real AIOS action."""
    live = _live_jobs(root)
    if args.id not in live:
        print(f"error: job {args.id} not found", file=sys.stderr)
        return 1

    job = dict(live[args.id])
    job["stage"] = "paid"
    job["paidAt"] = now_iso()
    job["updatedAt"] = now_iso()
    if args.price is not None:
        job["priceKrw"] = args.price
    if args.agent_pct is not None:
        job["agentContributionPct"] = args.agent_pct
    if args.confirm_hash:
        job["confirmHash"] = args.confirm_hash
    if args.deliverable_url:
        job["deliverableUrl"] = args.deliverable_url

    _append(_store_path(root, "jobs.jsonl"), job)

    # --- attribution ---
    all_events = _read_all(_store_path(root, "events.jsonl"))
    job_events = [e for e in all_events if e.get("jobId") == args.id]

    # If no explicit events were recorded, synthesize from agentContributionPct
    if not job_events and job.get("agentContributionPct") is not None:
        pct = job["agentContributionPct"]
        human_pct = 100 - pct
        ref = args.evidence or f"ref:close-{args.id}"
        if pct > 0:
            job_events.append({
                "jobId": args.id, "contributorId": "agent:aios",
                "contributorKind": "agent", "mode": "jump",
                "evidenceRef": ref, "weightHint": pct,
            })
        if human_pct > 0:
            job_events.append({
                "jobId": args.id, "contributorId": "human:founder",
                "contributorKind": "human", "mode": "jump",
                "evidenceRef": ref, "weightHint": human_pct,
            })

    attr = attribute(job, job_events)
    if attr is None:
        print(json.dumps({
            "ok": True, "jobId": args.id, "stage": "paid",
            "attribution": None,
            "note": "no usable evidence events — record with `job event` then re-close"
        }, ensure_ascii=False))
        return 0

    settlements = settle(job, attr)
    entries = build_ledger_entries(attr, settlements or [], now_iso())

    ledger_path = _store_path(root, "ledger.jsonl")
    for entry in entries:
        _append(ledger_path, entry)

    # Emit to the primitive event bus so event processor and future subscribers
    # can react to a completed payment + attribution.
    _emit_primitive_event(root, "uri-work:paid", {
        "jobId": args.id,
        "priceKrw": job.get("priceKrw"),
        "taskType": job.get("taskType"),
        "attributionTotal": attr.get("total"),
        "ledgerEntriesWritten": len(entries),
    })

    result = {
        "ok": True,
        "jobId": args.id,
        "stage": "paid",
        "attribution": {
            k: v for k, v in attr.items() if k != "contributors"
        },
        "settlement": settlements,
        "ledger_entries_written": len(entries),
        "ledger_path": str(ledger_path),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_job_show(args: argparse.Namespace, root: Path) -> int:
    live = _live_jobs(root)
    if args.id not in live:
        print(f"error: job {args.id} not found", file=sys.stderr)
        return 1
    job = live[args.id]
    events = [e for e in _read_all(_store_path(root, "events.jsonl")) if e.get("jobId") == args.id]
    ledger = [e for e in _read_all(_store_path(root, "ledger.jsonl")) if e.get("jobId") == args.id]
    print(json.dumps({"job": job, "events": events, "ledger": ledger}, ensure_ascii=False, indent=2))
    return 0


def cmd_job_list(args: argparse.Namespace, root: Path) -> int:
    live = _live_jobs(root)
    rows = sorted(live.values(), key=lambda j: j.get("at", ""))
    if not rows:
        print("(no jobs)")
        return 0
    for j in rows:
        price = f"{j.get('priceKrw'):,}원" if j.get("priceKrw") else "미정"
        agent = f"agent {j.get('agentContributionPct')}%" if j.get("agentContributionPct") is not None else ""
        print(f"{j['jobId']:12s}  {j['stage']:12s}  {j['taskType']:12s}  {price:>12s}  {agent}")
    return 0


def cmd_ledger_show(args: argparse.Namespace, root: Path) -> int:
    ledger = _read_all(_store_path(root, "ledger.jsonl"))
    if args.id:
        ledger = [e for e in ledger if e.get("jobId") == args.id]
    if not ledger:
        print("(empty)")
        return 0
    for entry in ledger:
        kind = entry.get("kind", "?")
        job_id = entry.get("jobId", "?")
        at = entry.get("at", "?")
        if kind == "attribution":
            credits = entry.get("payload", {}).get("credits", {})
            credit_str = ", ".join(f"{k}: {v:.2f}" for k, v in credits.items())
            print(f"{at}  [{kind}]  {job_id}  credits: {credit_str}")
        elif kind == "settlement":
            parts = entry.get("payload", [])
            totals = {p["contributorId"]: p["amountKrw"] for p in parts}
            total_str = ", ".join(f"{k}: {v:,}원" for k, v in totals.items())
            print(f"{at}  [{kind}]  {job_id}  {total_str}")
        else:
            print(f"{at}  [{kind}]  {job_id}")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aios uri-work",
        description="Real Uri Work job lifecycle — writes to .aios/uri-work/*.jsonl"
    )
    p.add_argument("--root", type=Path, default=_DEFAULT_ROOT, help="AIOS root (default: myworld/)")
    sub = p.add_subparsers(dest="cmd")

    # job sub-group
    job_p = sub.add_parser("job")
    job_sub = job_p.add_subparsers(dest="job_cmd")

    # job create
    jc = job_sub.add_parser("create")
    jc.add_argument("--id", required=True)
    jc.add_argument("--task", required=True, choices=["poster", "cardnews", "slides", "application", "script", "dev", "other"])
    jc.add_argument("--price", type=int, default=None)
    jc.add_argument("--requester", required=True)
    jc.add_argument("--org", default="")
    jc.add_argument("--org-type", default="club", choices=["club", "capstone", "contest", "council"])
    jc.add_argument("--verified-how", default=None)
    jc.add_argument("--brief-ref", default=None)

    # job advance
    ja = job_sub.add_parser("advance")
    ja.add_argument("--id", required=True)
    ja.add_argument("--stage", required=True, choices=["in_progress", "delivered", "accepted", "paid", "declined", "killed"])

    # job event (record usage evidence)
    je = job_sub.add_parser("event")
    je.add_argument("--id", required=True)
    je.add_argument("--contributor", required=True, help='e.g. "agent:claude-sonnet" or "human:재원"')
    je.add_argument("--kind", default="agent", choices=["agent", "human", "memory", "tool"])
    je.add_argument("--mode", required=True, choices=["jump", "no_jump"])
    je.add_argument("--ref", required=True, help="evidence ref/hash/url (never raw content)")
    je.add_argument("--weight", type=float, default=None, help="relative effort weight (e.g. 70)")
    je.add_argument("--cost-saved", type=int, default=None, help="KRW saved (no_jump only)")

    # job close
    jcl = job_sub.add_parser("close")
    jcl.add_argument("--id", required=True)
    jcl.add_argument("--paid", action="store_true", default=True)
    jcl.add_argument("--price", type=int, default=None)
    jcl.add_argument("--agent-pct", type=int, default=None, help="AI share 0-100 (fallback if no events)")
    jcl.add_argument("--evidence", default=None, help="evidence ref for auto-synthesized events")
    jcl.add_argument("--confirm-hash", default=None)
    jcl.add_argument("--deliverable-url", default=None)

    # job show
    js = job_sub.add_parser("show")
    js.add_argument("--id", required=True)

    # job list
    job_sub.add_parser("list")

    # ledger
    led_p = sub.add_parser("ledger")
    led_sub = led_p.add_subparsers(dest="ledger_cmd")
    lshow = led_sub.add_parser("show")
    lshow.add_argument("--id", default=None, help="filter by jobId")

    return p


def main() -> int:
    p = build_parser()
    args = p.parse_args()
    root = args.root.resolve()

    if args.cmd == "job":
        if args.job_cmd == "create":
            return cmd_job_create(args, root)
        if args.job_cmd == "advance":
            return cmd_job_advance(args, root)
        if args.job_cmd == "event":
            return cmd_job_event(args, root)
        if args.job_cmd == "close":
            return cmd_job_close(args, root)
        if args.job_cmd == "show":
            return cmd_job_show(args, root)
        if args.job_cmd == "list":
            return cmd_job_list(args, root)

    if args.cmd == "ledger":
        if args.ledger_cmd == "show":
            return cmd_ledger_show(args, root)

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
