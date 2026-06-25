#!/usr/bin/env python3
"""
aios_outbox_relay.py — Transactional-outbox relay (W1).

Drains the `outbox` table (SQLite fixture; Lakebase equivalent: jobs.outbox)
to the worker plane (Graph Compiler, Embedding, Merkle, …).

Delivery guarantee: AT-LEAST-ONCE / IDEMPOTENT-CONSUMER.

  The relay selects pending rows (dispatched_at IS NULL) ordered by id,
  calls dispatch_fn(topic, payload) for each, and on success marks
  dispatched_at.  If the process crashes after dispatch_fn succeeds but
  before the UPDATE is committed, the row remains pending and will be
  re-dispatched on the next pass.  CONSUMERS MUST be idempotent — e.g.,
  UPSERT on a (tenant_id, source_event_id, worker_name) unique key, or
  dedup via a set keyed by outbox row id.  A dispatch_fn that raises an
  exception leaves its row pending (retried next pass) without blocking
  subsequent rows.

SQLite table names vs Lakebase schema-qualified names:
  SQLite (fixture)   →  Lakebase (production)
  outbox             →  jobs.outbox
  events             →  ledger.events

The connection object is the only Lakebase-specific seam; swap it with a
psycopg2/asyncpg connection and the relay logic is unchanged.

Usage:
  # fixture demo (creates an in-memory DB, inserts one row, relays it):
  python3 scripts/aios_outbox_relay.py --once [--db PATH]
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS outbox (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id    TEXT    NOT NULL,
    topic        TEXT    NOT NULL,
    payload      TEXT    NOT NULL,   -- JSON string
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    dispatched_at TEXT                -- NULL = pending; set on successful dispatch
);

-- Minimal ledger.events mirror for context / FK reference in tests.
-- In Lakebase this lives in the ledger schema (ledger.events).
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id    TEXT    NOT NULL,
    event_type   TEXT    NOT NULL,
    payload      TEXT    NOT NULL,   -- JSON string
    created_at   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Create outbox and events tables if they do not exist."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def open_fixture(path: str = ":memory:") -> sqlite3.Connection:
    """Open (or create) a SQLite fixture DB and initialise the schema."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Core relay
# ---------------------------------------------------------------------------

DispatchFn = Callable[[str, str], None]


def relay_once(conn: sqlite3.Connection, dispatch_fn: DispatchFn) -> int:
    """
    Drain one batch of pending outbox rows.

    For each row WHERE dispatched_at IS NULL (ordered by id ascending):
      1. Call dispatch_fn(topic, payload).
      2. On success: UPDATE dispatched_at = now.
      3. On exception: leave row pending (will retry next pass); continue to
         the next row so a single failing row cannot starve later ones.

    Returns the number of rows successfully dispatched in this pass.

    AT-LEAST-ONCE NOTE: the window between step 1 and step 2 is a potential
    re-delivery window if the process is killed between those two statements.
    Consumers MUST handle duplicate delivery (see module docstring).
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT id, topic, payload FROM outbox WHERE dispatched_at IS NULL ORDER BY id"
    )
    rows = cur.fetchall()

    dispatched = 0
    for row_id, topic, payload in rows:
        try:
            dispatch_fn(topic, payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("dispatch failed for outbox id=%s topic=%s: %s", row_id, topic, exc)
            continue  # leave pending; do NOT block subsequent rows

        # Mark row dispatched only after dispatch_fn succeeds.
        # A crash here → re-delivery on next pass (AT-LEAST-ONCE).
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cur.execute(
            "UPDATE outbox SET dispatched_at = ? WHERE id = ?",
            (now, row_id),
        )
        conn.commit()
        dispatched += 1
        log.debug("dispatched outbox id=%s topic=%s", row_id, topic)

    return dispatched


def relay_loop(
    conn: sqlite3.Connection,
    dispatch_fn: DispatchFn,
    *,
    poll_interval: float = 1.0,
    max_iterations: int | None = None,
) -> None:
    """
    Poll relay_once on a fixed interval.

    Runs indefinitely when max_iterations is None (production mode).
    Set max_iterations for testing / bounded runs.
    poll_interval is ignored when max_iterations=1 (no sleep needed).
    """
    iterations = 0
    while True:
        try:
            n = relay_once(conn, dispatch_fn)
            if n:
                log.info("relay_loop: dispatched %d row(s)", n)
        except Exception as exc:  # noqa: BLE001
            log.error("relay_loop iteration error: %s", exc)

        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            break
        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _stdout_dispatch(topic: str, payload: str) -> None:
    print(json.dumps({"topic": topic, "payload": payload}, ensure_ascii=False))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="AIOS transactional-outbox relay (W1)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="drain one pass then exit (useful for scripts and tests)",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        metavar="PATH",
        help="SQLite fixture path (default: :memory:)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="insert a sample outbox row before running (demo / smoke-test)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        metavar="SECS",
        help="seconds between relay passes in loop mode (default: 1.0)",
    )
    args = parser.parse_args()

    conn = open_fixture(args.db)

    if args.seed:
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("demo-tenant", "graph.compile", json.dumps({"event_id": 1})),
        )
        conn.commit()
        log.info("seeded one sample outbox row")

    if args.once:
        n = relay_once(conn, _stdout_dispatch)
        print(f"dispatched {n} row(s)")
    else:
        relay_loop(conn, _stdout_dispatch, poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
