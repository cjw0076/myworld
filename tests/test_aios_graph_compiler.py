"""
tests/test_aios_graph_compiler.py — Graph Compiler (W2) test suite.

Runs entirely on SQLite fixtures; no Lakebase credentials required.

Contracts being proven:

  IDEMPOTENCY
    Same event compiled twice → claims written exactly once.
    The UNIQUE(tenant_id, source_event_id, compiler_name, compiler_version,
    predicate) key + INSERT OR IGNORE is the mechanism.

  W1→W2 SEAM
    aios_outbox_relay.relay_once feeds a graph_compile outbox row to
    make_consumer.  Claims appear after the first pass.  Simulating
    at-least-once redelivery (reset dispatched_at to NULL, relay again)
    produces zero additional claims.

  MALFORMED-DROP
    A malformed event is dropped with a log warning; no claim is written,
    no exception escapes, and other events in the batch are unaffected.

  DRAFT-FIRST
    Every written claim has status='draft' (never auto-accepted).

Run:
  python3 -m pytest tests/test_aios_graph_compiler.py -q
"""

import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from aios_graph_compiler import (  # noqa: E402
    compile_event,
    extract_claims,
    init_claims_schema,
    make_consumer,
    open_fixture,
)
from aios_outbox_relay import relay_once  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db() -> sqlite3.Connection:
    """In-memory DB with W1 (outbox/events) + W2 (claims) schemas."""
    return open_fixture(":memory:")


def _claim_count(conn: sqlite3.Connection, tenant_id: str = "t1") -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM claims WHERE tenant_id = ?", (tenant_id,)
    ).fetchone()[0]


def _insert_outbox(
    conn: sqlite3.Connection,
    topic: str,
    payload: dict,
    tenant_id: str = "t1",
) -> int:
    cur = conn.execute(
        "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
        (tenant_id, topic, json.dumps(payload)),
    )
    conn.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency(unittest.TestCase):
    """Same event compiled twice writes claims only once."""

    def test_same_event_twice_writes_once(self):
        conn = _make_db()
        event = {
            "tenant_id": "t1",
            "event_id": "evt-001",
            "payload": {"category": "aios"},
        }

        n1 = compile_event(conn, event, compiler_name="stub", compiler_version="0.1")
        n2 = compile_event(conn, event, compiler_name="stub", compiler_version="0.1")

        self.assertGreater(n1, 0, "first compile must write at least one claim")
        self.assertEqual(n2, 0, "second compile must return 0 (all claims already exist)")
        self.assertEqual(_claim_count(conn), n1, "DB must hold exactly n1 claims, not 2×n1")

    def test_different_event_ids_are_independent(self):
        conn = _make_db()
        ev_a = {"tenant_id": "t1", "event_id": "evt-A", "payload": {"category": "x"}}
        ev_b = {"tenant_id": "t1", "event_id": "evt-B", "payload": {"category": "x"}}

        n_a = compile_event(conn, ev_a, compiler_name="stub", compiler_version="0.1")
        n_b = compile_event(conn, ev_b, compiler_name="stub", compiler_version="0.1")

        self.assertGreater(n_a, 0)
        self.assertGreater(n_b, 0)
        # Both events produce claims; same predicate but different source_event_id
        # → no collision.
        self.assertEqual(_claim_count(conn), n_a + n_b)

    def test_different_compiler_versions_are_independent(self):
        conn = _make_db()
        event = {"tenant_id": "t1", "event_id": "evt-ver", "payload": {"category": "x"}}

        n1 = compile_event(conn, event, compiler_name="stub", compiler_version="0.1")
        n2 = compile_event(conn, event, compiler_name="stub", compiler_version="0.2")

        self.assertGreater(n1, 0)
        self.assertGreater(n2, 0)
        self.assertEqual(_claim_count(conn), n1 + n2)


# ---------------------------------------------------------------------------
# W1→W2 seam
# ---------------------------------------------------------------------------

