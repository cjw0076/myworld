"""Tests for AIOS primitive surface (ASC-0050)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add scripts/ so we can import aios_primitives as a package.
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from aios_primitives import events, monitor, schedule, task, ask, tools, web  # noqa: E402


class _RootCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self) -> None:
        os.chdir(self.cwd)
        self.tmp.cleanup()


class EventLogTests(_RootCase):
    def test_emit_and_read(self):
        events.emit("task.created", "t-abc", {"subject": "x"}, root=self.root)
        events.emit("monitor.started", "m1", {"pid": 1234}, root=self.root)
        recs = events.read_events(root=self.root)
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["kind"], "task.created")
        self.assertEqual(recs[1]["kind"], "monitor.started")
        self.assertTrue(all("ts_iso" in r and "ts_monotonic_ns" in r for r in recs))

    def test_read_filters(self):
        events.emit("task.created", "t-1", {}, root=self.root)
        events.emit("task.status", "t-1", {"to": "completed"}, root=self.root)
        events.emit("task.created", "t-2", {}, root=self.root)
        by_name = events.read_events(name="t-1", root=self.root)
        self.assertEqual(len(by_name), 2)
        by_kind = events.read_events(kind="task.created", root=self.root)
        self.assertEqual(len(by_kind), 2)

    def test_read_tolerates_partial_line(self):
        path = events.events_path(self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"kind":"a","name":"x"}\n{"kind":"b","na', encoding="utf-8")
        recs = events.read_events(root=self.root)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["kind"], "a")


class TaskTests(_RootCase):
    def test_lifecycle(self):
        t = task.create("write tests", "for ASC-0050", owner="claude", root=self.root)
        self.assertEqual(t["status"], "pending")
        tid = t["id"]
        t2 = task.update(tid, status="in_progress", root=self.root)
        self.assertEqual(t2["status"], "in_progress")
        t3 = task.update(tid, status="completed", root=self.root)
        self.assertEqual(t3["status"], "completed")
        got = task.get(tid, root=self.root)
        self.assertEqual(got["status"], "completed")

    def test_invalid_status_rejected(self):
        t = task.create("x", root=self.root)
        r = task.update(t["id"], status="bogus", root=self.root)
        self.assertFalse(r.get("updated", True))

    def test_list_filter(self):
        a = task.create("a", root=self.root)
        b = task.create("b", root=self.root)
        task.update(a["id"], status="completed", root=self.root)
        completed = task.list_tasks(status="completed", root=self.root)
        self.assertEqual(len(completed), 1)
        all_tasks = task.list_tasks(root=self.root)
        self.assertEqual(len(all_tasks), 2)

    def test_events_emitted(self):
        t = task.create("x", root=self.root)
        task.update(t["id"], status="in_progress", root=self.root)
        recs = events.read_events(name=t["id"], root=self.root)
        kinds = [r["kind"] for r in recs]
        self.assertIn("task.created", kinds)
        self.assertIn("task.status", kinds)


class AskTests(_RootCase):
    def test_create_and_answer(self):
        q = ask.create("OK to release?", options=["yes", "no"], to="operator", root=self.root)
        self.assertEqual(q["status"], "open")
        r = ask.answer(q["id"], "yes", answered_by="claude", root=self.root)
        self.assertEqual(r["status"], "answered")
        self.assertEqual(r["answer"], "yes")

    def test_wait_returns_when_answered(self):
        q = ask.create("ready?", root=self.root)
        ask.answer(q["id"], "yes", root=self.root)
        state = ask.wait(q["id"], timeout_seconds=2, poll_interval=1, root=self.root)
        self.assertEqual(state["status"], "answered")

    def test_wait_timeout(self):
        q = ask.create("never answered", root=self.root)
        state = ask.wait(q["id"], timeout_seconds=1, poll_interval=1, root=self.root)
        self.assertEqual(state["status"], "timeout")


class ToolsTests(_RootCase):
    def test_register_and_discover_local(self):
        tools.register(
            {
                "id": "tool.demo",
                "name": "Demo Tool",
                "description": "for searching demo capabilities",
                "tags": ["demo", "search"],
            },
            root=self.root,
        )
        r = tools.discover("demo capability", root=self.root)
        ids = [e["id"] for e in r["local_registry"]]
        self.assertIn("tool.demo", ids)

    def test_discover_no_match(self):
        r = tools.discover("nothing-here", root=self.root)
        self.assertEqual(r["local_registry"], [])


class WebTests(_RootCase):
    def test_fetch_requires_claims(self):
        with self.assertRaises(ValueError):
            web.fetch("https://example.com", claims=[], root=self.root)

    def test_fetch_writes_receipt(self):
        r = web.fetch(
            "https://example.com/docs",
            claims=["example claim 1", "example claim 2"],
            publisher="Example",
            root=self.root,
        )
        self.assertEqual(r["schema_version"], "aios.web_research_receipt.v1")
        self.assertEqual(r["capability_route"], "capabilityos.web_research_route.v1")
        path = Path(r["path"])
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["url"], "https://example.com/docs")

    def test_search_requires_sources(self):
        with self.assertRaises(ValueError):
            web.search("q", sources=[], root=self.root)


class MonitorTests(_RootCase):
    def test_start_list_stop(self):
        m = monitor.start("test-mon", "for i in 1 2 3; do echo tick-$i; sleep 0.1; done", root=self.root)
        self.assertTrue(m["pid"] > 0)
        # Wait briefly for at least one event to land.
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            recs = events.read_events(name="test-mon", kind="monitor.event", root=self.root)
            if len(recs) >= 1:
                break
            time.sleep(0.2)
        recs = events.read_events(name="test-mon", kind="monitor.event", root=self.root)
        self.assertGreaterEqual(len(recs), 1)
        ms = monitor.list_monitors(root=self.root)
        names = [m["name"] for m in ms]
        self.assertIn("test-mon", names)
        # Stop returns success even after self-exit.
        stop_result = monitor.stop("test-mon", root=self.root)
        self.assertTrue(stop_result.get("stopped"))

    def test_start_idempotent(self):
        a = monitor.start("idem", "sleep 30", root=self.root)
        try:
            b = monitor.start("idem", "sleep 30", root=self.root)
            self.assertEqual(a["pid"], b.get("pid"))
            self.assertTrue(b.get("already_running"))
        finally:
            monitor.stop("idem", root=self.root)


class ScheduleTests(_RootCase):
    def test_once_fires(self):
        dispatch = self.root / "fake-packet.json"
        dispatch.write_text("{}", encoding="utf-8")
        s = schedule.once("sched-once", delay_seconds=1, dispatch=dispatch.as_posix(), root=self.root)
        self.assertEqual(s["kind"], "once")
        # Wait for fire event.
        deadline = time.monotonic() + 8
        fired = False
        while time.monotonic() < deadline:
            recs = events.read_events(name="sched-once", kind="schedule.fired", root=self.root)
            if recs:
                fired = True
                break
            time.sleep(0.5)
        self.assertTrue(fired, "schedule.once did not fire within 8 seconds")


class CliShimTests(_RootCase):
    def test_module_import(self):
        # Ensure the package can be imported and exposes the main entry.
        from aios_primitives.__main__ import build_parser
        p = build_parser()
        # monitor start subcommand should exist.
        args = p.parse_args(["monitor", "start", "--name", "x", "--command", "echo y"])
        self.assertEqual(args.kind, "monitor")
        self.assertEqual(args.op, "start")
        self.assertEqual(args.name, "x")


if __name__ == "__main__":
    unittest.main()
