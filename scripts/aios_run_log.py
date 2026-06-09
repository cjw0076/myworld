#!/usr/bin/env python3
"""AIOS Run Log — make a kernel run RESUMABLE, not just auditable (blueprint step 5).

Teardown §logging: codex resumes by scanning its rollout newest→oldest, stopping at
the latest `Compacted.replacement_history` (a complete history base) plus the latest
`turn_context` (cwd/model/sandbox/approval). AIOS's ledger is inspectable but never
replayable. This is the run-scoped append-only log that closes that gap:

  session_meta  (run_id, agent, cwd, git_sha, forked_from)   — once, first line
  turn_context  (turn, agent, gate_policy)                    — per turn (durable baseline)
  trajectory    (turn, tool, decision, status)                — per tool call (names only)
  compacted     (base_turn)                                   — periodic checkpoint

`reconstruct()` scans newest→oldest and rebuilds the resume state: the latest
`compacted` base + latest `turn_context` → where to resume. Privacy (DNA #7):
names/status/metadata only — never message or tool content.

Schema: aios.run_log.v1
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / ".aios" / "runs"


def _git_sha(cwd: Path) -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=cwd,
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


@dataclass
class RunLog:
    run_id: str
    agent: str = "codex@myworld"
    runs_dir: Path = RUNS
    forked_from: str = ""
    compact_every: int = 25      # checkpoint cadence (turns)

    def __post_init__(self) -> None:
        self.path = Path(self.runs_dir) / f"{self.run_id}.jsonl"
        self._turns = 0

    def _append(self, rec: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def open(self, *, ts: str = "") -> None:
        """Write session_meta — the run's identity + reproduction baseline."""
        self._append({"kind": "session_meta", "run_id": self.run_id, "agent": self.agent,
                      "cwd": str(ROOT), "git_sha": _git_sha(ROOT),
                      "forked_from": self.forked_from, "ts": ts})

    def sink(self, rec: dict) -> None:
        """turn_sink for aios_turn_loop.run_loop — appends turn_context/trajectory and
        drops a `compacted` checkpoint every `compact_every` turns."""
        if rec.get("kind") == "turn_context":
            self._turns = rec.get("turn", self._turns + 1)
            rec = {**rec, "agent": self.agent}
            if self._turns % self.compact_every == 0:
                self._append({"kind": "compacted", "base_turn": self._turns})
        self._append(rec)


def reconstruct(path: str | Path) -> dict:
    """Rebuild the resume state by scanning newest→oldest: the latest compacted base +
    latest turn_context = where to resume; plus the run's identity. Mirrors codex
    rollout reconstruction. Never reads content — there is none in the log."""
    p = Path(path)
    if not p.exists():
        return {"resumable": False, "reason": "no log"}
    records = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    meta = next((r for r in records if r.get("kind") == "session_meta"), None)
    last_ctx = next((r for r in reversed(records) if r.get("kind") == "turn_context"), None)
    last_compact = next((r for r in reversed(records) if r.get("kind") == "compacted"), None)
    traj = [r for r in records if r.get("kind") == "trajectory"]
    return {
        "schema_version": "aios.run_log.v1",
        "resumable": meta is not None and last_ctx is not None,
        "run_id": (meta or {}).get("run_id"),
        "agent": (meta or {}).get("agent"),
        "git_sha": (meta or {}).get("git_sha"),
        "base_turn": (last_compact or {}).get("base_turn", 0),
        "resume_at_turn": (last_ctx or {}).get("turn", 0) + 1,
        "tool_calls_so_far": len(traj),
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    import aios_tools as tools
    import aios_turn_loop as loop

    rl = RunLog("demo-run")
    rl.open()
    steps = [{"tool_calls": [loop.ToolCall("self.audit", {"claims": []}, call_id="c1")]},
             {"tool_calls": []}]
    it = iter(steps)
    loop.run_loop("demo", lambda h: next(it), tools.build_registry(),
                  gate=tools.gate_for("codex@myworld"), turn_sink=rl.sink)
    print(json.dumps(reconstruct(rl.path), ensure_ascii=False, indent=2))