class TestW1W2Seam(unittest.TestCase):
    """
    relay_once (W1) → make_consumer (W2): end-to-end pipe.

    At-least-once redelivery from W1 must produce no duplicate claims in W2.
    """

    def test_relay_feeds_compiler(self):
        conn = _make_db()
        event = {
            "tenant_id": "t1",
            "event_id": "evt-seam-1",
            "payload": {"category": "relay-test"},
        }
        _insert_outbox(conn, "graph_compile", event)

        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        dispatched = relay_once(conn, consumer)

        self.assertEqual(dispatched, 1, "relay must dispatch exactly one outbox row")
        self.assertGreater(_claim_count(conn), 0, "compiler must have written at least one claim")

    def test_at_least_once_redelivery_no_duplicate_claims(self):
        """
        Simulate W1 crash-before-mark: reset dispatched_at to NULL so the
        relay re-delivers the same event.  The UNIQUE key + INSERT OR IGNORE
        in compile_event must absorb the second delivery as a no-op.
        """
        conn = _make_db()
        event = {
            "tenant_id": "t1",
            "event_id": "evt-seam-2",
            "payload": {"category": "dedup-test", "tools": ["mcp"]},
        }
        row_id = _insert_outbox(conn, "graph_compile", event)
        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")

        # First relay pass: dispatch succeeds, outbox row marked dispatched.
        relay_once(conn, consumer)
        count_after_first = _claim_count(conn)
        self.assertGreater(count_after_first, 0, "first pass must produce claims")

        # Simulate at-least-once redelivery: clear dispatched_at so the relay
        # treats this row as pending again.
        conn.execute(
            "UPDATE outbox SET dispatched_at = NULL WHERE id = ?", (row_id,)
        )
        conn.commit()

        # Second relay pass: re-delivers the SAME event to the compiler.
        relay_once(conn, consumer)
        count_after_second = _claim_count(conn)

        self.assertEqual(
            count_after_second,
            count_after_first,
            "re-delivery must not create duplicate claims",
        )

    def test_relay_ignores_other_topics(self):
        """Consumer silently ignores outbox rows with topic != 'graph_compile'."""
        conn = _make_db()
        event = {"tenant_id": "t1", "event_id": "evt-other", "payload": {}}
        _insert_outbox(conn, "embed.request", event)  # different topic

        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        relay_once(conn, consumer)

        self.assertEqual(_claim_count(conn), 0, "non-graph_compile topics must not produce claims")


# ---------------------------------------------------------------------------
# Malformed event handling
# ---------------------------------------------------------------------------

class TestMalformedDrop(unittest.TestCase):
    """Malformed events are dropped; no crash; other events are unaffected."""

    def test_missing_tenant_id_drops_silently(self):
        conn = _make_db()
        bad = {"event_id": "x", "payload": {}}  # no tenant_id
        n = compile_event(conn, bad, compiler_name="stub", compiler_version="0.1")
        self.assertEqual(n, 0)
        self.assertEqual(_claim_count(conn), 0)

    def test_missing_event_id_drops_silently(self):
        conn = _make_db()
        bad = {"tenant_id": "t1", "payload": {}}  # no event_id
        n = compile_event(conn, bad, compiler_name="stub", compiler_version="0.1")
        self.assertEqual(n, 0)

    def test_non_dict_event_drops_silently(self):
        conn = _make_db()
        for bad in ("string", 42, None, [1, 2]):
            with self.subTest(event=bad):
                n = compile_event(conn, bad, compiler_name="stub", compiler_version="0.1")
                self.assertEqual(n, 0)
        self.assertEqual(_claim_count(conn), 0)

    def test_malformed_does_not_block_good_event(self):
        """A bad event before a good one must not prevent the good one from compiling."""
        conn = _make_db()

        # Malformed first
        n_bad = compile_event(
            conn, {"payload": {}}, compiler_name="stub", compiler_version="0.1"
        )
        self.assertEqual(n_bad, 0)

        # Good event after
        good = {"tenant_id": "t1", "event_id": "evt-good", "payload": {"category": "ok"}}
        n_good = compile_event(conn, good, compiler_name="stub", compiler_version="0.1")
        self.assertGreater(n_good, 0)

    def test_malformed_json_in_outbox_no_crash(self):
        """Malformed JSON payload in outbox row → consumer logs and continues."""
        conn = _make_db()
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("t1", "graph_compile", "NOT-JSON{{"),
        )
        conn.commit()

        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        # Must not raise.
        dispatched = relay_once(conn, consumer)
        # Relay marks the row dispatched (consumer did not raise).
        self.assertEqual(dispatched, 1)
        # But no claims were written.
        self.assertEqual(_claim_count(conn), 0)

    def test_malformed_row_does_not_block_valid_row(self):
        """Malformed outbox row followed by a valid one: both are processed."""
        conn = _make_db()
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("t1", "graph_compile", "BADJSON"),
        )
        good_event = {
            "tenant_id": "t1",
            "event_id": "evt-after-bad",
            "payload": {"category": "good"},
        }
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("t1", "graph_compile", json.dumps(good_event)),
        )
        conn.commit()

        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        relay_once(conn, consumer)

        self.assertGreater(_claim_count(conn), 0, "valid row after bad row must produce claims")


