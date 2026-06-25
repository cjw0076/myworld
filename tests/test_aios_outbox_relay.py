"""
tests/test_aios_outbox_relay.py — Transactional-outbox relay (W1) test suite.

Runs entirely on SQLite fixtures; no Lakebase credentials required.

Delivery contract being proven:
  AT-LEAST-ONCE: every pending row is eventually dispatched, even if the
    process crashes between dispatch_fn and the dispatched_at mark.
  IDEMPOTENT-CONSUMER: duplicate deliveries (e.g. after a crash-and-retry)
    are handled gracefully by the consumer (not by the relay itself).
  NO STARVATION: a failing row does not block subsequent rows.

Run:
  python3 -m pytest tests/test_aios_outbox_relay.py -q
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path

# Make scripts/ importable from the repo root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aios_outbox_relay import init_schema, open_fixture, relay_loop, relay_once  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with the fixture schema."""
    return open_fixture(":memory:")


def _insert_outbox(conn: sqlite3.Connection, topic: str, payload: dict, tenant_id: str = "t1") -> int:
    cur = conn.execute(
        "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
        (tenant_id, topic, json.dumps(payload)),
    )
    conn.commit()
    return cur.lastrowid


def _insert_event(conn: sqlite3.Connection, event_type: str, payload: dict, tenant_id: str = "t1") -> int:
    cur = conn.execute(
        "INSERT INTO events (tenant_id, event_type, payload) VALUES (?, ?, ?)",
        (tenant_id, event_type, json.dumps(payload)),
    )
    conn.commit()
    return cur.lastrowid


def _pending_count(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM outbox WHERE dispatched_at IS NULL"
    ).fetchone()[0]


def _dispatched_at(conn: sqlite3.Connection, row_id: int):
    return conn.execute(
        "SELECT dispatched_at FROM outbox WHERE id = ?", (row_id,)
    ).fetchone()[0]


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestOutboxRelayBasic(unittest.TestCase):
    """Committed event → pending row → dispatched exactly once."""

    def test_committed_event_creates_pending_row(self):
        conn = _make_db()
        _insert_event(conn, "memory.store", {"key": "k1"})
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 1})
        # Row must be pending before relay runs.
        self.assertEqual(_pending_count(conn), 1)
        self.assertIsNone(_dispatched_at(conn, row_id))

    def test_relay_once_dispatches_pending_row(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 42})

        calls: list[tuple[str, str]] = []
        relay_once(conn, lambda t, p: calls.append((t, p)))

        # dispatch_fn called exactly once.
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "graph.compile")
        self.assertEqual(json.loads(calls[0][1])["event_id"], 42)

    def test_relay_once_marks_dispatched_at(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "embed.request", {"event_id": 7})

        relay_once(conn, lambda t, p: None)

        self.assertIsNotNone(_dispatched_at(conn, row_id))
        # No pending rows remain.
        self.assertEqual(_pending_count(conn), 0)

    def test_relay_once_returns_dispatched_count(self):
        conn = _make_db()
        _insert_outbox(conn, "graph.compile", {"n": 1})
        _insert_outbox(conn, "graph.compile", {"n": 2})

        n = relay_once(conn, lambda t, p: None)
        self.assertEqual(n, 2)

    def test_already_dispatched_row_not_re_dispatched(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 1})
        # Mark as dispatched before relay runs.
        conn.execute(
            "UPDATE outbox SET dispatched_at = '2026-01-01T00:00:00Z' WHERE id = ?",
            (row_id,),
        )
        conn.commit()

        calls: list = []
        relay_once(conn, lambda t, p: calls.append((t, p)))

        self.assertEqual(len(calls), 0)


