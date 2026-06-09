#!/usr/bin/env python3
"""AIOS Work — a goal-spanning, forkable work object (blueprint step 6).

Teardown §logging: omo's `BoulderState` models that one GOAL spans many sessions
(works → tasks → sessions, with status/elapsed/worktree), and codex/claude thread
lineage (`forked_from_id`/`parentUuid`). AIOS had flat per-session receipts with no
goal-spanning state and no parent pointers — so a goal interrupted across sessions
was lost. This is the object that links them:

  Work{ work_id, goal, status(active|paused|completed|abandoned), run_ids[],
        parent_work (lineage), worktree, started/ended }

`resume()` reconstructs each attached run via aios_run_log.reconstruct → where the
goal stands and where to pick up. Append-only-friendly (status transitions recorded,
never destroyed). Privacy: ids/status/goal-label only.

Schema: aios.work.v1
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK_DIR = ROOT / ".aios" / "work"
STATUSES = ("active", "paused", "completed", "abandoned")


def _wid(goal: str, seq: int) -> str:
    h = 0
    for c in goal:
        h = (h * 131 + ord(c)) % (1 << 32)
    return f"work-{h:08x}-{seq}"


@dataclass
class Work:
    work_id: str
    goal: str
    status: str = "active"
    run_ids: list[str] = field(default_factory=list)
    parent_work: str = ""
    worktree: str = ""
    started: str = ""
    ended: str = ""

    def to_dict(self) -> dict:
        return {"schema_version": "aios.work.v1", **asdict(self)}


def _path(work_id: str, work_dir: Path) -> Path:
    return Path(work_dir) / f"{work_id}.json"


def save(work: Work, *, work_dir: Path = WORK_DIR) -> Path:
    work_dir.mkdir(parents=True, exist_ok=True)
    p = _path(work.work_id, work_dir)
    p.write_text(json.dumps(work.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load(work_id: str, *, work_dir: Path = WORK_DIR) -> Work | None:
    p = _path(work_id, work_dir)
    if not p.is_file():
        return None
    o = json.loads(p.read_text(encoding="utf-8"))
    o.pop("schema_version", None)
    return Work(**{k: v for k, v in o.items() if k in Work.__dataclass_fields__})


def start_work(goal: str, *, seq: int = 0, started: str = "", worktree: str = "",
               work_dir: Path = WORK_DIR) -> Work:
    w = Work(work_id=_wid(goal, seq), goal=goal[:160], status="active",
             started=started, worktree=worktree)
    save(w, work_dir=work_dir)
    return w


def attach_run(work_id: str, run_id: str, *, work_dir: Path = WORK_DIR) -> bool:
    w = load(work_id, work_dir=work_dir)
    if w is None:
        return False
    if run_id not in w.run_ids:
        w.run_ids.append(run_id)
    save(w, work_dir=work_dir)
    return True


def set_status(work_id: str, status: str, *, ended: str = "", work_dir: Path = WORK_DIR) -> bool:
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    w = load(work_id, work_dir=work_dir)
    if w is None:
        return False
    w.status = status
    if status in ("completed", "abandoned"):
        w.ended = ended
    save(w, work_dir=work_dir)
    return True


def fork_work(parent_work_id: str, goal: str, *, seq: int = 0, work_dir: Path = WORK_DIR) -> Work | None:
    parent = load(parent_work_id, work_dir=work_dir)
    if parent is None:
        return None
    w = Work(work_id=_wid(goal, seq), goal=goal[:160], status="active",
             parent_work=parent_work_id)
    save(w, work_dir=work_dir)
    return w


def resume(work_id: str, *, work_dir: Path = WORK_DIR, runs_dir: Path | None = None) -> dict:
    """Reconstruct where a goal stands across its sessions — each run via run_log."""
    import aios_run_log as rl
    rd = runs_dir or rl.RUNS
    w = load(work_id, work_dir=work_dir)
    if w is None:
        return {"resumable": False, "reason": "no work object"}
    runs = [rl.reconstruct(Path(rd) / f"{rid}.jsonl") for rid in w.run_ids]
    resumable_runs = [r for r in runs if r.get("resumable")]
    return {
        "schema_version": "aios.work.v1", "work_id": work_id, "goal": w.goal,
        "status": w.status, "parent_work": w.parent_work or None,
        "sessions": len(w.run_ids), "resumable_sessions": len(resumable_runs),
        "total_tool_calls": sum(r.get("tool_calls_so_far", 0) for r in runs),
        "resumable": w.status in ("active", "paused"),
        "last_run": runs[-1] if runs else None,
    }


if __name__ == "__main__":
    w = start_work("ship the deadline copilot to a real student")
    attach_run(w.work_id, "run-a")
    set_status(w.work_id, "paused")
    print(json.dumps(resume(w.work_id), ensure_ascii=False, indent=2))
