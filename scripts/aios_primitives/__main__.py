"""CLI dispatcher for aios_primitives.

Usage:
  python -m aios_primitives monitor start --name foo --command "..."
  python -m aios_primitives task create --subject ... --description ...
  python -m aios_primitives schedule once --delay-seconds 60 --dispatch packet.json
  python -m aios_primitives ask --question ... --options A,B,C
  python -m aios_primitives tools discover --query "..."
  python -m aios_primitives web fetch --url ... --claim "..." --claim "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import events as ev_mod
from . import monitor as monitor_mod
from . import schedule as schedule_mod
from . import task as task_mod
from . import ask as ask_mod
from . import tools as tools_mod
from . import web as web_mod


def _print(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aios_primitives")
    p.add_argument("--root", type=Path, default=None, help="Override root dir (defaults to cwd)")
    sub = p.add_subparsers(dest="kind", required=True)

    # monitor
    m = sub.add_parser("monitor")
    msub = m.add_subparsers(dest="op", required=True)
    ms = msub.add_parser("start")
    ms.add_argument("--name", required=True)
    ms.add_argument("--command", required=True)
    msub.add_parser("list")
    mg = msub.add_parser("get"); mg.add_argument("--name", required=True)
    mt = msub.add_parser("stop"); mt.add_argument("--name", required=True)

    # schedule
    s = sub.add_parser("schedule")
    ssub = s.add_subparsers(dest="op", required=True)
    so = ssub.add_parser("once")
    so.add_argument("--name", required=True)
    so.add_argument("--delay-seconds", type=int, required=True)
    so.add_argument("--dispatch", required=True)
    sr = ssub.add_parser("repeat")
    sr.add_argument("--name", required=True)
    sr.add_argument("--interval-seconds", type=int, required=True)
    sr.add_argument("--initial-delay", type=int, default=0)
    sr.add_argument("--dispatch", required=True)
    ssub.add_parser("list")
    st = ssub.add_parser("stop"); st.add_argument("--name", required=True)

    # task
    t = sub.add_parser("task")
    tsub = t.add_subparsers(dest="op", required=True)
    tc = tsub.add_parser("create")
    tc.add_argument("--subject", required=True)
    tc.add_argument("--description", default="")
    tc.add_argument("--owner", default=None)
    tu = tsub.add_parser("update")
    tu.add_argument("--id", required=True)
    tu.add_argument("--status", default=None)
    tu.add_argument("--subject", default=None)
    tu.add_argument("--description", default=None)
    tu.add_argument("--owner", default=None)
    tl = tsub.add_parser("list")
    tl.add_argument("--status", default=None)
    tg = tsub.add_parser("get"); tg.add_argument("--id", required=True)

    # ask
    a = sub.add_parser("ask")
    asub = a.add_subparsers(dest="op", required=True)
    ac = asub.add_parser("create")
    ac.add_argument("--question", required=True)
    ac.add_argument("--options", default="")
    ac.add_argument("--to", default="operator")
    ac.add_argument("--from-agent", default=None)
    ac.add_argument("--multi-select", action="store_true")
    aa = asub.add_parser("answer")
    aa.add_argument("--id", required=True)
    aa.add_argument("--answer", required=True)
    aa.add_argument("--answered-by", default=None)
    aw = asub.add_parser("wait")
    aw.add_argument("--id", required=True)
    aw.add_argument("--timeout-seconds", type=int, default=ask_mod.DEFAULT_TIMEOUT_SECONDS)
    aw.add_argument("--poll-interval", type=int, default=ask_mod.DEFAULT_POLL_INTERVAL_SECONDS)
    al = asub.add_parser("list"); al.add_argument("--status", default=None)
    ag = asub.add_parser("get"); ag.add_argument("--id", required=True)

    # tools
    to = sub.add_parser("tools")
    tosub = to.add_subparsers(dest="op", required=True)
    td = tosub.add_parser("discover")
    td.add_argument("--query", required=True)
    td.add_argument("--max-results", type=int, default=5)
    tr = tosub.add_parser("register")
    tr.add_argument("--id", required=True)
    tr.add_argument("--name", required=True)
    tr.add_argument("--description", default="")
    tr.add_argument("--tags", default="")

    # web
    w = sub.add_parser("web")
    wsub = w.add_subparsers(dest="op", required=True)
    wf = wsub.add_parser("fetch")
    wf.add_argument("--url", required=True)
    wf.add_argument("--claim", action="append", required=True)
    wf.add_argument("--publisher", default=None)
    wf.add_argument("--accessed-at", default=None)
    wf.add_argument("--source-type", default="documentation")
    wf.add_argument("--source-date", default=None)
    wf.add_argument("--record", default=None)
    ws = wsub.add_parser("search")
    ws.add_argument("--query", required=True)
    ws.add_argument("--sources-json", required=True, help="JSON file path with sources array")
    ws.add_argument("--record", default=None)

    # events
    e = sub.add_parser("events")
    e.add_argument("--name", default=None)
    e.add_argument("--event-kind", dest="event_kind", default=None,
                   help="Filter events by kind (e.g. task.created, monitor.event)")
    e.add_argument("--limit", type=int, default=50)

    # stop (generic) — use --target-kind to avoid shadowing top-level kind.
    sp = sub.add_parser("stop")
    sp.add_argument("--target-kind", dest="target_kind",
                    choices=["monitor", "schedule"], required=True)
    sp.add_argument("--name", required=True)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root

    if args.kind == "monitor":
        if args.op == "start":
            _print(monitor_mod.start(args.name, args.command, root))
        elif args.op == "list":
            _print(monitor_mod.list_monitors(root))
        elif args.op == "get":
            _print(monitor_mod.get(args.name, root) or {})
        elif args.op == "stop":
            _print(monitor_mod.stop(args.name, root))
    elif args.kind == "schedule":
        if args.op == "once":
            _print(schedule_mod.once(args.name, args.delay_seconds, args.dispatch, root))
        elif args.op == "repeat":
            _print(schedule_mod.repeat(args.name, args.interval_seconds, args.dispatch, args.initial_delay, root))
        elif args.op == "list":
            _print(schedule_mod.list_schedules(root))
        elif args.op == "stop":
            _print(schedule_mod.stop(args.name, root))
    elif args.kind == "task":
        if args.op == "create":
            _print(task_mod.create(args.subject, args.description, args.owner, root))
        elif args.op == "update":
            _print(task_mod.update(args.id, args.status, args.subject, args.description, args.owner, root))
        elif args.op == "list":
            _print(task_mod.list_tasks(args.status, root))
        elif args.op == "get":
            _print(task_mod.get(args.id, root) or {})
    elif args.kind == "ask":
        if args.op == "create":
            opts = [o.strip() for o in (args.options or "").split(",") if o.strip()]
            _print(ask_mod.create(args.question, opts, args.to, args.from_agent, args.multi_select, root))
        elif args.op == "answer":
            _print(ask_mod.answer(args.id, args.answer, args.answered_by, root))
        elif args.op == "wait":
            state = ask_mod.wait(args.id, args.timeout_seconds, args.poll_interval, root)
            _print(state)
            if state.get("status") == "timeout":
                return ask_mod.TIMEOUT_EXIT_CODE
        elif args.op == "list":
            _print(ask_mod.list_questions(args.status, root))
        elif args.op == "get":
            _print(ask_mod.get(args.id, root) or {})
    elif args.kind == "tools":
        if args.op == "discover":
            _print(tools_mod.discover(args.query, args.max_results, root))
        elif args.op == "register":
            tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
            _print(tools_mod.register({"id": args.id, "name": args.name, "description": args.description, "tags": tags}, root))
    elif args.kind == "web":
        if args.op == "fetch":
            _print(web_mod.fetch(args.url, args.claim, args.publisher, args.accessed_at, args.source_type, args.source_date, args.record, root))
        elif args.op == "search":
            sources = json.loads(Path(args.sources_json).read_text(encoding="utf-8"))
            _print(web_mod.search(args.query, sources, args.record, root))
    elif args.kind == "events":
        recs = ev_mod.read_events(args.name, args.event_kind, root)
        _print(recs[-args.limit:])
    elif args.kind == "stop":
        # The generic 'stop' subcommand uses a separate `--kind` argument;
        # rename via `args.target_kind` access via getattr to avoid shadowing.
        target = getattr(args, "kind", None)
        # argparse stored both — the top-level kind is "stop" here, so we
        # need a fresh attribute. Re-read from the namespace:
        target_kind = args.__dict__.get("target_kind") or args.__dict__.get("kind_arg")
        # Fallback: the original parser used `--kind` which shadowed; we now
        # require the user to pass it as the second positional via subparser.
        if target_kind == "monitor":
            _print(monitor_mod.stop(args.name, root))
        elif target_kind == "schedule":
            _print(schedule_mod.stop(args.name, root))
        else:
            _print({"stopped": False, "reason": "use 'monitor stop' or 'schedule stop' instead"})
    return 0


if __name__ == "__main__":
    sys.exit(main())
