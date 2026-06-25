#!/usr/bin/env python3
"""
aios_graph_compiler.py — Graph Compiler (W2).

Consumes ledger events from the `graph_compile` outbox topic (produced by W1)
and projects them into the `claims` table as DRAFT knowledge-graph triples.

Lakebase production mapping (SQLite fixture names → schema-qualified names):
  SQLite            →  Lakebase
  outbox            →  jobs.outbox
  events            →  ledger.events
  claims            →  graph.claims

IDEMPOTENCY CONTRACT (pairs with W1's at-least-once delivery):
  Every claim insertion uses INSERT OR IGNORE against the UNIQUE key
  (tenant_id, source_event_id, compiler_name, compiler_version, predicate).
  Compiling the SAME event twice — whether from a queue retry, a crash-before-
  mark window in W1, or an explicit replay — writes each claim at most once.
  The relay can deliver at-least-once; the compiler absorbs duplicate deliveries
  as no-ops.

DRAFT-FIRST INVARIANT:
  All claims are written with status='draft'. No claim is auto-accepted.
  Acceptance is a separate operator-mediated lifecycle step (MemoryOS review).

CLAIM EXTRACTOR INTERFACE:
  extract_claims(event) -> list[dict] is the seam where the LLM extractor plugs
  in.  The current implementation is a DETERMINISTIC STUB that derives
  (subject, predicate, object) triples purely from structural fields in the
  event payload (category, tools, event_type, source).  The real LLM extractor
  (e.g., calling Claude to extract semantic triples) swaps in here behind the
  same interface without changing compile_event or make_consumer.

Usage:
  # fixture demo (in-memory DB, seeds one event, compiles it):
  python3 scripts/aios_graph_compiler.py --once [--db PATH]
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_CLAIMS_SCHEMA_SQL = """
-- graph.claims (Lakebase: graph schema, claims table)
-- Stores knowledge-graph triples compiled from ledger events.
-- Idempotency key: UNIQUE(tenant_id, source_event_id, compiler_name,
--   compiler_version, predicate) — guarantees at-most-once write per
--   (event × compiler × predicate), making INSERT OR IGNORE safe for
--   at-least-once redelivery from W1.
CREATE TABLE IF NOT EXISTS claims (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id        TEXT    NOT NULL,
    source_event_id  TEXT    NOT NULL,
    compiler_name    TEXT    NOT NULL,
    compiler_version TEXT    NOT NULL,
    subject          TEXT    NOT NULL,
    predicate        TEXT    NOT NULL,
    object           TEXT    NOT NULL,
    confidence       REAL    NOT NULL DEFAULT 1.0,
    status           TEXT    NOT NULL DEFAULT 'draft',
    created_at       TEXT    NOT NULL
                     DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (tenant_id, source_event_id, compiler_name, compiler_version, predicate)
);
"""


def init_claims_schema(conn: sqlite3.Connection) -> None:
    """Create the claims table if it does not exist."""
    conn.executescript(_CLAIMS_SCHEMA_SQL)
    conn.commit()


def open_fixture(path: str = ":memory:") -> sqlite3.Connection:
    """
    Open (or create) a SQLite fixture DB with both W1 (outbox/events) and
    W2 (claims) schemas.

    Delegates W1 schema creation to aios_outbox_relay.open_fixture so that a
    single connection can be used for end-to-end W1→W2 seam tests.
    """
    # Import here to avoid circular-import at module load; W1 is a dependency,
    # not the other way around.
    from aios_outbox_relay import open_fixture as relay_open  # noqa: PLC0415

    conn = relay_open(path)
    init_claims_schema(conn)
    return conn


# ---------------------------------------------------------------------------
# Claim extractor (deterministic stub)
# ---------------------------------------------------------------------------

def extract_claims(event: dict) -> list[dict]:
    """
    Deterministic stub claim extractor.

    Derives (subject, predicate, object, confidence) triples purely from
    structural fields in event["payload"].  No LLM, no I/O, no side effects.

    The real LLM extractor swaps in here behind this same interface:
      def extract_claims(event: dict) -> list[dict]:
          # Call Claude / local LLM, parse response into the same list[dict].

    Supported payload fields:
      category   → ("event:<id>", "has_category", "<value>")
      event_type → ("event:<id>", "has_event_type", "<value>")
      source     → ("event:<id>", "has_source", "<value>")
      tools      → ("event:<id>", "uses_tool:<name>", "true") per tool

    Fallback (no recognized fields): one ("event:<id>", "exists", "true") claim.
    """
    payload = event.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}

    event_id = str(event.get("event_id", "unknown"))
    subject = f"event:{event_id}"

    claims: list[dict] = []

    if "category" in payload:
        claims.append({
            "subject": subject,
            "predicate": "has_category",
            "object": str(payload["category"]),
            "confidence": 1.0,
        })

    if "event_type" in payload:
        claims.append({
            "subject": subject,
            "predicate": "has_event_type",
            "object": str(payload["event_type"]),
            "confidence": 1.0,
        })

    if "source" in payload:
        claims.append({
            "subject": subject,
            "predicate": "has_source",
            "object": str(payload["source"]),
            "confidence": 1.0,
        })

    tools = payload.get("tools", [])
    if isinstance(tools, list):
        for tool in tools:
            # Predicate encodes the tool name so each tool gets a unique key
            # under the UNIQUE(…, predicate) constraint.
            claims.append({
                "subject": subject,
                "predicate": f"uses_tool:{tool}",
                "object": "true",
                "confidence": 1.0,
            })

    if not claims:
        claims.append({
            "subject": subject,
            "predicate": "exists",
            "object": "true",
            "confidence": 1.0,
        })

    return claims


# ---------------------------------------------------------------------------
# Core compiler
# ---------------------------------------------------------------------------

def compile_event(
    conn: sqlite3.Connection,
    event: object,
    *,
    compiler_name: str,
    compiler_version: str,
) -> int:
    """
    Project one ledger event into DRAFT claims.

    Parameters
    ----------
    conn             : SQLite connection with the claims table present.
    event            : Ledger event dict.  Required keys: tenant_id, event_id.
                       Optional key: payload (dict of structural fields).
    compiler_name    : Identifies which extractor produced these claims.
    compiler_version : Version of the extractor (part of the idempotency key).

    Returns
    -------
    int : Number of NEW claims written (0 if all already existed or event was
          malformed).

    Guarantees
    ----------
    IDEMPOTENT : Calling compile_event with the same (event, compiler_name,
        compiler_version) any number of times writes each claim at most once.
        The UNIQUE key + INSERT OR IGNORE is the mechanism.

    ATOMIC : All INSERTs for a single event are in one transaction.  A
        malformed event causes zero writes (no partial state).

    DRAFT-FIRST : Every written claim has status='draft'.
    """
    # --- validate / extract structured fields ---
    if not isinstance(event, dict):
        log.warning("compile_event: event is not a dict, dropped: type=%s", type(event).__name__)
        return 0

    try:
        tenant_id = event["tenant_id"]
        event_id = str(event["event_id"])
    except KeyError as exc:
        log.warning("compile_event: missing required field %s, dropped: event=%r", exc, event)
        return 0

    try:
        claims = extract_claims(event)
    except Exception as exc:  # noqa: BLE001
        log.warning("compile_event: extract_claims failed for event_id=%s: %s", event_id, exc)
        return 0

    # --- write claims in a single atomic transaction ---
    new_count = 0
    try:
        cur = conn.cursor()
        for claim in claims:
            cur.execute(
                """
                INSERT OR IGNORE INTO claims
                    (tenant_id, source_event_id, compiler_name, compiler_version,
                     subject, predicate, object, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    event_id,
                    compiler_name,
                    compiler_version,
                    claim["subject"],
                    claim["predicate"],
                    claim["object"],
                    claim.get("confidence", 1.0),
                ),
            )
            # changes() == 1 if the row was inserted; 0 if UNIQUE conflict
            # caused the insert to be ignored.
            new_count += conn.execute("SELECT changes()").fetchone()[0]
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        log.warning(
            "compile_event: transaction failed for tenant=%s event_id=%s: %s",
            tenant_id, event_id, exc,
        )
        return 0

    log.debug(
        "compile_event: tenant=%s event_id=%s new_claims=%d",
        tenant_id, event_id, new_count,
    )
    return new_count


