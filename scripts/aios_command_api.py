#!/usr/bin/env python3
"""
aios_command_api.py — Command API (A1): canonical write path + CQRS seam.

Implements the ONE-TRANSACTION write path — the architecture's keystone
invariant.  Events, run_state, and outbox are committed atomically:

    BEGIN
    -- Lakebase: SET LOCAL app.tenant_id = '<tenant_id>';  (RLS GUC)
    INSERT INTO events ...
    UPDATE run_state SET version = version + 1
        WHERE tenant_id = ? AND run_id = ? AND version = <expected>
    -- 0 rows updated → ROLLBACK + raise VersionConflict
    INSERT INTO outbox ...
    COMMIT

No event is ever committed without its matching outbox row, and no outbox
row is ever committed without its matching event.

Lakebase schema mapping (SQLite fixture → production):
  events     →  ledger.events
  run_state  →  ledger.run_state
  outbox     →  jobs.outbox   (shape aligned with aios_outbox_relay so
                               relay_once can drain it without changes)

CQRS seam:
  Command: write_command(conn, ...)  — the sole write entry-point.
  Query  : read_run_state(conn, ...) — read-only; never writes.

Tenant isolation (simulated RLS):
  Every SQL statement carries an explicit tenant_id predicate.  In Lakebase
  (PostgreSQL) this is additionally enforced by a Row-Level Security policy
  keyed on current_setting('app.tenant_id'), set per-transaction via
  SET LOCAL.

Usage:
  python3 scripts/aios_command_api.py --demo
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class VersionConflict(Exception):
    """
    Raised by write_command when expected_version does not match the current
    run_state.version for the given (tenant_id, run_id).

    The entire transaction is rolled back before this exception is raised.
    No event, run_state change, or outbox row is left behind.  The caller
    may safely re-read run_state and retry with the updated version.
    """


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
-- A1 write-side tables.

-- events: immutable event ledger.  One row per domain event.
--   Lakebase: ledger.events
--   Idempotency key: UNIQUE(event_id) and UNIQUE(tenant_id, run_id, seq).
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id   TEXT    NOT NULL,
    event_id    TEXT    NOT NULL,
    run_id      TEXT    NOT NULL,
    seq         INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    payload     TEXT    NOT NULL,           -- JSON string
    created_at  TEXT    NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (event_id),
    UNIQUE (tenant_id, run_id, seq)
);

-- run_state: mutable current state + optimistic concurrency version.
--   Lakebase: ledger.run_state
--   PRIMARY KEY enforces exactly one state record per (tenant_id, run_id).
CREATE TABLE IF NOT EXISTS run_state (
    tenant_id   TEXT    NOT NULL,
    run_id      TEXT    NOT NULL,
    state       TEXT    NOT NULL DEFAULT 'created',
    version     INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT    NOT NULL
                DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    PRIMARY KEY (tenant_id, run_id)
);

-- outbox: transactional outbox for fan-out to the worker plane.
--   Shape aligned with aios_outbox_relay so relay_once can drain it without
--   any changes.  Lakebase: jobs.outbox
CREATE TABLE IF NOT EXISTS outbox (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     TEXT    NOT NULL,
    topic         TEXT    NOT NULL,
    payload       TEXT    NOT NULL,         -- JSON string
    created_at    TEXT    NOT NULL
                  DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    dispatched_at TEXT                      -- NULL = pending; set by W1 relay
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all A1 write-side tables if they do not exist."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def open_fixture(path: str = ":memory:") -> sqlite3.Connection:
    """
    Open (or create) a SQLite fixture DB and initialise the A1 schema.

    The returned connection is suitable for write_command, read_run_state,
    and for aios_outbox_relay.relay_once (the outbox table shape matches).
    For end-to-end spine tests also call
    aios_graph_compiler.init_claims_schema(conn) to add the W2 claims table.
    """
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    init_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Write path — Command side
# ---------------------------------------------------------------------------


def write_command(
    conn: sqlite3.Connection,
    *,
    tenant_id: str,
    run_id: str,
    event_type: str,
    payload: dict,
    expected_version: int,
    topic: str,
) -> str:
    """
    Canonical one-transaction write: events + run_state + outbox.

    Atomicity guarantee (ALL-OR-NOTHING):
      All three writes happen in a single transaction.  Any failure —
      including a version mismatch — rolls back all three.  No event is ever
      committed without its outbox row, and no outbox row without its event.

      Implementation: ``with conn:`` issues commit() on normal exit and
      rollback() on any exception, including VersionConflict.

    Optimistic concurrency control:
      UPDATE run_state ... WHERE version = expected_version
      If rowcount is 0 → version mismatch → VersionConflict is raised →
      transaction is rolled back.  No locks are held between reads and writes.
      Callers re-read run_state and retry with the current version.

    Tenant isolation (simulated RLS):
      All three writes carry an explicit tenant_id column/predicate.  In
      Lakebase (PostgreSQL) this is reinforced by:
        SET LOCAL app.tenant_id = '<tenant_id>';
      inside the transaction so the RLS policy enforces row visibility at the
      DB layer independently of this application-level predicate.

    CQRS boundary:
      This function is the only sanctioned write path for all three tables.
      Use read_run_state() for queries — it never writes.

    Parameters
    ----------
    conn             : SQLite connection from open_fixture().
    tenant_id        : Tenant identifier; the RLS key in production.
    run_id           : Execution run identifier (groups related events).
    event_type       : Domain event type (e.g. 'agent.started').
    payload          : Arbitrary event data (must be JSON-serialisable).
    expected_version : Caller's view of run_state.version.  Must match the
                       current version or VersionConflict is raised.
    topic            : Outbox topic routed to worker consumers by W1 relay.

    Returns
    -------
    str : The event_id (UUID) assigned to the new event.

    Raises
    ------
    VersionConflict : run_state.version != expected_version; zero rows written.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_id = str(uuid.uuid4())
    seq = expected_version + 1  # monotone per (tenant_id, run_id)

    # Outbox payload carries the full event so W1→W2 consumers receive all
    # fields without a separate events-table query.
    outbox_payload = json.dumps(
        {
            "tenant_id": tenant_id,
            "event_id": event_id,
            "run_id": run_id,
            "seq": seq,
            "type": event_type,
            "payload": payload,   # original command payload
        }
    )

    # ONE-TRANSACTION write.
    # with conn: → __exit__ calls commit() on success, rollback() on exception.
    # Raising VersionConflict inside the block triggers rollback before
    # the exception propagates to the caller.
    #
    # PostgreSQL/Lakebase equivalent:
    #   BEGIN;
    #   SET LOCAL app.tenant_id = '<tenant_id>';      -- RLS GUC
    #   INSERT INTO ledger.events ...;
    #   UPDATE ledger.run_state SET version = version + 1
    #       WHERE tenant_id = ... AND run_id = ... AND version = <expected>;
    #   -- 0 rows → ROLLBACK; raise VersionConflict
    #   INSERT INTO jobs.outbox ...;
    #   COMMIT;
    with conn:
        cur = conn.cursor()

        # Step 1 — append the event to the immutable event ledger.
        # A UNIQUE constraint failure on (tenant_id, run_id, seq) means another
        # writer already committed seq=expected_version+1 — equivalent to a
        # version conflict — so we convert it to VersionConflict so the
        # with conn: block rolls back cleanly and the caller gets the same
        # exception type regardless of which guard fires first.
        try:
            cur.execute(
                "INSERT INTO events "
                "(tenant_id, event_id, run_id, seq, type, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (tenant_id, event_id, run_id, seq, event_type, json.dumps(payload), now),
            )
        except sqlite3.IntegrityError as exc:
            raise VersionConflict(
                f"run_id={run_id!r} tenant={tenant_id!r}: "
                f"seq={seq} already exists (concurrent write at same expected_version): {exc}"
            ) from exc

        # Step 2 — advance run_state version (optimistic concurrency check).
        # WHERE version = expected_version is the lock-free concurrency guard.
        cur.execute(
            "UPDATE run_state "
            "SET state = ?, version = version + 1, updated_at = ? "
            "WHERE tenant_id = ? AND run_id = ? AND version = ?",
            (event_type, now, tenant_id, run_id, expected_version),
        )
        if cur.rowcount == 0:
            # 0 rows: either expected_version is stale or run_id does not exist
            # for this tenant.  Raising here triggers with conn: rollback of
            # Step 1 before the exception reaches the caller.
            raise VersionConflict(
                f"run_id={run_id!r} tenant={tenant_id!r}: "
                f"expected version {expected_version!r} but current version "
                f"differs (or run does not exist for this tenant)"
            )

        # Step 3 — emit the outbox row for W1 relay to fan out.
        cur.execute(
            "INSERT INTO outbox (tenant_id, topic, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (tenant_id, topic, outbox_payload, now),
        )

    log.debug(
        "write_command: tenant=%s run_id=%s event_id=%s type=%s seq=%d",
        tenant_id, run_id, event_id, event_type, seq,
    )
    return event_id


