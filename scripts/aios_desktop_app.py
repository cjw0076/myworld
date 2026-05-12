#!/usr/bin/env python3
"""Native desktop AIOS control app.

This is a non-web desktop surface built on Python's standard tkinter toolkit.
It reads the same control-plane snapshot used by the static app, but does not
start an HTTP server or open a browser.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_FOR_IMPORTS = Path(__file__).resolve().parents[1]
if str(ROOT_FOR_IMPORTS) not in sys.path:
    sys.path.insert(0, str(ROOT_FOR_IMPORTS))

from scripts.aios_control_snapshot import build_snapshot, write_json  # noqa: E402


SCHEMA_VERSION = "aios.desktop_app.v1"
SNAPSHOT_JSON = Path("apps/control/aios-control-snapshot.json")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_or_build_snapshot(root: Path, *, refresh: bool = False) -> dict[str, Any]:
    path = root / SNAPSHOT_JSON
    if not refresh and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    snapshot = build_snapshot(root)
    write_json(path, snapshot)
    return snapshot


def desktop_status(root: Path) -> dict[str, Any]:
    toolkit = tkinter_status()
    snapshot_path = root / SNAPSHOT_JSON
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "desktop": {
            "toolkit": "tkinter",
            "available": toolkit["available"],
            "display_available": toolkit["display_available"],
            "error": toolkit.get("error"),
        },
        "snapshot": {
            "exists": snapshot_path.exists(),
            "path": SNAPSHOT_JSON.as_posix(),
        },
        "mode": "native_desktop",
        "uses_http_server": False,
        "uses_browser": False,
    }


def tkinter_status() -> dict[str, Any]:
    try:
        import tkinter as tk  # noqa: F401
    except Exception as exc:  # pragma: no cover - platform dependent
        return {"available": False, "display_available": False, "error": str(exc)}
    try:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception as exc:
        return {"available": True, "display_available": False, "error": str(exc)}
    return {"available": True, "display_available": True}


def display_unavailable_message(error: Exception) -> str:
    return "\n".join(
        [
            "AIOS desktop launch failed: graphical display is not available.",
            f"detail: {error}",
            "Run launch from a graphical desktop session, or inspect headless state with:",
            "  python scripts/aios_desktop_app.py status --json",
            "  python scripts/aios_desktop_app.py snapshot --json",
        ]
    )


def view_model(snapshot: dict[str, Any]) -> dict[str, Any]:
    contracts = snapshot.get("contracts") or {}
    dispatches = snapshot.get("dispatches") or {}
    goals = snapshot.get("goals") or {}
    evolution = goals.get("evolution") or {}
    monitor = snapshot.get("monitor") or {}
    round_state = snapshot.get("round_controller") or {}
    repos = (snapshot.get("repos") or {}).get("items") or []
    return {
        "title": "AIOS Control",
        "generated_at": snapshot.get("generated_at"),
        "monitor_health": monitor.get("health") or "unknown",
        "next_action": first_next_action(snapshot),
        "goal": (goals.get("active") or {}).get("id") or "none",
        "recommendation": evolution.get("recommendation") or "none",
        "readiness": evolution.get("readiness") or "unknown",
        "round_running": bool(round_state.get("running")),
        "contract_counts": contracts.get("counts") or {},
        "dispatch_counts": dispatches.get("counts") or {},
        "latest_contracts": contracts.get("latest") or [],
        "latest_dispatches": dispatches.get("latest") or [],
        "repos": repos,
        "aios_inputs": snapshot.get("aios_inputs") or {},
        "stop_lanes": (snapshot.get("stop_lanes") or {}).get("items") or [],
    }


def first_next_action(snapshot: dict[str, Any]) -> str:
    actions = snapshot.get("next_actions") or []
    if not actions:
        return "none"
    first = actions[0]
    if not isinstance(first, dict):
        return str(first)
    return f"{first.get('owner', 'unknown')}: {first.get('action', 'unknown')} - {first.get('reason', '')}".strip()


def launch(root: Path, *, refresh: bool) -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception as exc:
        print(f"tkinter unavailable: {exc}", file=sys.stderr)
        return 2

    snapshot = load_or_build_snapshot(root, refresh=refresh)
    model = view_model(snapshot)
    try:
        app = tk.Tk()
    except tk.TclError as exc:
        print(display_unavailable_message(exc), file=sys.stderr)
        return 2
    app.title("AIOS Control")
    app.geometry("1180x760")
    app.minsize(920, 620)
    configure_style(ttk)

    state: dict[str, Any] = {"snapshot": snapshot, "model": model}
    build_layout(app, ttk, root, state)
    app.mainloop()
    return 0


def configure_style(ttk: Any) -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Header.TLabel", font=("TkDefaultFont", 14, "bold"))
    style.configure("Metric.TLabel", font=("TkDefaultFont", 11, "bold"))
    style.configure("Status.TLabel", padding=(6, 4))


def build_layout(app: Any, ttk: Any, root: Path, state: dict[str, Any]) -> None:
    shell = ttk.Frame(app, padding=12)
    shell.pack(fill="both", expand=True)

    header = ttk.Frame(shell)
    header.pack(fill="x")
    title = ttk.Label(header, text="AIOS Control", style="Header.TLabel")
    title.pack(side="left")
    status_var = state["status_var"] = make_string_var(app, "")
    ttk.Label(header, textvariable=status_var, style="Status.TLabel").pack(side="left", padx=16)
    ttk.Button(header, text="Refresh", command=lambda: refresh_gui(root, state)).pack(side="right")

    metrics = ttk.Frame(shell)
    metrics.pack(fill="x", pady=(12, 8))
    state["metric_vars"] = {}
    for key in ("monitor_health", "recommendation", "round_running", "next_action"):
        frame = ttk.Frame(metrics, padding=(0, 0, 18, 0))
        frame.pack(side="left", fill="x", expand=True)
        ttk.Label(frame, text=key.replace("_", " ").title(), style="Metric.TLabel").pack(anchor="w")
        var = make_string_var(app, "")
        state["metric_vars"][key] = var
        ttk.Label(frame, textvariable=var, wraplength=260).pack(anchor="w")

    notebook = ttk.Notebook(shell)
    notebook.pack(fill="both", expand=True)
    state["tables"] = {}
    for tab_name in ("Contracts", "Dispatches", "Repos", "Routes", "Stops"):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text=tab_name)
        state["tables"][tab_name] = frame

    render_all(ttk, state)


def make_string_var(app: Any, value: str) -> Any:
    import tkinter as tk

    return tk.StringVar(app, value=value)


def refresh_gui(root: Path, state: dict[str, Any]) -> None:
    state["snapshot"] = load_or_build_snapshot(root, refresh=True)
    state["model"] = view_model(state["snapshot"])
    render_all(None, state)


def render_all(ttk_module: Any, state: dict[str, Any]) -> None:
    model = state["model"]
    state["status_var"].set(f"Generated {model.get('generated_at')}")
    for key, var in state["metric_vars"].items():
        var.set(str(model.get(key)))
    ttk = ttk_module or __import__("tkinter.ttk", fromlist=["ttk"])
    render_table(ttk, state["tables"]["Contracts"], ["id", "status", "slug", "goal"], model["latest_contracts"])
    render_table(ttk, state["tables"]["Dispatches"], ["dispatch_id", "status", "contract_id", "reason"], model["latest_dispatches"])
    render_table(ttk, state["tables"]["Repos"], ["repo", "dirty", "inbox_count", "outbox_count", "goal_count", "route_count"], model["repos"])
    routes = route_rows(model.get("aios_inputs") or {})
    render_table(ttk, state["tables"]["Routes"], ["kind", "value"], routes)
    render_table(ttk, state["tables"]["Stops"], ["name", "contracts"], model["stop_lanes"])


def route_rows(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, values in inputs.items():
        for value in values or []:
            rows.append({"kind": key, "value": value})
    return rows


def render_table(ttk: Any, parent: Any, columns: list[str], rows: list[dict[str, Any]]) -> None:
    for child in parent.winfo_children():
        child.destroy()
    tree = ttk.Treeview(parent, columns=columns, show="headings")
    yscroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
    for column in columns:
        tree.heading(column, text=column.replace("_", " ").title())
        width = 140 if column not in {"goal", "reason", "contracts", "value", "name"} else 360
        tree.column(column, width=width, minwidth=90, stretch=True)
    for row in rows:
        tree.insert("", "end", values=[format_cell(row.get(column)) for column in columns])
    tree.grid(row=0, column=0, sticky="nsew")
    yscroll.grid(row=0, column=1, sticky="ns")
    xscroll.grid(row=1, column=0, sticky="ew")
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)


def format_cell(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    payload = desktop_status(root)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"desktop_available={payload['desktop']['available']} display={payload['desktop']['display_available']}")
        print(f"snapshot={payload['snapshot']['path']} exists={payload['snapshot']['exists']}")
    return 0


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    snapshot = load_or_build_snapshot(root, refresh=args.refresh)
    model = view_model(snapshot)
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "view_model": model}, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"monitor={model['monitor_health']} recommendation={model['recommendation']}")
    return 0


def cmd_launch(args: argparse.Namespace) -> int:
    return launch(Path(args.root).resolve(), refresh=not args.no_refresh)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native desktop AIOS control app")
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="cmd", required=True)
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--refresh", action="store_true")
    snapshot.add_argument("--json", action="store_true")
    snapshot.set_defaults(func=cmd_snapshot)
    launch_cmd = sub.add_parser("launch")
    launch_cmd.add_argument("--no-refresh", action="store_true")
    launch_cmd.set_defaults(func=cmd_launch)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
