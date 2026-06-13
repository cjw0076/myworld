#!/usr/bin/env python3
"""AIOS Serving API — minimal HTTP server for the end-user serving UI.

Serves apps/serving/index.html and POST /run which invokes the organic pipeline.
Intentionally zero-dependency (stdlib only) to avoid install friction.

Usage:
  python3 scripts/aios_serving_api.py --port 8741 [--host 127.0.0.1]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SERVING_DIR = ROOT / "apps" / "serving"
SCRIPTS_DIR = ROOT / "scripts"


def _import_head():
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import importlib.util
    spec = importlib.util.spec_from_file_location("aios_head", SCRIPTS_DIR / "aios_head.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_organic(goal: str, provider: str, max_turns: int) -> dict:
    head = _import_head()
    adapters = head._default_adapters(provider)
    if provider not in adapters:
        return {"error": f"provider '{provider}' not available", "exit": "no_provider"}
    sampler = head.make_provider_sampler(provider, adapters)
    return head.run_organic_goal(goal, sampler=sampler, max_turns=max_turns, root=ROOT)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[aios-serving] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_file(SERVING_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/health":
            self._json({"status": "ok", "service": "aios_serving_api"})
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/run":
            self.send_error(404, "Not found")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        goal = str(body.get("goal", "")).strip()
        if not goal:
            self._json({"error": "goal required"}, status=400)
            return
        provider = str(body.get("provider", "claude"))
        max_turns = int(body.get("max_turns", 12))

        result = run_organic(goal, provider, max_turns)
        self._json(result)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404, f"File not found: {path.name}")
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj: dict, status: int = 200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8741) -> None:
    server = HTTPServer((host, port), Handler)
    print(f"[aios-serving] http://{host}:{port}/  (Ctrl-C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[aios-serving] stopped")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8741)
    parser.add_argument("--check", action="store_true",
                        help="verify static files exist and exit (for CI)")
    args = parser.parse_args(argv)

    if args.check:
        missing = [f for f in [SERVING_DIR / "index.html"] if not f.exists()]
        if missing:
            print(json.dumps({"status": "fail", "missing": [str(m) for m in missing]}))
            return 1
        print(json.dumps({"status": "ok", "serving_dir": str(SERVING_DIR)}))
        return 0

    serve(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
