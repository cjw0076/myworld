#!/usr/bin/env python3
"""
aios_session_entropy.py — Session-length proportional entropy injection.

Reads the oldest session checkpoint to calculate session duration, then
derives an entropy pressure level (1-5). High pressure sessions (long sessions)
trigger more genesis challenges to break convergence patterns.

Usage:
  python3 scripts/aios_session_entropy.py check              # print level + reason
  python3 scripts/aios_session_entropy.py inject [--dry-run] # run challenge if due

Schema: aios.session_entropy.v1
WORK item: WORK-20260612-006
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


SCHEMA = "aios.session_entropy.v1"

# Pressure thresholds (hours → level)
PRESSURE_THRESHOLDS = [
    (0.5, 1),   # <30 min → level 1
    (1.0, 2),   # <1h    → level 2
    (2.0, 3),   # <2h    → level 3
    (4.0, 4),   # <4h    → level 4
    (float("inf"), 5),  # >4h → level 5 (max pressure)
]

# Minimum time between entropy injections (per pressure level)
MIN_INJECTION_INTERVAL = {
    1: timedelta(hours=2),
    2: timedelta(hours=1),
    3: timedelta(minutes=30),
    4: timedelta(minutes=20),
    5: timedelta(minutes=10),
}

GENESIS_CHALLENGES_DIR = Path(".aios/genesis_challenges")
LAST_INJECTION_FILE = Path(".aios/primitives/last_entropy_injection.json")
CHECKPOINT_DIR = Path(".aios/checkpoints")


def _root() -> Path:
    r = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("AIOS_ROOT")
    if r:
        return Path(r)
    here = Path(__file__).resolve().parent.parent
    if (here / ".aios").exists():
        return here
    return Path.cwd()


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def _now_iso() -> str:
    return _now().isoformat(timespec="seconds")


def session_start_time(root: Path) -> datetime | None:
    cp_dir = root / CHECKPOINT_DIR
    if not cp_dir.exists():
        return None
    checkpoints = sorted(cp_dir.glob("*.json"))
    if not checkpoints:
        return None
    try:
        cp = json.loads(checkpoints[0].read_text(encoding="utf-8"))
        ts = cp.get("ts_iso")
        if ts:
            return datetime.fromisoformat(ts)
    except Exception:
        pass
    # Fallback: use file mtime
    return datetime.fromtimestamp(checkpoints[0].stat().st_mtime, tz=timezone.utc).astimezone()


def pressure_level(duration_hours: float) -> int:
    for threshold, level in PRESSURE_THRESHOLDS:
        if duration_hours < threshold:
            return level
    return 5


def last_injection_time(root: Path) -> datetime | None:
    p = root / LAST_INJECTION_FILE
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return datetime.fromisoformat(d["injected_at"])
    except Exception:
        return None


def injection_due(root: Path, level: int) -> tuple[bool, str]:
    last = last_injection_time(root)
    if last is None:
        return True, "no prior injection recorded"
    now = _now()
    min_gap = MIN_INJECTION_INTERVAL[level]
    elapsed = now - last
    if elapsed >= min_gap:
        return True, f"last injection {elapsed} ago (min gap {min_gap})"
    remaining = min_gap - elapsed
    return False, f"next injection in {remaining} (level {level} gap={min_gap})"


def cmd_check(root: Path) -> dict:
    start = session_start_time(root)
    now = _now()
    if start:
        duration_h = (now - start).total_seconds() / 3600
    else:
        duration_h = 0.0

    level = pressure_level(duration_h)
    due, reason = injection_due(root, level)

    result = {
        "schema_version": SCHEMA,
        "session_start": start.isoformat(timespec="seconds") if start else None,
        "session_duration_hours": round(duration_h, 2),
        "pressure_level": level,
        "max_pressure": 5,
        "injection_due": due,
        "reason": reason,
        "checked_at": _now_iso(),
        "min_injection_interval": str(MIN_INJECTION_INTERVAL[level]),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_inject(root: Path, dry_run: bool = False) -> dict:
    start = session_start_time(root)
    now = _now()
    if start:
        duration_h = (now - start).total_seconds() / 3600
    else:
        duration_h = 0.0

    level = pressure_level(duration_h)
    due, reason = injection_due(root, level)

    if not due:
        result = {
            "schema_version": SCHEMA,
            "injected": False,
            "pressure_level": level,
            "reason": reason,
            "checked_at": _now_iso(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    # Build a session-specific snapshot for the critic
    snapshot_text = (
        f"AIOS session entropy check — duration {duration_h:.1f}h, pressure level {level}/5.\n"
        f"Session start: {start.isoformat() if start else 'unknown'}\n"
        f"Current time: {now.isoformat()}\n"
        f"Risk: long session leads to convergent reasoning — challenge current assumptions.\n"
        f"Key assumptions to challenge:\n"
        f"1. Gate A output (ASC-0272~0276) is sufficient before Gate B.\n"
        f"2. Visual target selection is the right gate mechanism for UI work.\n"
        f"3. Codex (autonomous chain) will process ASC-0276 correctly.\n"
        f"4. 149 unreviewed memoryOS drafts are not urgent.\n"
        f"5. Entropy pressure at level {level} needs only {MIN_INJECTION_INTERVAL[level]} gap between injections.\n"
    )

    genesis_root = root / "GenesisOS"
    (root / GENESIS_CHALLENGES_DIR).mkdir(parents=True, exist_ok=True)

    slug = now.strftime("%Y-%m-%dT%H-%M-%S")
    challenge_out = root / GENESIS_CHALLENGES_DIR / f"session-entropy-{slug}.json"
    snapshot_file = root / ".aios/primitives/coevolution" / "session_entropy_snapshot.txt"
    snapshot_file.parent.mkdir(parents=True, exist_ok=True)
    snapshot_file.write_text(snapshot_text, encoding="utf-8")

    challenge_data = {}
    if not dry_run and genesis_root.exists():
        try:
            proc = subprocess.run(
                ["python3", "-m", "genesisos.cli", "critic",
                 "--text", str(snapshot_file), "--json"],
                cwd=str(genesis_root),
                capture_output=True, text=True, timeout=60
            )
            if proc.returncode == 0 and proc.stdout.strip():
                challenge_data = json.loads(proc.stdout.strip())
                challenge_out.write_text(
                    json.dumps(challenge_data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
        except Exception as e:
            challenge_data = {"error": str(e)}

    # Record injection time
    injection_record = {
        "schema_version": SCHEMA,
        "injected_at": _now_iso(),
        "pressure_level": level,
        "session_duration_hours": round(duration_h, 2),
        "challenge_path": str(challenge_out) if not dry_run else None,
        "dry_run": dry_run,
    }
    if not dry_run:
        (root / LAST_INJECTION_FILE).write_text(
            json.dumps(injection_record, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # Emit event
    events_log = root / ".aios/primitives/events.jsonl"
    events_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": "aios.primitive_event.v1",
        "kind": "session_entropy_injection",
        "name": "aios-session-entropy",
        "ts_iso": _now_iso(),
        "payload": {
            "pressure_level": level,
            "session_duration_hours": round(duration_h, 2),
            "challenge_path": str(challenge_out) if not dry_run else None,
            "prison_signature_count": len(challenge_data.get("prison_signatures", [])),
            "soft_block": challenge_data.get("soft_block", False),
            "dry_run": dry_run,
        }
    }
    if not dry_run:
        with events_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    result = {
        "schema_version": SCHEMA,
        "injected": True,
        "dry_run": dry_run,
        "pressure_level": level,
        "session_duration_hours": round(duration_h, 2),
        "challenge_path": str(challenge_out) if not dry_run else None,
        "challenge_summary": {
            "prison_signatures": len(challenge_data.get("prison_signatures", [])),
            "soft_block": challenge_data.get("soft_block", False),
            "confidence": challenge_data.get("confidence"),
        },
        "injected_at": _now_iso(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AIOS session entropy injection")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("check", help="Show current pressure level and whether injection is due")

    p_inject = sub.add_parser("inject", help="Run entropy injection if due")
    p_inject.add_argument("--dry-run", action="store_true", help="Skip actual genesis call and file writes")

    args = parser.parse_args()
    root = _root()

    if args.cmd == "check":
        cmd_check(root)
    elif args.cmd == "inject":
        cmd_inject(root, dry_run=getattr(args, "dry_run", False))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
