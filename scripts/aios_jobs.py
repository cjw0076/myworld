#!/usr/bin/env python3
"""aios jobs — a leased jobs queue for AIOS dispatch (ASC-0185).

AIOS dispatch was a bare file drop into `.aios/inbox/<repo>/`: two watchers
waking together could double-claim the same packet, two autodrafters could
mint the same id, and a crashed worker left a packet lost or double-run
(ASC-0059 watcher-race; the autodraft ID-collision class).

This is Codex CLI's leased-jobs pattern, ported. A job carries `kind`,
`job_key` (idempotency), `lease_until`, `retry_remaining`, and an
`ownership_token`. A worker *claims* a job by taking a lease — claiming is an
atomic `os.rename` between state directories, so exactly one worker wins.
Only the lease holder may complete it; an expired lease returns the job to
the queue with one retry spent; at zero retries the job fails with a named
stop reason (DNA Invariant 4).

State dirs under `.aios/jobs/`: `queued/ leased/ done/ failed/`. Every
transition is also appended to `.aios/jobs/log.jsonl` — the append-only
audit truth (Invariant 3); the state dirs are the fast index.

  aios jobs enqueue --kind <k> --job-key <key> [--contract <id>] [--repo <r>]
  aios jobs claim --worker <token> [--kind <k>]
  aios jobs heartbeat --job <id> --worker <token>
  aios jobs complete --job <id> --worker <token>
  aios jobs fail --job <id> --worker <token> --reason <text>
  aios jobs sweep            expire lapsed leases
  aios jobs status           queue counts
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEASE_SECONDS = 600
DEFAULT_RETRIES = 3
STATES = ("queued", "leased", "done", "failed")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def jobs_root(root: Path) -> Path:
    return root / ".aios" / "jobs"


def _ensure(root: Path) -> Path:
    jr = jobs_root(root)
    for s in STATES:
        (jr / s).mkdir(parents=True, exist_ok=True)
    return jr


def _log(root: Path, event: str, job: dict[str, Any]) -> None:
    """Append a transition to the append-only audit log (Invariant 3)."""
    line = json.dumps({"at": now_iso(), "event": event, "job_id": job.get("job_id"),
                        "state": job.get("state"), "kind": job.get("kind"),
                        "job_key": job.get("job_key")}, ensure_ascii=False)
    with (jobs_root(root) / "log.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _all_jobs(root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    """(state, path, record) for every job in every state dir."""
    out: list[tuple[str, Path, dict[str, Any]]] = []
    jr = jobs_root(root)
    for s in STATES:
        d = jr / s
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                out.append((s, f, json.loads(f.read_text(encoding="utf-8"))))
            except (ValueError, OSError):
                continue
    return out


def enqueue(root: Path, kind: str, job_key: str, contract_id: str = "",
            target_repo: str = "", retries: int = DEFAULT_RETRIES) -> dict[str, Any]:
    """Add a job. A second enqueue with the same job_key is a no-op (dedup)."""
    _ensure(root)
    for state, _, rec in _all_jobs(root):
        if rec.get("job_key") == job_key:
            return {"status": "duplicate", "job_id": rec["job_id"], "state": state}
    job_id = f"job_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{secrets.token_hex(4)}"
    job = {
        "job_id": job_id, "kind": kind, "job_key": job_key,
        "contract_id": contract_id, "target_repo": target_repo,
        "state": "queued", "lease_until": None, "ownership_token": None,
        "retry_remaining": retries, "created_at": now_iso(),
        "provenance": {"enqueued_at": now_iso()},
    }
    (jobs_root(root) / "queued" / f"{job_id}.json").write_text(
        json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(root, "enqueue", job)
    return {"status": "enqueued", "job_id": job_id}


def claim(root: Path, worker: str, kind: str | None = None) -> dict[str, Any]:
    """Atomically claim the oldest queued job. The os.rename is the race
    guard — exactly one worker wins; losers get FileNotFoundError and retry."""
    _ensure(root)
    jr = jobs_root(root)
    for f in sorted((jr / "queued").glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if kind and rec.get("kind") != kind:
            continue
        dest = jr / "leased" / f.name
        try:
            os.rename(f, dest)  # atomic — the claim
        except (FileNotFoundError, OSError):
            continue            # another worker won this one
        rec["state"] = "leased"
        rec["ownership_token"] = worker
        rec["lease_until"] = time.time() + LEASE_SECONDS
        rec["provenance"]["claimed_at"] = now_iso()
        rec["provenance"]["claimed_by"] = worker
        dest.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        _log(root, "claim", rec)
        return {"status": "claimed", "job": rec}
    return {"status": "empty"}


def claim_key(root: Path, worker: str, job_key: str) -> dict[str, Any]:
    """Claim a *specific* queued job by job_key — the watcher path: a watcher
    that has selected an inbox packet leases exactly that job. Atomic rename;
    a second watcher claiming the same key loses. Distinguishes the cases a
    watcher must act on differently:
      claimed     — leased to this worker, process it
      unavailable — already leased/done/failed elsewhere, skip
      absent      — no job for this key (legacy packet), process via file-drop
    """
    _ensure(root)
    jr = jobs_root(root)
    for f in sorted((jr / "queued").glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if rec.get("job_key") != job_key:
            continue
        dest = jr / "leased" / f.name
        try:
            os.rename(f, dest)  # atomic — the claim
        except (FileNotFoundError, OSError):
            return {"status": "unavailable", "reason": "lost the race"}
        rec["state"] = "leased"
        rec["ownership_token"] = worker
        rec["lease_until"] = time.time() + LEASE_SECONDS
        rec["provenance"]["claimed_at"] = now_iso()
        rec["provenance"]["claimed_by"] = worker
        dest.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        _log(root, "claim", rec)
        return {"status": "claimed", "job": rec}
    # not queued — already taken, or never enqueued
    for state in ("leased", "done", "failed"):
        for f in (jr / state).glob("*.json"):
            try:
                if json.loads(f.read_text(encoding="utf-8")).get("job_key") == job_key:
                    return {"status": "unavailable", "state": state}
            except (ValueError, OSError):
                continue
    return {"status": "absent"}


def _find_leased(root: Path, ident: str) -> Path | None:
    """Locate a leased job by job_id (filename) or, as a fallback, job_key."""
    p = jobs_root(root) / "leased" / f"{ident}.json"
    if p.exists():
        return p
    for f in (jobs_root(root) / "leased").glob("*.json"):
        try:
            if json.loads(f.read_text(encoding="utf-8")).get("job_key") == ident:
                return f
        except (ValueError, OSError):
            continue
    return None


def _guard(root: Path, job_id: str, worker: str) -> tuple[Path, dict[str, Any]] | dict[str, Any]:
    p = _find_leased(root, job_id)
    if not p:
        return {"status": "error", "reason": "job not leased or not found"}
    rec = json.loads(p.read_text(encoding="utf-8"))
    if rec.get("ownership_token") != worker:
        return {"status": "error", "reason": "not the lease holder"}
    return p, rec


def heartbeat(root: Path, job_id: str, worker: str) -> dict[str, Any]:
    g = _guard(root, job_id, worker)
    if isinstance(g, dict):
        return g
    p, rec = g
    rec["lease_until"] = time.time() + LEASE_SECONDS
    p.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    _log(root, "heartbeat", rec)
    return {"status": "extended", "job_id": job_id}


def _move(root: Path, p: Path, rec: dict[str, Any], state: str, event: str) -> None:
    rec["state"] = state
    rec["provenance"][f"{state}_at"] = now_iso()
    dest = jobs_root(root) / state / p.name
    dest.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    p.unlink(missing_ok=True)
    _log(root, event, rec)


def complete(root: Path, job_id: str, worker: str) -> dict[str, Any]:
    g = _guard(root, job_id, worker)
    if isinstance(g, dict):
        return g
    p, rec = g
    _move(root, p, rec, "done", "complete")
    return {"status": "done", "job_id": job_id}


def fail(root: Path, job_id: str, worker: str, reason: str) -> dict[str, Any]:
    g = _guard(root, job_id, worker)
    if isinstance(g, dict):
        return g
    p, rec = g
    rec["fail_reason"] = reason
    _move(root, p, rec, "failed", "fail")
    return {"status": "failed", "job_id": job_id, "reason": reason}


def sweep(root: Path) -> dict[str, Any]:
    """Return lapsed leases to the queue (one retry spent); at zero retries
    the job fails with a named stop reason (Invariant 4)."""
    _ensure(root)
    jr = jobs_root(root)
    requeued, failed = [], []
    now = time.time()
    for f in sorted((jr / "leased").glob("*.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if rec.get("lease_until") and rec["lease_until"] > now:
            continue  # lease still valid
        rec["retry_remaining"] = int(rec.get("retry_remaining", 0)) - 1
        if rec["retry_remaining"] >= 0:
            rec["state"] = "queued"
            rec["ownership_token"] = None
            rec["lease_until"] = None
            rec["provenance"]["lease_expired_at"] = now_iso()
            (jr / "queued" / f.name).write_text(
                json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
            f.unlink(missing_ok=True)
            _log(root, "lease_expired_requeue", rec)
            requeued.append(rec["job_id"])
        else:
            rec["fail_reason"] = "lease expired, retries exhausted"
            _move(root, f, rec, "failed", "fail_retries_exhausted")
            failed.append(rec["job_id"])
    return {"status": "swept", "requeued": requeued, "failed": failed}


def status(root: Path) -> dict[str, Any]:
    counts = {s: 0 for s in STATES}
    for state, _, _ in _all_jobs(root):
        counts[state] = counts.get(state, 0) + 1
    return {"schema": "aios.jobs.status.v1", "at": now_iso(), "counts": counts}


def main(argv: list[str] | None = None) -> int:
    # shared flags accepted on either side of the subcommand
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=".")
    common.add_argument("--json", action="store_true")

    p = argparse.ArgumentParser(description="AIOS leased jobs queue", parents=[common])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, parents=[common])

    e = add("enqueue")
    e.add_argument("--kind", required=True)
    e.add_argument("--job-key", required=True)
    e.add_argument("--contract", default="")
    e.add_argument("--repo", default="")
    e.add_argument("--retries", type=int, default=DEFAULT_RETRIES)

    c = add("claim")
    c.add_argument("--worker", required=True)
    c.add_argument("--kind", default=None)

    ck = add("claim-key")
    ck.add_argument("--worker", required=True)
    ck.add_argument("--job-key", required=True)

    for name in ("heartbeat", "complete"):
        s = add(name)
        s.add_argument("--job", required=True)
        s.add_argument("--worker", required=True)

    fp = add("fail")
    fp.add_argument("--job", required=True)
    fp.add_argument("--worker", required=True)
    fp.add_argument("--reason", required=True)

    add("sweep")
    add("status")

    args = p.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "enqueue":
        result = enqueue(root, args.kind, args.job_key, args.contract, args.repo, args.retries)
    elif args.cmd == "claim":
        result = claim(root, args.worker, args.kind)
    elif args.cmd == "claim-key":
        result = claim_key(root, args.worker, args.job_key)
    elif args.cmd == "heartbeat":
        result = heartbeat(root, args.job, args.worker)
    elif args.cmd == "complete":
        result = complete(root, args.job, args.worker)
    elif args.cmd == "fail":
        result = fail(root, args.job, args.worker, args.reason)
    elif args.cmd == "sweep":
        result = sweep(root)
    else:
        result = status(root)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("status") != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
