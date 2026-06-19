#!/usr/bin/env python3
"""AIOS Event Processor — real daemon that tails .aios/primitives/events.jsonl
and routes new events to handlers.

This closes the loop the 4 pulse scripts opened:
  pulse loop → events.jsonl → (HERE) → handlers → side effects / ledger writes

Cursor-based: processes only NEW events since last run. Idempotent re-runs
never double-process. Cursor stored at .aios/event_processor_cursor.

Handlers registered (extensible):
  self_check  → log failures; trigger genesis critic on FAILURE_REAL
  memory      → forward to MemoryOS memory pulse summary
  genesis     → accumulate for periodic challenge refresh

Note: uri-work handler removed — URI product events are handled inside the
URI repo (uri/scripts/uri_work.py). AIOS core does not depend on URI.

Run modes:
  once   — process all pending events then exit (cron / shell call)
  daemon — loop forever, polling events_path every POLL_SECS
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_SCRIPT_DIR = Path(__file__).resolve().parent
_DEFAULT_ROOT = _SCRIPT_DIR.parent

POLL_SECS = 30  # daemon polling interval
GENESIS_TRIGGER_WINDOW = 20  # invoke genesis critic every N FAILURE_REAL events

Handler = Callable[[dict, Path], None]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Cursor — tracks byte offset in events.jsonl
# ---------------------------------------------------------------------------

def _cursor_path(root: Path) -> Path:
    return root / ".aios" / "event_processor_cursor"


def _read_cursor(root: Path) -> int:
    p = _cursor_path(root)
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_cursor(root: Path, offset: int) -> None:
    p = _cursor_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(str(offset), encoding="utf-8")


# ---------------------------------------------------------------------------
# Event reading
# ---------------------------------------------------------------------------

def _read_new_events(events_path: Path, from_offset: int) -> tuple[list[dict], int]:
    """Read all events after byte offset. Returns (events, new_offset)."""
    if not events_path.exists():
        return [], from_offset

    events: list[dict] = []
    new_offset = from_offset

    with events_path.open("rb") as f:
        f.seek(from_offset)
        while True:
            line = f.readline()
            if not line:
                new_offset = f.tell()
                break
            line_stripped = line.strip()
            if line_stripped:
                try:
                    events.append(json.loads(line_stripped))
                except json.JSONDecodeError:
                    pass  # truncated / corrupt line — skip, DNA #3
            new_offset = f.tell()

    return events, new_offset


# ---------------------------------------------------------------------------
# State shared across handler calls (in-process, reset each run for 'once')
# ---------------------------------------------------------------------------

class ProcessorState:
    def __init__(self) -> None:
        self.failure_real_count = 0
        self.last_genesis_invoke_at_failure = 0
        self.processed_total = 0
        self.dispatched_handlers: list[str] = []


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _handle_self_check(event: dict, root: Path, state: ProcessorState) -> None:
    payload_line = event.get("payload", {}).get("line", "")
    if not payload_line:
        return

    if "FAILURE_REAL" in payload_line:
        state.failure_real_count += 1
        since_last = state.failure_real_count - state.last_genesis_invoke_at_failure
        if since_last >= GENESIS_TRIGGER_WINDOW:
            _invoke_genesis_on_failures(root, state)
            state.last_genesis_invoke_at_failure = state.failure_real_count

    if "DAEMON_DEAD" in payload_line:
        _log_alert(root, "DAEMON_DEAD detected by self_check", payload_line)

    if "DISPATCH_PARSE_BROKEN" in payload_line:
        _log_alert(root, "DISPATCH_PARSE_BROKEN — run: scripts/aios_dispatch.py repair", payload_line)



def _invoke_genesis_on_failures(root: Path, state: ProcessorState) -> None:
    """Invoke GenesisOS critic on accumulated AIOS failures (advisory only)."""
    text = (
        f"AIOS self_check FAILURE_REAL count={state.failure_real_count} "
        f"at {now_iso()}. Recent failures may indicate systemic issues. "
        "Identify the top assumptions in the current AIOS design that, if wrong, "
        "would explain these failures."
    )
    tmp = root / ".aios" / "tmp" / "genesis_event_trigger.txt"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(text, encoding="utf-8")

    genesis_root = root / "GenesisOS"
    if not genesis_root.exists():
        return

    result = subprocess.run(
        [sys.executable, "-m", "genesisos.cli", "critic",
         "--text", str(tmp), "--json"],
        capture_output=True, text=True, timeout=60,
        cwd=str(genesis_root)
    )

    if result.returncode == 0 and result.stdout.strip():
        out_path = root / ".aios" / "genesis_challenges" / f"auto_{now_iso().replace(':', '-')}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result.stdout, encoding="utf-8")
        state.dispatched_handlers.append(f"genesis:auto-critique:{out_path.name}")


def _log_alert(root: Path, summary: str, detail: str = "") -> None:
    alert_path = root / ".aios" / "event_processor_alerts.jsonl"
    record = {"at": now_iso(), "summary": summary, "detail": detail[:300]}
    with alert_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main processing loop
# ---------------------------------------------------------------------------

def _dispatch(event: dict, root: Path, state: ProcessorState) -> None:
    name = event.get("name", "")
    payload = event.get("payload", {})

    if name == "aios-self-check":
        _handle_self_check(event, root, state)
    # capability / memory / hive pulses: currently just counted, not re-dispatched
    # uri-work events: handled inside uri repo — AIOS core ignores them
    state.processed_total += 1


def process_once(root: Path, verbose: bool = False) -> dict[str, Any]:
    events_path = root / ".aios" / "primitives" / "events.jsonl"
    cursor = _read_cursor(root)
    events, new_cursor = _read_new_events(events_path, cursor)

    state = ProcessorState()
    for event in events:
        _dispatch(event, root, state)

    _write_cursor(root, new_cursor)

    summary = {
        "ok": True,
        "processed": len(events),
        "cursor_before": cursor,
        "cursor_after": new_cursor,
        "failure_real_seen": state.failure_real_count,
        "dispatched": state.dispatched_handlers,
        "at": now_iso(),
    }
    if verbose and events:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif verbose:
        print(f"[{now_iso()}] no new events (cursor={new_cursor})")
    return summary


def run_daemon(root: Path, verbose: bool = False) -> None:
    print(f"[{now_iso()}] event processor daemon starting (poll={POLL_SECS}s, root={root})")
    while True:
        try:
            summary = process_once(root, verbose=False)
            if summary["processed"] > 0 or verbose:
                print(
                    f"[{now_iso()}] processed={summary['processed']} "
                    f"failures={summary['failure_real_seen']} "
                    f"dispatched={summary['dispatched']}"
                )
        except KeyboardInterrupt:
            print(f"\n[{now_iso()}] daemon stopped by user")
            break
        except Exception as exc:  # noqa: BLE001
            _log_alert(root, "event_processor crash", str(exc)[:300])
            print(f"[{now_iso()}] error: {exc}", file=sys.stderr)
        time.sleep(POLL_SECS)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aios event-processor",
        description="Process new AIOS primitive events and route to handlers"
    )
    p.add_argument("--root", type=Path, default=_DEFAULT_ROOT)
    p.add_argument("--verbose", "-v", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("once", help="process pending events then exit")
    sub.add_parser("daemon", help="run continuously, polling every 30s")
    sub.add_parser("status", help="show cursor position and event backlog size")
    emit_p = sub.add_parser("emit", help="manually emit a typed event into the bus")
    emit_p.add_argument("event_type", help='e.g. "uri-work:paid"')
    emit_p.add_argument("--payload", default="{}", help="JSON payload string")

    return p


def main() -> int:
    p = build_parser()
    args = p.parse_args()
    root = args.root.resolve()

    if args.cmd == "once" or args.cmd is None:
        summary = process_once(root, verbose=True)
        if args.cmd is None:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "daemon":
        run_daemon(root, verbose=getattr(args, "verbose", False))
        return 0

    if args.cmd == "status":
        events_path = root / ".aios" / "primitives" / "events.jsonl"
        cursor = _read_cursor(root)
        total = events_path.stat().st_size if events_path.exists() else 0
        backlog = max(0, total - cursor)
        print(json.dumps({
            "cursor": cursor,
            "total_bytes": total,
            "backlog_bytes": backlog,
            "approx_unprocessed_events": backlog // 150,  # ~150 bytes/event average
        }, indent=2))
        return 0

    if args.cmd == "emit":
        events_path = root / ".aios" / "primitives" / "events.jsonl"
        events_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            payload = {"raw": args.payload}
        payload["eventType"] = args.event_type
        record = {
            "schema_version": "aios.primitive_event.v1",
            "kind": "manual_event",
            "name": args.event_type,
            "ts_iso": now_iso(),
            "payload": payload,
        }
        with events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps({"ok": True, "emitted": record}, ensure_ascii=False, indent=2))
        return 0

    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
