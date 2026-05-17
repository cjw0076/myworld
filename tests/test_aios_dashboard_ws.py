import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_dashboard_ws.py"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def handshake(port: int) -> socket.socket:
    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        "GET /events HTTP/1.1\r\n"
        f"Host: 127.0.0.1:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(request.encode("ascii"))
    response = sock.recv(4096)
    if b"101 Switching Protocols" not in response:
        raise AssertionError(response)
    sock.settimeout(4)
    return sock


def read_frame(sock: socket.socket) -> dict:
    first = sock.recv(2)
    if len(first) < 2:
        raise AssertionError("missing websocket frame header")
    length = first[1] & 0x7F
    if length == 126:
        length = int.from_bytes(sock.recv(2), "big")
    elif length == 127:
        length = int.from_bytes(sock.recv(8), "big")
    payload = b""
    while len(payload) < length:
        payload += sock.recv(length - len(payload))
    return json.loads(payload.decode("utf-8"))


class DashboardWebSocketTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        (root / ".aios" / "primitives").mkdir(parents=True)
        (root / ".aios" / "state").mkdir(parents=True)
        (root / ".aios" / "primitives" / "events.jsonl").write_text("", encoding="utf-8")
        (root / ".aios" / "state" / "monitor_assessment.latest.json").write_text(
            json.dumps({"health": "clear", "blocked": [], "next_actions": []}),
            encoding="utf-8",
        )

    def start_server(self, root: Path, port: int) -> subprocess.Popen[str]:
        process = subprocess.Popen(
            [
                sys.executable,
                SCRIPT.as_posix(),
                "--root",
                root.as_posix(),
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--heartbeat-seconds",
                "0.2",
                "--no-assess",
            ],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        deadline = time.time() + 3
        while time.time() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr else ""
                raise AssertionError(stderr)
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    return process
            except OSError:
                time.sleep(0.05)
        raise AssertionError("server did not start")

    def test_heartbeat_and_event_frame(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            port = free_port()
            process = self.start_server(root, port)
            sock = None
            try:
                sock = handshake(port)
                first = read_frame(sock)
                self.assertEqual(first["type"], "heartbeat")
                self.assertEqual(first["monitor"]["health"], "clear")

                event = {"schema_version": "aios.primitive_event.v1", "kind": "task.created", "payload": {"subject": "demo"}}
                with (root / ".aios" / "primitives" / "events.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(event) + "\n")

                seen = []
                deadline = time.time() + 3
                while time.time() < deadline:
                    frame = read_frame(sock)
                    seen.append(frame["type"])
                    if frame["type"] == "event":
                        self.assertEqual(frame["event"]["kind"], "task.created")
                        break
                self.assertIn("event", seen)
            finally:
                if sock is not None:
                    sock.close()
                process.terminate()
                process.wait(timeout=5)
                if process.stderr is not None:
                    process.stderr.close()

    def test_client_assets_include_simple_and_operator_modes(self) -> None:
        index = (ROOT / "apps" / "control" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "apps" / "control" / "app.js").read_text(encoding="utf-8")
        live = (ROOT / "apps" / "control" / "live.js").read_text(encoding="utf-8")
        self.assertIn('data-mode="simple"', index)
        self.assertIn('data-mode="operator"', index)
        self.assertIn("renderSimple", app)
        self.assertIn("WebSocket", live)


if __name__ == "__main__":
    unittest.main()
