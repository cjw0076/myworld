#!/usr/bin/env python3
"""HTTP delivery surface for Deadline Copilot (handoff gap #3 enabler).

Exposes the copilot as a tiny local service so any frontend — the uri app, a
shortcut, curl — can POST a student's deadlines and get back the verified,
provenance-tracked plan. No external deps (stdlib http.server). The flow itself
(failover-routed local gen → date-verify → GenesisOS → receipt → per-student
memory) is unchanged; this just makes it callable.

  POST /plan  {"assignments":[{course,title,due}], "student":"id", "today":"YYYY-MM-DD"}
              — or {"ical":"<.ics text>"} / {"csv":"<text>"} instead of assignments
  GET  /health

Schema: aios.copilot_serve.v1
Usage: python scripts/aios_copilot_serve.py [--port 8765]
"""
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import aios_deadline_copilot as copilot

ROOT = Path(__file__).resolve().parents[1]


def plan_request(payload: dict) -> tuple[int, dict]:
    """Pure request handler: validate input, run the copilot, return (status, body).
    Kept separate from the HTTP layer so it is unit-testable."""
    if payload.get("ical"):
        assignments = copilot.parse_ical(str(payload["ical"]))
    elif payload.get("csv"):
        assignments = copilot.parse_csv(str(payload["csv"]))
    else:
        assignments = payload.get("assignments")
    if not assignments or not isinstance(assignments, list):
        return 400, {"error": "no assignments (provide assignments[], ical, or csv)"}

    today = payload.get("today") or time.strftime("%Y-%m-%d")
    student = payload.get("student")
    out_dir = copilot.student_dir(student)
    prior = copilot.load_prior_context(out_dir)
    receipt = copilot.run(assignments, today, prior)

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S")
    (out_dir / f"receipt-{stamp}.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 200, receipt


def make_handler() -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/health":
                self._send(200, {"ok": True, "service": "aios.copilot_serve.v1"})
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/plan":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._send(400, {"error": "invalid JSON body"})
                return
            status, body = plan_request(payload)
            self._send(status, body)

        def log_message(self, *args) -> None:  # quiet
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)
    server = HTTPServer((args.host, args.port), make_handler())
    print(f"aios copilot serving on http://{args.host}:{args.port}  (POST /plan, GET /health)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