class TestOutboxRelayAtLeastOnce(unittest.TestCase):
    """AT-LEAST-ONCE: a dispatch_fn that throws leaves the row pending for retry."""

    def test_failing_dispatch_leaves_row_pending(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 1})

        def boom(topic: str, payload: str) -> None:
            raise RuntimeError("transient worker error")

        relay_once(conn, boom)

        # Row must still be pending.
        self.assertIsNone(_dispatched_at(conn, row_id))
        self.assertEqual(_pending_count(conn), 1)

    def test_retry_pass_dispatches_after_transient_failure(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 1})

        # First pass: dispatch_fn always raises.
        relay_once(conn, lambda t, p: (_ for _ in ()).throw(ValueError("down")))

        # Row still pending.
        self.assertEqual(_pending_count(conn), 1)

        # Second pass: dispatch_fn succeeds.
        calls: list = []
        relay_once(conn, lambda t, p: calls.append((t, p)))

        self.assertEqual(len(calls), 1)
        self.assertIsNone(_dispatched_at(conn, row_id) is None or None)  # dispatched now
        self.assertEqual(_pending_count(conn), 0)

    def test_relay_once_returns_zero_when_all_fail(self):
        conn = _make_db()
        _insert_outbox(conn, "topic.a", {"n": 1})
        _insert_outbox(conn, "topic.b", {"n": 2})

        n = relay_once(conn, lambda t, p: (_ for _ in ()).throw(IOError("fail")))
        self.assertEqual(n, 0)
        self.assertEqual(_pending_count(conn), 2)


class TestOutboxRelayCrashAndIdempotency(unittest.TestCase):
    """
    Crash-after-dispatch-before-mark scenario + consumer-idempotency proof.

    Simulates: dispatch_fn was called and the consumer recorded the delivery,
    but the process crashed before dispatched_at was written.  On the next
    relay pass the row is re-delivered.  A consumer that deduplicates by
    outbox row id (e.g. using a set) absorbs the second delivery as a no-op.
    """

    def test_crash_before_mark_causes_redelivery(self):
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 99})

        delivered: list[int] = []

        def consumer(topic: str, payload: str) -> None:
            delivered.append(row_id)

        # Simulate crash: consumer receives the message but dispatched_at is
        # never written (process killed between dispatch and UPDATE).
        consumer("graph.compile", json.dumps({"event_id": 99}))
        # dispatched_at NOT updated — row still pending in DB.
        self.assertEqual(_pending_count(conn), 1)
        self.assertEqual(len(delivered), 1)

        # Next relay pass re-delivers the same row.
        relay_once(conn, consumer)

        self.assertEqual(len(delivered), 2)  # second delivery
        self.assertEqual(_pending_count(conn), 0)  # now marked

    def test_consumer_idempotency_via_dedup_set(self):
        """
        Consumer uses a set keyed by row id; second delivery is a no-op.
        This proves the AT-LEAST-ONCE + IDEMPOTENT-CONSUMER contract.
        """
        conn = _make_db()
        row_id = _insert_outbox(conn, "graph.compile", {"event_id": 99})

        processed_ids: set[int] = set()
        side_effects: list[str] = []

        def idempotent_consumer(topic: str, payload: str) -> None:
            r_id = row_id  # closed over for this test
            if r_id in processed_ids:
                return  # second delivery: no-op
            processed_ids.add(r_id)
            side_effects.append(f"processed {r_id}")

        # First delivery (crash simulation — no mark written).
        idempotent_consumer("graph.compile", json.dumps({"event_id": 99}))
        self.assertIn(row_id, processed_ids)
        self.assertEqual(len(side_effects), 1)

        # Second delivery via relay (row still pending in DB).
        relay_once(conn, idempotent_consumer)

        # Side-effect executed exactly once despite two calls.
        self.assertEqual(len(side_effects), 1)
        # Row is now marked dispatched.
        self.assertEqual(_pending_count(conn), 0)


