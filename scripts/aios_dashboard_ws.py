#!/usr/bin/env python3
"""Tiny stdlib WebSocket event stream for the local AIOS dashboard."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import select
import socket
import socketserver
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "aios.dashboard_ws.v1"
GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
EVENTS_PATH = Path(".aios/primitives/events.jsonl")
MONITOR_PATH = Path(".aios/state/monitor_assessment.latest.json")
MONITORS_DIR = Path(".aios/primitives/monitors")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def primitive_pulses(root: Path) -> list[dict[str, Any]]:
    pulses: list[dict[str, Any]] = []
    monitors = root / MONITORS_DIR
    if not monitors.exists():
        return pulses
    for path in sorted(monitors.glob("*.json"))[:20]:
        payload = read_json(path)
        if isinstance(payload, dict):
            pulses.append(
                {
                    "name": payload.get("name") or path.stem,
                    "status": payload.get("status") or payload.get("state") or "unknown",
                    "updated_at": payload.get("updated_at") or payload.get("last_seen") or payload.get("ts_iso"),
                }
            )
    return pulses


def run_monitor_assess(root: Path) -> dict[str, Any] | None:
    try:
        result = subprocess.run(
            [sys.executable, "scripts/aios_monitor.py", "assess", "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def heartbeat(root: Path, *, assess: bool = True) -> dict[str, Any]:
    monitor = run_monitor_assess(root) if assess else None
    if monitor is None:
        monitor = read_json(root / MONITOR_PATH) or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "heartbeat",
        "ts_iso": now_iso(),
        "monitor": {
            "health": monitor.get("health", "unknown") if isinstance(monitor, dict) else "unknown",
            "blocked": monitor.get("blocked", []) if isinstance(monitor, dict) else [],
            "next_actions": monitor.get("next_actions", []) if isinstance(monitor, dict) else [],
        },
        "pulses": primitive_pulses(root),
    }


def parse_event_line(raw: str) -> dict[str, Any]:
    stripped = raw.rstrip("\n")
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        event = None
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "event",
        "ts_iso": now_iso(),
        "event": event,
        "raw": stripped,
    }


def websocket_accept(key: str) -> str:
    digest = hashlib.sha1((key + GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(payload: dict[str, Any]) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    length = len(body)
    if length < 126:
        header = bytes([0x81, length])
    elif length < 65536:
        header = bytes([0x81, 126]) + length.to_bytes(2, "big")
    else:
        header = bytes([0x81, 127]) + length.to_bytes(8, "big")
    return header + body


def client_closed(sock: socket.socket) -> bool:
    ready, _, _ = select.select([sock], [], [], 0)
    if not ready:
        return False
    try:
        data = sock.recv(2, socket.MSG_PEEK)
    except (BlockingIOError, InterruptedError):
        return False
    except OSError:
        return True
    return data == b""


class DashboardWebSocketHandler(socketserver.BaseRequestHandler):
    root: Path
    heartbeat_seconds: float
    assess: bool

    def handle(self) -> None:
        request = self.request.recv(4096).decode("utf-8", errors="replace")
        headers = self.parse_headers(request)
        path = self.parse_path(request)
        key = headers.get("sec-websocket-key")
        if not key:
            self.request.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
            return
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {websocket_accept(key)}\r\n"
            "\r\n"
        )
        self.request.sendall(response.encode("ascii"))
        self.request.setblocking(False)
        if path.startswith("/chat"):
            self.stream_chat()
        else:
            self.stream_events()

    @staticmethod
    def parse_headers(request: str) -> dict[str, str]:
        headers: dict[str, str] = {}
        for line in request.split("\r\n")[1:]:
            key, sep, value = line.partition(":")
            if sep:
                headers[key.strip().lower()] = value.strip()
        return headers

    @staticmethod
    def parse_path(request: str) -> str:
        first = request.split("\r\n", 1)[0]
        parts = first.split()
        return parts[1] if len(parts) >= 2 else "/events"

    def send_payload(self, payload: dict[str, Any]) -> bool:
        try:
            self.request.sendall(encode_frame(payload))
        except OSError:
            return False
        return True

    def stream_events(self) -> None:
        events = self.root / EVENTS_PATH
        events.parent.mkdir(parents=True, exist_ok=True)
        events.touch(exist_ok=True)
        offset = events.stat().st_size
        next_heartbeat = 0.0
        while True:
            if client_closed(self.request):
                return
            now = time.monotonic()
            if now >= next_heartbeat:
                if not self.send_payload(heartbeat(self.root, assess=self.assess)):
                    return
                next_heartbeat = now + self.heartbeat_seconds
            try:
                with events.open("r", encoding="utf-8", errors="replace") as fh:
                    fh.seek(offset)
                    for line in fh:
                        if not self.send_payload(parse_event_line(line)):
                            return
                    offset = fh.tell()
            except OSError:
                pass
            time.sleep(0.1)

    def stream_chat(self) -> None:
        self.send_payload({"schema_version": SCHEMA_VERSION, "type": "chat_ready", "ts_iso": now_iso()})
        while True:
            if client_closed(self.request):
                return
            frame = read_client_text_frame(self.request)
            if frame is None:
                time.sleep(0.1)
                continue
            try:
                payload = json.loads(frame)
            except json.JSONDecodeError:
                self.send_payload({"schema_version": SCHEMA_VERSION, "type": "chat_error", "reason": "json_invalid", "ts_iso": now_iso()})
                continue
            if not isinstance(payload, dict):
                self.send_payload({"schema_version": SCHEMA_VERSION, "type": "chat_error", "reason": "json_object_required", "ts_iso": now_iso()})
                continue
            message = str(payload.get("message") or "").strip()
            conversation = str(payload.get("conversation_id") or "web")
            if not message:
                self.send_payload({"schema_version": SCHEMA_VERSION, "type": "chat_error", "reason": "message_missing", "ts_iso": now_iso()})
                continue
            result = run_chat_turn(self.root, message, conversation)
            self.send_payload({"schema_version": SCHEMA_VERSION, "type": "chat_response", "ts_iso": now_iso(), "result": result})


class ThreadingWebSocketServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = True


def read_exact(sock: socket.socket, size: int) -> bytes | None:
    chunks = bytearray()
    deadline = time.monotonic() + 0.1
    while len(chunks) < size:
        try:
            chunk = sock.recv(size - len(chunks))
        except (BlockingIOError, InterruptedError):
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.01)
            continue
        except OSError:
            return b""
        if not chunk:
            return b""
        chunks.extend(chunk)
    return bytes(chunks)


def read_client_text_frame(sock: socket.socket) -> str | None:
    header = read_exact(sock, 2)
    if header is None:
        return None
    if header == b"":
        return ""
    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F
    if length == 126:
        ext = read_exact(sock, 2)
        if not ext:
            return None
        length = int.from_bytes(ext, "big")
    elif length == 127:
        ext = read_exact(sock, 8)
        if not ext:
            return None
        length = int.from_bytes(ext, "big")
    mask = read_exact(sock, 4) if masked else b""
    body = read_exact(sock, length)
    if body is None:
        return None
    if body == b"":
        return ""
    if opcode == 8:
        return ""
    if opcode != 1:
        return None
    if masked and mask:
        body = bytes(byte ^ mask[index % 4] for index, byte in enumerate(body))
    return body.decode("utf-8", errors="replace")


def run_chat_turn(root: Path, message: str, conversation: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/aios_chat_router.py",
                "--root",
                root.as_posix(),
                "--conversation",
                conversation,
                "--message",
                message,
                "--json",
            ],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "reason": "chat_router_failed", "error": str(exc)}
    if result.returncode != 0:
        return {"ok": False, "reason": "chat_router_failed", "stderr_tail": result.stderr[-800:], "stdout_tail": result.stdout[-800:]}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "chat_router_json_invalid", "stdout_tail": result.stdout[-800:]}
    if isinstance(payload, dict):
        payload["ok"] = True
        return payload
    return {"ok": False, "reason": "chat_router_json_not_object"}


def serve(root: Path, host: str, port: int, heartbeat_seconds: float, assess: bool) -> None:
    handler = type(
        "ConfiguredDashboardWebSocketHandler",
        (DashboardWebSocketHandler,),
        {"root": root, "heartbeat_seconds": heartbeat_seconds, "assess": assess},
    )
    with ThreadingWebSocketServer((host, port), handler) as server:
        server.serve_forever(poll_interval=0.2)


def check(root: Path, host: str, port: int, timeout: float) -> dict[str, Any]:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            request = (
                "GET /events HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            sock.sendall(request.encode("ascii"))
            response = sock.recv(4096)
            ok = b"101 Switching Protocols" in response
    except OSError as exc:
        return {"ok": False, "schema_version": SCHEMA_VERSION, "error": str(exc), "root": root.as_posix()}
    return {"ok": ok, "schema_version": SCHEMA_VERSION, "elapsed_seconds": round(time.monotonic() - started, 3), "root": root.as_posix()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    serve_parser = sub.add_parser("serve")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8766)
    serve_parser.add_argument("--heartbeat-seconds", type=float, default=30.0)
    serve_parser.add_argument("--no-assess", action="store_true")

    check_parser = sub.add_parser("check")
    check_parser.add_argument("--host", default="127.0.0.1")
    check_parser.add_argument("--port", type=int, default=8766)
    check_parser.add_argument("--timeout", type=float, default=2.0)
    check_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "serve":
        serve(root, args.host, args.port, args.heartbeat_seconds, not args.no_assess)
        return 0
    if args.command == "check":
        result = check(root, args.host, args.port, args.timeout)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