# ---------------------------------------------------------------------------
# Draft-first invariant
# ---------------------------------------------------------------------------

class TestDraftFirst(unittest.TestCase):
    """Every written claim has status='draft' (never auto-accepted)."""

    def test_single_event_claims_are_draft(self):
        conn = _make_db()
        event = {
            "tenant_id": "t1",
            "event_id": "evt-draft",
            "payload": {"category": "aios", "source": "test", "tools": ["mcp"]},
        }
        compile_event(conn, event, compiler_name="stub", compiler_version="0.1")

        statuses = [
            row[0]
            for row in conn.execute(
                "SELECT status FROM claims WHERE tenant_id = 't1'"
            ).fetchall()
        ]
        self.assertTrue(statuses, "at least one claim must be written")
        self.assertTrue(
            all(s == "draft" for s in statuses),
            f"expected all 'draft', got: {set(statuses)}",
        )

    def test_via_relay_claims_are_draft(self):
        conn = _make_db()
        event = {
            "tenant_id": "t1",
            "event_id": "evt-draft-relay",
            "payload": {"event_type": "memory.store"},
        }
        _insert_outbox(conn, "graph_compile", event)
        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        relay_once(conn, consumer)

        statuses = [
            row[0]
            for row in conn.execute(
                "SELECT status FROM claims WHERE tenant_id = 't1'"
            ).fetchall()
        ]
        self.assertTrue(statuses)
        self.assertTrue(all(s == "draft" for s in statuses))


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TestClaimsSchema(unittest.TestCase):
    """Schema initialisation and column shape."""

    def test_init_claims_schema_idempotent(self):
        conn = sqlite3.connect(":memory:")
        init_claims_schema(conn)
        init_claims_schema(conn)  # second call must not raise

    def test_claims_table_columns(self):
        conn = _make_db()
        cols = {row[1] for row in conn.execute("PRAGMA table_info(claims)")}
        self.assertGreaterEqual(
            cols,
            {
                "id", "tenant_id", "source_event_id", "compiler_name",
                "compiler_version", "subject", "predicate", "object",
                "confidence", "status", "created_at",
            },
        )

    def test_unique_constraint_enforced(self):
        """Direct INSERT of a duplicate claim row raises IntegrityError."""
        conn = _make_db()
        row = ("t1", "ev1", "stub", "0.1", "event:ev1", "has_category", "x", 1.0)
        conn.execute(
            "INSERT INTO claims (tenant_id, source_event_id, compiler_name, "
            "compiler_version, subject, predicate, object, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            row,
        )
        conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO claims (tenant_id, source_event_id, compiler_name, "
                "compiler_version, subject, predicate, object, confidence) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                row,
            )


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------

class TestExtractClaims(unittest.TestCase):
    """extract_claims stub: deterministic, pure, structural."""

    def test_category_field(self):
        event = {"event_id": "e1", "payload": {"category": "aios"}}
        claims = extract_claims(event)
        predicates = {c["predicate"] for c in claims}
        self.assertIn("has_category", predicates)
        cat_claim = next(c for c in claims if c["predicate"] == "has_category")
        self.assertEqual(cat_claim["object"], "aios")

    def test_tools_field(self):
        event = {"event_id": "e2", "payload": {"tools": ["mcp", "relay"]}}
        claims = extract_claims(event)
        predicates = {c["predicate"] for c in claims}
        self.assertIn("uses_tool:mcp", predicates)
        self.assertIn("uses_tool:relay", predicates)

    def test_empty_payload_produces_exists_claim(self):
        event = {"event_id": "e3", "payload": {}}
        claims = extract_claims(event)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0]["predicate"], "exists")

    def test_same_event_same_output(self):
        """Stub extractor is deterministic (no randomness, no I/O)."""
        event = {"event_id": "e4", "payload": {"category": "x", "tools": ["t"]}}
        self.assertEqual(extract_claims(event), extract_claims(event))

    def test_all_claims_have_required_keys(self):
        event = {
            "event_id": "e5",
            "payload": {"category": "c", "source": "s", "event_type": "et", "tools": ["t"]},
        }
        for claim in extract_claims(event):
            self.assertIn("subject", claim)
            self.assertIn("predicate", claim)
            self.assertIn("object", claim)
            self.assertIn("confidence", claim)


if __name__ == "__main__":
    unittest.main()