class TestOutboxRelayOrdering(unittest.TestCase):
    """
    Ordering: rows dispatched in insertion (id ASC) order.
    One failing row must not starve subsequent rows.
    """

    def test_rows_dispatched_in_insertion_order(self):
        conn = _make_db()
        ids_inserted = [
            _insert_outbox(conn, f"topic.{i}", {"seq": i}) for i in range(5)
        ]

        dispatch_order: list[int] = []

        def tracking_dispatch(topic: str, payload: str) -> None:
            dispatch_order.append(json.loads(payload)["seq"])

        relay_once(conn, tracking_dispatch)

        self.assertEqual(dispatch_order, list(range(5)))

    def test_failing_row_does_not_starve_later_rows(self):
        conn = _make_db()
        id_a = _insert_outbox(conn, "topic.a", {"n": 1})
        id_b = _insert_outbox(conn, "topic.b", {"n": 2})
        id_c = _insert_outbox(conn, "topic.c", {"n": 3})

        called_topics: list[str] = []

        def selective_dispatch(topic: str, payload: str) -> None:
            called_topics.append(topic)
            if topic == "topic.a":
                raise RuntimeError("topic.a worker down")

        relay_once(conn, selective_dispatch)

        # All three rows were attempted.
        self.assertIn("topic.a", called_topics)
        self.assertIn("topic.b", called_topics)
        self.assertIn("topic.c", called_topics)

        # Failing row (a) still pending; b and c dispatched.
        self.assertIsNone(_dispatched_at(conn, id_a))
        self.assertIsNotNone(_dispatched_at(conn, id_b))
        self.assertIsNotNone(_dispatched_at(conn, id_c))

        # One pending row remains (topic.a).
        self.assertEqual(_pending_count(conn), 1)

    def test_dispatch_order_respects_id_not_topic_alpha(self):
        """Even if topics sort differently, rows dispatch by insertion id."""
        conn = _make_db()
        _insert_outbox(conn, "zzz.first", {"seq": 0})
        _insert_outbox(conn, "aaa.second", {"seq": 1})

        order: list[str] = []
        relay_once(conn, lambda t, p: order.append(t))

        self.assertEqual(order, ["zzz.first", "aaa.second"])


class TestOutboxRelayLoop(unittest.TestCase):
    """relay_loop with max_iterations for bounded testing."""

    def test_relay_loop_max_iterations(self):
        conn = _make_db()
        _insert_outbox(conn, "graph.compile", {"event_id": 1})

        calls: list = []
        relay_loop(conn, lambda t, p: calls.append((t, p)), poll_interval=0, max_iterations=2)

        # Row dispatched; subsequent iteration finds nothing.
        self.assertEqual(len(calls), 1)
        self.assertEqual(_pending_count(conn), 0)

    def test_relay_loop_processes_rows_across_iterations(self):
        conn = _make_db()

        call_count = [0]
        iteration = [0]

        def dispatch_and_insert(topic: str, payload: str) -> None:
            call_count[0] += 1

        # Insert first row before loop, second row mid-loop via a side channel.
        _insert_outbox(conn, "topic.1", {"n": 1})

        # We'll use a patched relay_once to insert a new row on the first iteration.
        original_relay_once = relay_once

        insert_done = [False]

        def relay_once_with_hook(c, fn):
            result = original_relay_once(c, fn)
            if not insert_done[0]:
                _insert_outbox(c, "topic.2", {"n": 2})
                insert_done[0] = True
            return result

        import aios_outbox_relay
        orig = aios_outbox_relay.relay_once

        try:
            aios_outbox_relay.relay_once = relay_once_with_hook
            relay_loop(conn, dispatch_and_insert, poll_interval=0, max_iterations=3)
        finally:
            aios_outbox_relay.relay_once = orig

        # Both rows should have been dispatched across the two iterations.
        self.assertEqual(call_count[0], 2)
        self.assertEqual(_pending_count(conn), 0)


class TestOutboxRelaySchema(unittest.TestCase):
    """Schema initialisation and table structure."""

    def test_init_schema_idempotent(self):
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        # Second call must not raise (IF NOT EXISTS).
        init_schema(conn)

    def test_outbox_table_columns(self):
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(outbox)")}
        self.assertGreaterEqual(
            cols,
            {"id", "tenant_id", "topic", "payload", "created_at", "dispatched_at"},
        )

    def test_events_table_columns(self):
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        self.assertGreaterEqual(cols, {"id", "tenant_id", "event_type", "payload", "created_at"})


if __name__ == "__main__":
    unittest.main()