# ---------------------------------------------------------------------------
# Relay consumer factory
# ---------------------------------------------------------------------------

DispatchFn = Callable[[str, str], None]


def make_consumer(
    conn: sqlite3.Connection,
    *,
    compiler_name: str = "stub",
    compiler_version: str = "0.1",
) -> DispatchFn:
    """
    Return a dispatch_fn compatible with aios_outbox_relay.relay_once.

    The returned function:
      - Ignores topics other than 'graph_compile'.
      - Parses the payload JSON as a ledger event dict.
      - Calls compile_event; absorbs errors internally (never raises), so
        the relay always marks the outbox row dispatched — malformed events
        are dropped, not retried endlessly.

    Wiring example:
        conn = open_fixture()
        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        aios_outbox_relay.relay_once(conn, consumer)
    """
    def dispatch_fn(topic: str, payload: str) -> None:
        if topic != "graph_compile":
            return
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            log.warning("make_consumer: invalid JSON in graph_compile payload: %s", exc)
            return
        compile_event(conn, event, compiler_name=compiler_name, compiler_version=compiler_version)

    return dispatch_fn


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="AIOS graph compiler (W2) — fixture demo"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="seed one fixture event, compile it via W1 relay, then exit",
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        metavar="PATH",
        help="SQLite fixture path (default: :memory:)",
    )
    args = parser.parse_args()

    conn = open_fixture(args.db)

    if args.once:
        # Import W1 relay to demonstrate the full W1→W2 seam.
        from aios_outbox_relay import relay_once  # noqa: PLC0415

        # Seed one outbox row (as W1 producer would do after a ledger commit).
        event = {
            "tenant_id": "demo-tenant",
            "event_id": "demo-event-1",
            "payload": {
                "category": "aios",
                "event_type": "memory.store",
                "tools": ["mcp", "relay"],
            },
        }
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("demo-tenant", "graph_compile", json.dumps(event)),
        )
        conn.commit()
        log.info("seeded one graph_compile outbox row")

        # Drain via relay → compiler seam.
        consumer = make_consumer(conn, compiler_name="stub", compiler_version="0.1")
        dispatched = relay_once(conn, consumer)
        log.info("relay dispatched %d outbox row(s)", dispatched)

        rows = conn.execute(
            "SELECT subject, predicate, object, status FROM claims"
        ).fetchall()
        print(f"compiled {len(rows)} claim(s):")
        for row in rows:
            print(json.dumps(dict(zip(["subject", "predicate", "object", "status"], row))))

        # Demonstrate idempotency: relay the same event again.
        conn.execute(
            "INSERT INTO outbox (tenant_id, topic, payload) VALUES (?, ?, ?)",
            ("demo-tenant", "graph_compile", json.dumps(event)),
        )
        conn.commit()
        log.info("seeded same event a second time (idempotency demo)")
        relay_once(conn, consumer)

        rows2 = conn.execute(
            "SELECT COUNT(*) FROM claims"
        ).fetchone()[0]
        print(f"after second relay pass: {rows2} claim(s) total (no duplicates)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