# ---------------------------------------------------------------------------
# Query path — CQRS read side
# ---------------------------------------------------------------------------


def read_run_state(
    conn: sqlite3.Connection,
    tenant_id: str,
    run_id: str,
) -> dict | None:
    """
    Query side (CQRS read path): return the current run_state or None.

    NEVER writes to any table.  This is the only sanctioned read path for
    run_state; keeping reads and writes in separate functions enforces the
    Command/Query Responsibility Segregation boundary.

    Tenant isolation: the WHERE tenant_id = ? predicate ensures a query for
    tenant A cannot return rows owned by tenant B.  In Lakebase (PostgreSQL)
    this is additionally enforced by Row-Level Security at the DB layer.

    Parameters
    ----------
    conn      : Any SQLite connection with the run_state table.
    tenant_id : Tenant identifier.
    run_id    : Execution run identifier.

    Returns
    -------
    dict with keys {tenant_id, run_id, state, version, updated_at} or None.
    """
    # CQRS contract: no INSERT, UPDATE, DELETE — pure read.
    row = conn.execute(
        "SELECT state, version, updated_at "
        "FROM run_state "
        "WHERE tenant_id = ? AND run_id = ?",
        (tenant_id, run_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "tenant_id": tenant_id,
        "run_id": run_id,
        "state": row[0],
        "version": row[1],
        "updated_at": row[2],
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _demo(db_path: str = ":memory:") -> None:
    """Demo: one write_command + relay drain via W1→W2, prints draft claims."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from aios_outbox_relay import relay_once          # noqa: PLC0415
    from aios_graph_compiler import (                 # noqa: PLC0415
        init_claims_schema,
        make_consumer,
    )

    conn = open_fixture(db_path)
    init_claims_schema(conn)   # add W2 claims table to the same connection

    tenant = "demo-tenant"
    run = "demo-run-1"

    # Seed a run_state row (normally done by a 'create_run' command).
    conn.execute(
        "INSERT INTO run_state (tenant_id, run_id, state, version) VALUES (?, ?, ?, ?)",
        (tenant, run, "created", 0),
    )
    conn.commit()
    log.info("seeded run_state tenant=%s run_id=%s version=0", tenant, run)

    # A1 producer: atomic write.
    eid = write_command(
        conn,
        tenant_id=tenant,
        run_id=run,
        event_type="agent.started",
        payload={"category": "aios", "source": "demo", "tools": ["relay", "compiler"]},
        expected_version=0,
        topic="graph_compile",
    )
    log.info("write_command succeeded: event_id=%s", eid)

    state = read_run_state(conn, tenant, run)
    log.info("CQRS read after write: %s", state)

    # W1→W2 spine: relay drains the outbox row, compiler projects draft claims.
    consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
    dispatched = relay_once(conn, consumer)
    log.info("relay_once dispatched %d outbox row(s)", dispatched)

    rows = conn.execute(
        "SELECT subject, predicate, object, status FROM claims WHERE tenant_id = ?",
        (tenant,),
    ).fetchall()
    print(f"\nFull spine: {len(rows)} draft claim(s) from one write_command:")
    for r in rows:
        print(json.dumps(dict(zip(["subject", "predicate", "object", "status"], r))))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AIOS Command API (A1) — canonical write path + CQRS seam"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run one write_command + relay drain, print draft claims",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        metavar="PATH",
        help="SQLite fixture path (default: :memory:)",
    )
    args = parser.parse_args()

    if args.demo:
        _demo(args.db)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
