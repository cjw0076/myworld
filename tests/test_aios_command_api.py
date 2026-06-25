"""
tests/test_aios_command_api.py — Command API (A1) test suite.

Runs entirely on SQLite fixtures; no Lakebase credentials required.

Contracts proven:

  ATOMICITY
    A write that fails mid-way (VersionConflict on UPDATE run_state — which
    happens after the events INSERT and before the outbox INSERT) leaves
    NO event, NO run_state change, NO outbox row — all-or-nothing.
    A successful write produces exactly one event row, one outbox row, and
    increments run_state.version by 1.

  OPTIMISTIC CONCURRENCY
    Two writes with the same expected_version: the second raises
    VersionConflict and writes nothing (version and counts unchanged).
    After reading the updated version and retrying, the write succeeds.

  TENANT ISOLATION
    Tenant A's write/read cannot touch tenant B's run_state or events.
    Writing with the wrong tenant_id raises VersionConflict (run not found).

  FULL SPINE (A1 -> W1 -> W2)
    write_command emits an outbox row;
    relay_once (W1) with make_consumer (W2) produces a draft claim.
    Running the relay twice produces no duplicate claims (relay idempotency).
    Simulating W1 at-least-once redelivery (reset dispatched_at) produces
    no extra claims (W2 INSERT OR IGNORE idempotency).

Run:
  python3 -m pytest tests/test_aios_command_api.py -q
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aios_command_api import (   # noqa: E402
    VersionConflict,
    open_fixture,
    read_run_state,
    write_command,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> sqlite3.Connection:
    """In-memory SQLite connection with A1 write-side schema."""
    return open_fixture(":memory:")


def _init_run(
    conn: sqlite3.Connection,
    tenant_id: str,
    run_id: str,
    version: int = 0,
) -> None:
    """Seed a run_state row so write_command can UPDATE it."""
    conn.execute(
        "INSERT INTO run_state (tenant_id, run_id, state, version) "
        "VALUES (?, ?, ?, ?)",
        (tenant_id, run_id, "created", version),
    )
    conn.commit()


def _event_count(conn: sqlite3.Connection, tenant_id: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM events WHERE tenant_id = ?", (tenant_id,)
    ).fetchone()[0]


def _outbox_pending(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM outbox WHERE dispatched_at IS NULL"
    ).fetchone()[0]


def _run_version(conn: sqlite3.Connection, tenant_id: str, run_id: str) -> int | None:
    row = conn.execute(
        "SELECT version FROM run_state WHERE tenant_id = ? AND run_id = ?",
        (tenant_id, run_id),
    ).fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# Atomicity
# ---------------------------------------------------------------------------


class TestAtomicity(unittest.TestCase):
    """All-or-nothing: a mid-write failure leaves zero state change."""

    def test_failed_write_leaves_no_event_no_outbox_no_version_change(self):
        """
        VersionConflict is raised after the events INSERT and before COMMIT.
        with conn: rolls back, so the events INSERT is also rolled back.
        The outbox INSERT is never reached.  run_state.version stays at 0.
        """
        conn = _make_db()
        _init_run(conn, "t1", "run1")   # version = 0

        with self.assertRaises(VersionConflict):
            write_command(
                conn,
                tenant_id="t1",
                run_id="run1",
                event_type="agent.started",
                payload={"key": "val"},
                expected_version=99,    # wrong: actual is 0
                topic="graph_compile",
            )

        self.assertEqual(_event_count(conn, "t1"), 0, "event INSERT must be rolled back")
        self.assertEqual(_outbox_pending(conn), 0, "outbox INSERT must not occur")
        self.assertEqual(_run_version(conn, "t1", "run1"), 0, "version must remain 0")

    def test_successful_write_produces_one_event_one_outbox_version_incremented(self):
        """Happy path: exactly one event, one outbox row, version bumped by 1."""
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        eid = write_command(
            conn,
            tenant_id="t1",
            run_id="run1",
            event_type="agent.started",
            payload={"step": 1},
            expected_version=0,
            topic="graph_compile",
        )

        self.assertIsInstance(eid, str, "write_command must return the event_id string")
        self.assertEqual(_event_count(conn, "t1"), 1)
        self.assertEqual(_outbox_pending(conn), 1)
        self.assertEqual(_run_version(conn, "t1", "run1"), 1)

    def test_sequential_writes_accumulate(self):
        """Each sequential write adds one event and one outbox row."""
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="agent.started", payload={},
            expected_version=0, topic="graph_compile",
        )
        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="agent.progressed", payload={},
            expected_version=1, topic="graph_compile",
        )

        self.assertEqual(_event_count(conn, "t1"), 2)
        self.assertEqual(_outbox_pending(conn), 2)
        self.assertEqual(_run_version(conn, "t1", "run1"), 2)

    def test_failed_write_does_not_block_subsequent_successful_write(self):
        """After a VersionConflict rollback, a correct write succeeds cleanly."""
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        with self.assertRaises(VersionConflict):
            write_command(
                conn, tenant_id="t1", run_id="run1",
                event_type="e1", payload={},
                expected_version=99, topic="graph_compile",
            )

        # Correct write must succeed; connection is in clean state after rollback.
        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )
        self.assertEqual(_event_count(conn, "t1"), 1)
        self.assertEqual(_run_version(conn, "t1", "run1"), 1)


# ---------------------------------------------------------------------------
# Optimistic concurrency
# ---------------------------------------------------------------------------


class TestOptimisticConcurrency(unittest.TestCase):
    """Two writers with the same expected_version: the second raises VersionConflict."""

    def test_second_write_same_version_raises_conflict_writes_nothing(self):
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        # First write succeeds: version 0 → 1.
        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="agent.started", payload={},
            expected_version=0, topic="graph_compile",
        )

        # Second write using stale expected_version=0 must conflict.
        with self.assertRaises(VersionConflict):
            write_command(
                conn, tenant_id="t1", run_id="run1",
                event_type="agent.started", payload={},
                expected_version=0,     # stale: current is 1
                topic="graph_compile",
            )

        # Only the first write's rows must exist.
        self.assertEqual(_event_count(conn, "t1"), 1)
        self.assertEqual(_run_version(conn, "t1", "run1"), 1)

    def test_conflict_leaves_no_extra_outbox_row(self):
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )
        outbox_before = _outbox_pending(conn)

        with self.assertRaises(VersionConflict):
            write_command(
                conn, tenant_id="t1", run_id="run1",
                event_type="e1", payload={},
                expected_version=0, topic="graph_compile",
            )

        self.assertEqual(
            _outbox_pending(conn), outbox_before,
            "version conflict must not add an outbox row",
        )

    def test_retry_with_correct_version_succeeds(self):
        """After VersionConflict, re-read version via read_run_state and retry."""
        conn = _make_db()
        _init_run(conn, "t1", "run1")

        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )

        with self.assertRaises(VersionConflict):
            write_command(
                conn, tenant_id="t1", run_id="run1",
                event_type="e2", payload={},
                expected_version=0, topic="graph_compile",
            )

        # CQRS read to get the current version.
        state = read_run_state(conn, "t1", "run1")
        self.assertIsNotNone(state)

        # Retry with current version succeeds.
        write_command(
            conn, tenant_id="t1", run_id="run1",
            event_type="e2", payload={},
            expected_version=state["version"], topic="graph_compile",
        )
        self.assertEqual(_run_version(conn, "t1", "run1"), 2)


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation(unittest.TestCase):
    """Tenant A's writes/reads cannot touch tenant B's state."""

    def test_write_is_scoped_to_tenant(self):
        conn = _make_db()
        _init_run(conn, "tenant-A", "run1")
        _init_run(conn, "tenant-B", "run1")

        write_command(
            conn, tenant_id="tenant-A", run_id="run1",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )

        # Tenant B's run must be untouched.
        self.assertEqual(_run_version(conn, "tenant-B", "run1"), 0)
        self.assertEqual(_event_count(conn, "tenant-B"), 0)

    def test_read_is_scoped_to_tenant(self):
        conn = _make_db()
        _init_run(conn, "tenant-A", "run1")
        _init_run(conn, "tenant-B", "run1")

        write_command(
            conn, tenant_id="tenant-A", run_id="run1",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )

        state_a = read_run_state(conn, "tenant-A", "run1")
        state_b = read_run_state(conn, "tenant-B", "run1")

        self.assertEqual(state_a["version"], 1)
        self.assertEqual(state_b["version"], 0, "tenant-B must not see tenant-A's write")

    def test_write_under_wrong_tenant_raises_version_conflict(self):
        """Attempting to write tenant-A's run under tenant-B raises VersionConflict."""
        conn = _make_db()
        _init_run(conn, "tenant-A", "run1")
        # No run_state for tenant-B; WHERE tenant_id='tenant-B' matches zero rows.

        with self.assertRaises(VersionConflict):
            write_command(
                conn, tenant_id="tenant-B", run_id="run1",
                event_type="e1", payload={},
                expected_version=0, topic="graph_compile",
            )

        # tenant-A's run_state must remain untouched.
        self.assertEqual(_run_version(conn, "tenant-A", "run1"), 0)

    def test_read_nonexistent_run_returns_none(self):
        conn = _make_db()
        result = read_run_state(conn, "no-such-tenant", "no-such-run")
        self.assertIsNone(result)

    def test_two_tenants_same_run_id_independent_versions(self):
        """Same run_id for two tenants tracks versions independently."""
        conn = _make_db()
        _init_run(conn, "t-alpha", "run-x")
        _init_run(conn, "t-beta", "run-x")

        write_command(
            conn, tenant_id="t-alpha", run_id="run-x",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )
        write_command(
            conn, tenant_id="t-alpha", run_id="run-x",
            event_type="e2", payload={},
            expected_version=1, topic="graph_compile",
        )
        write_command(
            conn, tenant_id="t-beta", run_id="run-x",
            event_type="e1", payload={},
            expected_version=0, topic="graph_compile",
        )

        self.assertEqual(_run_version(conn, "t-alpha", "run-x"), 2)
        self.assertEqual(_run_version(conn, "t-beta", "run-x"), 1)


