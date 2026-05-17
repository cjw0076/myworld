#!/usr/bin/env python3
"""AIOS local-first ingest server — aios.ingest_protocol.v1 http transport.

Implements ASC-0179 Packet B. A stdlib-only HTTP server that binds
127.0.0.1 ONLY and accepts AIOS packets via `POST /aios/ingest`, writing
them into `.aios/inbox/<repo>/` — the same storage the file transport uses.

This is a transport adapter, not a second ingestion path. Downstream
ingestion stays with `scripts/aios_ingest_product_recap.py`.

Hard boundary (ASC-0179): binds 127.0.0.1 only. No auth, no TLS, no
non-localhost bind. Network exposure is the hosting decision (ASC-0180).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aios_workbench_registry import known_repos  # noqa: E402

PROTOCOL = "aios.ingest_protocol.v1"
LOOPBACK = "127.0.0.1"
FORBIDDEN_MARKERS = (
    "BEGIN PRIVATE KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "sk-",
    "_from_desktop/",
    "dain/",
    "minyoung/",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def packet_identity(packet: dict[str, Any]) -> str:
    schema = str(packet.get("schema", ""))
    repo = str(packet.get("product_repo") or packet.get("repo") or "")
    key = str(packet.get("sprint_id") or packet.get("dispatch_id") or packet.get("packet_id") or "")
    return f"{schema}|{repo}|{key}"


def receipt_id(identity: str) -> str:
    return "rcpt_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def inbox_path_for(root: Path, packet: dict[str, Any]) -> Path | None:
    """Where a packet lands. product_recap packets go to inbox/myworld/."""
    schema = str(packet.get("schema", ""))
    if schema == "aios.product_recap.v1":
        repo = str(packet.get("product_repo", ""))
        if repo not in known_repos(root):
            return None
        sprint = str(packet.get("sprint_id", "")).strip()
        if not sprint:
            return None
        return root / ".aios" / "inbox" / "myworld" / f"product_recap__{repo}__{sprint}.json"
    return None


def validate(packet: dict[str, Any]) -> str:
    if not isinstance(packet, dict):
        return "body is not a JSON object"
    if not packet.get("schema"):
        return "missing schema field"
    blob = json.dumps(packet, ensure_ascii=False)
    for marker in FORBIDDEN_MARKERS:
        if marker in blob:
            return f"forbidden_marker:{marker} (DNA Invariant 7)"
    return "ok"


class IngestHandler(BaseHTTPRequestHandler):
    server_version = "AIOSIngest/1"
    root: Path = Path(".")

    def log_message(self, fmt: str, *args: Any) -> None:  # quiet by default
        pass

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/aios/health":
            self._send(200, {"protocol": PROTOCOL, "status": "ok", "bind": LOOPBACK})
        else:
            self._send(404, {"accepted": False, "receipt_id": None, "reason": "not found"})

    def do_POST(self) -> None:
        if self.path != "/aios/ingest":
            self._send(404, {"accepted": False, "receipt_id": None, "reason": "unknown path"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            packet = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._send(400, {"accepted": False, "receipt_id": None, "reason": f"invalid json: {exc}"})
            return

        reason = validate(packet)
        if reason != "ok":
            self._send(422, {"accepted": False, "receipt_id": None, "reason": reason})
            return

        dest = inbox_path_for(self.root, packet)
        if dest is None:
            self._send(
                422,
                {"accepted": False, "receipt_id": None, "reason": "unroutable packet (schema/repo/key)"},
            )
            return

        rid = receipt_id(packet_identity(packet))
        if dest.exists():
            # idempotent re-delivery
            self._send(200, {"accepted": True, "receipt_id": rid, "reason": "idempotent: already ingested"})
            return

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self._send(
            200,
            {
                "accepted": True,
                "receipt_id": rid,
                "reason": "ok",
                "stored": str(dest.relative_to(self.root)),
                "ingested_at": now_iso(),
                "next": "python scripts/aios_ingest_product_recap.py --apply",
            },
        )


def serve(root: Path, port: int) -> None:
    IngestHandler.root = root
    httpd = ThreadingHTTPServer((LOOPBACK, port), IngestHandler)
    actual_host, actual_port = httpd.server_address[0], httpd.server_address[1]
    if actual_host != LOOPBACK:
        httpd.server_close()
        raise SystemExit(f"refusing non-loopback bind: {actual_host} (ASC-0179 hard boundary)")
    print(f"AIOS ingest server: http://{actual_host}:{actual_port}/aios/ingest  (protocol {PROTOCOL})")
    print(f"bind={actual_host} (loopback only — hosting is ASC-0180, not this server)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS local-first ingest server (aios.ingest_protocol.v1)")
    parser.add_argument("--root", default=".", help="myworld repo root")
    parser.add_argument("--port", type=int, default=8787, help="loopback port (default 8787)")
    parser.add_argument("--host", default=LOOPBACK, help="ignored unless 127.0.0.1 — non-loopback is refused")
    args = parser.parse_args(argv)

    if args.host != LOOPBACK:
        print(f"error: --host {args.host} refused. ASC-0179 binds {LOOPBACK} only.", file=sys.stderr)
        return 2

    serve(Path(args.root).resolve(), args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