# ---------------------------------------------------------------------------
# Full spine: A1 -> W1 -> W2
# ---------------------------------------------------------------------------


class TestFullSpine(unittest.TestCase):
    """
    write_command (A1) -> relay_once (W1) -> make_consumer (W2):
    one write emits a draft claim; relay idempotency holds end-to-end.
    """

    def setUp(self) -> None:
        from aios_graph_compiler import init_claims_schema, make_consumer  # noqa: PLC0415
        from aios_outbox_relay import relay_once                            # noqa: PLC0415

        self._make_consumer = make_consumer
        self._relay_once = relay_once

        self.conn = _make_db()
        init_claims_schema(self.conn)    # add W2 claims table to same connection
        _init_run(self.conn, "t1", "run1")

    def _claim_count(self, tenant_id: str = "t1") -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM claims WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0]

    def test_write_relay_produces_draft_claim(self):
        """A1 produces outbox row; W1 relay + W2 compiler write a draft claim."""
        write_command(
            self.conn,
            tenant_id="t1",
            run_id="run1",
            event_type="agent.completed",
            payload={"category": "aios", "source": "test"},
            expected_version=0,
            topic="graph_compile",
        )

        consumer = self._make_consumer(
            self.conn, compiler_name="stub", compiler_version="0.1"
        )
        n = self._relay_once(self.conn, consumer)

        self.assertEqual(n, 1, "relay must dispatch exactly one outbox row")
        self.assertGreater(self._claim_count(), 0, "W2 must write at least one draft claim")

    def test_all_claims_status_is_draft(self):
        """Draft-first invariant: every claim produced via the full spine is 'draft'."""
        write_command(
            self.conn,
            tenant_id="t1",
            run_id="run1",
            event_type="agent.completed",
            payload={"category": "aios", "tools": ["relay", "compiler"]},
            expected_version=0,
            topic="graph_compile",
        )
        consumer = self._make_consumer(
            self.conn, compiler_name="stub", compiler_version="0.1"
        )
        self._relay_once(self.conn, consumer)

        statuses = [
            row[0]
            for row in self.conn.execute(
                "SELECT status FROM claims WHERE tenant_id = 't1'"
            ).fetchall()
        ]
        self.assertTrue(statuses, "at least one claim must be written")
        self.assertTrue(
            all(s == "draft" for s in statuses),
            f"expected all 'draft', got: {set(statuses)}",
        )

    def test_relay_twice_no_duplicate_claims(self):
        """
        Relay idempotency across A1->W1->W2:
        running relay_once twice on the same outbox row produces no duplicate
        claims.  First pass dispatches and marks the row; second pass sees
        no pending rows (relay returns 0).
        """
        write_command(
            self.conn,
            tenant_id="t1",
            run_id="run1",
            event_type="agent.completed",
            payload={"category": "aios"},
            expected_version=0,
            topic="graph_compile",
        )
        consumer = self._make_consumer(
            self.conn, compiler_name="stub", compiler_version="0.1"
        )

        n1 = self._relay_once(self.conn, consumer)
        count1 = self._claim_count()

        n2 = self._relay_once(self.conn, consumer)
        count2 = self._claim_count()

        self.assertEqual(n1, 1, "first pass must dispatch one row")
        self.assertEqual(n2, 0, "second pass must dispatch zero rows (already marked)")
        self.assertEqual(count1, count2, "claim count must be unchanged after second pass")

    def test_at_least_once_redelivery_no_duplicate_claims(self):
        """
        End-to-end idempotency: simulate W1 crash-before-mark by resetting
        dispatched_at to NULL, then relay again.  W2's INSERT OR IGNORE
        absorbs the re-delivery as a no-op.
        """
        write_command(
            self.conn,
            tenant_id="t1",
            run_id="run1",
            event_type="agent.completed",
            payload={"category": "aios", "source": "redelivery-test"},
            expected_version=0,
            topic="graph_compile",
        )
        consumer = self._make_consumer(
            self.conn, compiler_name="stub", compiler_version="0.1"
        )

        # First relay pass: dispatch + mark.
        self._relay_once(self.conn, consumer)
        count1 = self._claim_count()
        self.assertGreater(count1, 0)

        # Simulate W1 crash-before-mark: clear dispatched_at so relay re-delivers.
        self.conn.execute("UPDATE outbox SET dispatched_at = NULL")
        self.conn.commit()

        # Second relay pass: re-delivers; W2 INSERT OR IGNORE absorbs the dup.
        self._relay_once(self.conn, consumer)
        count2 = self._claim_count()

        self.assertEqual(count1, count2, "at-least-once redelivery must not duplicate claims")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchema(unittest.TestCase):
    """Table structure and idempotent initialisation."""

    def test_init_schema_idempotent(self):
        from aios_command_api import init_schema  # noqa: PLC0415
        conn = sqlite3.connect(":memory:")
        init_schema(conn)
        init_schema(conn)   # second call must not raise

    def test_events_table_columns(self):
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        self.assertGreaterEqual(
            cols,
            {"id", "tenant_id", "event_id", "run_id", "seq", "type", "payload", "created_at"},
        )

    def test_run_state_table_columns(self):
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(run_state)")}
        self.assertGreaterEqual(
            cols,
            {"tenant_id", "run_id", "state", "version", "updated_at"},
        )

    def test_outbox_table_columns_aligned_with_relay(self):
        """Outbox shape must match aios_outbox_relay so relay_once can drain it."""
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(outbox)")}
        self.assertGreaterEqual(
            cols,
            {"id", "tenant_id", "topic", "payload", "created_at", "dispatched_at"},
        )


if __name__ == "__main__":
    unittest.main()
