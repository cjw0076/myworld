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
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SERVING_DIR = ROOT / "apps" / "serving"
SCRIPTS_DIR = ROOT / "scripts"

_GOAL_MAX_LEN = 2000
_GOAL_INJECTION_PATTERNS = (
    "_from_desktop", "dain/", "minyoung/", "/etc/passwd", "/etc/shadow",
    "~/.ssh", "/.env", "ignore previous", "ignore all instructions",
    "system prompt", "print your api key",
)


_RATE_WINDOW = 60        # sliding window seconds
_RATE_MAX_REQUESTS = 10  # max requests per IP per window
_rate_lock = threading.Lock()
_rate_buckets: defaultdict[str, deque] = defaultdict(deque)


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limit exceeded."""
    now = time.monotonic()
    with _rate_lock:
        bucket = _rate_buckets[ip]
        while bucket and now - bucket[0] > _RATE_WINDOW:
            bucket.popleft()
        if len(bucket) >= _RATE_MAX_REQUESTS:
            return False
        bucket.append(now)
        return True


_SESSION_TTL = 3600      # sessions expire after 1 hour of inactivity
_SESSION_MAX_TURNS = 3   # carry forward last N goal/answer pairs
_session_lock = threading.Lock()
_sessions: dict[str, dict] = {}   # session_id → {turns: [...], last_seen: float}


def _session_push(session_id: str, goal: str, answer: str) -> None:
    """Append a goal+answer pair to the session history."""
    now = time.monotonic()
    with _session_lock:
        # Prune expired sessions opportunistically
        expired = [k for k, v in _sessions.items() if now - v["last_seen"] > _SESSION_TTL]
        for k in expired:
            del _sessions[k]
        sess = _sessions.setdefault(session_id, {"turns": [], "last_seen": now})
        sess["last_seen"] = now
        sess["turns"].append({"goal": goal[:300], "answer": answer[:500]})
        sess["turns"] = sess["turns"][-_SESSION_MAX_TURNS:]


def _session_context(session_id: str | None) -> str:
    """Return a compact prior-conversation context string for the synthesis prompt."""
    if not session_id:
        return ""
    with _session_lock:
        sess = _sessions.get(session_id)
    if not sess or not sess["turns"]:
        return ""
    lines = ["Prior conversation in this session:"]
    for t in sess["turns"]:
        lines.append(f"  Q: {t['goal']}")
        if t["answer"]:
            lines.append(f"  A: {t['answer']}")
    return "\n".join(lines)


def _validate_goal(goal: str) -> str | None:
    """Return error string if goal is rejected, else None."""
    if len(goal) > _GOAL_MAX_LEN:
        return f"goal too long (max {_GOAL_MAX_LEN} chars)"
    lower = goal.lower()
    for pattern in _GOAL_INJECTION_PATTERNS:
        if pattern in lower:
            return f"goal contains disallowed pattern"
    return None


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
    # "auto" builds a multi-model adapter set and routes per-goal; skip the single-key check
    if provider != "auto" and provider not in adapters:
        return {"error": f"provider '{provider}' not available", "exit": "no_provider"}
    sampler = head.make_provider_sampler(provider, adapters, goal=goal)
    return head.run_organic_goal(goal, sampler=sampler, max_turns=max_turns, root=ROOT)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # Required for SSE — HTTP/1.0 drops chunked streams

    def log_message(self, fmt, *args):
        print(f"[aios-serving] {self.address_string()} {fmt % args}", flush=True)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._serve_file(SERVING_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/health":
            self._json({"status": "ok", "service": "aios_serving_api"})
        elif path == "/status":
            with _rate_lock:
                active_ips = len(_rate_buckets)
            with _session_lock:
                active_sessions = len(_sessions)
            self._json({
                "status": "ok", "service": "aios_serving_api",
                "active_ips_rate_tracked": active_ips,
                "active_sessions": active_sessions,
                "rate_limit": f"{_RATE_MAX_REQUESTS} req/{_RATE_WINDOW}s per IP",
                "session_ttl_seconds": _SESSION_TTL,
            })
        elif path in ("/favicon.ico", "/.well-known/appspecific/com.chrome.devtools.json"):
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/run":
            self._handle_run()
        elif path == "/run/stream":
            self._handle_run_stream()
        else:
            self.send_error(404, "Not found")

    def _parse_run_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return None

    def _handle_run(self):
        """Blocking POST /run — waits for completion, returns full result with synthesis."""
        if not _check_rate_limit(self.client_address[0]):
            self._json({"error": "rate limit exceeded — 10 requests per minute"}, status=429)
            return
        body = self._parse_run_body()
        if body is None:
            return
        goal = str(body.get("goal", "")).strip()
        if not goal:
            self._json({"error": "goal required"}, status=400)
            return
        err = _validate_goal(goal)
        if err:
            self._json({"error": err, "rejected": True}, status=400)
            return
        session_id = str(body.get("session_id", "")).strip()[:64] or None
        prior_ctx = _session_context(session_id)
        result = run_organic(goal, str(body.get("provider", "claude")),
                             int(body.get("max_turns", 6)))
        # Add synthesis so API callers get a usable answer (same as streaming path)
        head = _import_head()
        preamble_data = head._organ_preamble(goal, ROOT)
        final_answer = head._organ_synthesis(goal, result, preamble=preamble_data,
                                             root=ROOT, prior_context=prior_ctx)
        if final_answer:
            result["final_answer"] = final_answer
        if session_id and final_answer:
            _session_push(session_id, goal, final_answer)
        self._json(result)

    def _handle_run_stream(self):
        """Streaming POST /run/stream — sends Server-Sent Events as turns complete.
        Rate-limited: 10 requests per IP per minute.

        Network pattern: chunked streaming (like TCP window updates) so the browser
        renders progress incrementally instead of blocking until the full run finishes.
        Each turn emits one SSE event; the final event includes the full result.
        """
        if not _check_rate_limit(self.client_address[0]):
            self._json({"error": "rate limit exceeded — 10 requests per minute"}, status=429)
            return
        body = self._parse_run_body()
        if body is None:
            return
        goal = str(body.get("goal", "")).strip()
        if not goal:
            self._json({"error": "goal required"}, status=400)
            return
        err = _validate_goal(goal)
        if err:
            self._json({"error": err, "rejected": True}, status=400)
            return
        provider = str(body.get("provider", "claude"))
        max_turns = int(body.get("max_turns", 6))
        session_id = str(body.get("session_id", "")).strip()[:64] or None
        prior_ctx = _session_context(session_id)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")        # close after done event, no keep-alive
        self.send_header("X-Accel-Buffering", "no")   # disable nginx buffering if proxied
        self._cors_headers()
        self.end_headers()

        def emit(event: str, data: dict) -> None:
            line = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            try:
                self.wfile.write(line.encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        emit("start", {"goal": goal[:120], "provider": provider, "max_turns": max_turns})

        head = _import_head()
        # auto provider: pick qwen3:8b vs 1.7b based on goal complexity
        actual_provider = head._auto_provider(goal) if provider == "auto" else provider
        adapters = head._default_adapters(provider)
        if actual_provider not in adapters:
            # Fall back gracefully if chosen model unavailable
            actual_provider = "ollama_rest" if "ollama_rest" in adapters else provider
        if actual_provider not in adapters:
            emit("error", {"error": f"provider '{provider}' not available"})
            return

        # Turn-level streaming: emit each turn as it completes (network: packet-by-packet)
        turn_events: list[dict] = []

        def streaming_turn_sink(rec: dict) -> None:
            if rec.get("kind") == "trajectory":
                turn_events.append(rec)
                emit("turn", {"turn": rec.get("turn"), "tool": rec.get("tool"),
                              "status": rec.get("status"), "decision": rec.get("decision")})

        from pathlib import Path
        root = Path(__file__).resolve().parents[1]

        import datetime as _dt
        run_id = f"stream-{_dt.datetime.now(_dt.timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        rl_mod = head._load("aios_run_log")
        run_log = rl_mod.RunLog(run_id=run_id, agent="codex@myworld",
                                runs_dir=root / ".aios" / "runs")
        run_log.open(ts=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"))

        def combined_sink(rec: dict) -> None:
            run_log.sink(rec)
            streaming_turn_sink(rec)

        preamble_data = head._organ_preamble(goal, root)
        emit("preamble", preamble_data)

        try:
            sampler = head.make_provider_sampler(actual_provider, adapters, goal=goal)
            result = head.run_loop_goal(goal, sampler=sampler, max_turns=max_turns,
                                        turn_sink=combined_sink)
            # Synthesis step: generate a concise final answer using fast local LLM
            final_answer = head._organ_synthesis(goal, result, preamble=preamble_data,
                                                 root=root, prior_context=prior_ctx)
            if final_answer:
                result["final_answer"] = final_answer
            # Save to session so next request in the same session has context
            if session_id and final_answer:
                _session_push(session_id, goal, final_answer)
            postamble = head._organ_postamble(goal, result, root, run_id=run_id)
            result["run_id"] = run_id
            result["organic_pipeline"] = {"preamble": preamble_data, "postamble": postamble}
            emit("done", result)
        except Exception as _exc:
            emit("error", {"error": str(_exc)[:200], "phase": "run_loop"})

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
    # ThreadingHTTPServer: each request gets its own thread — LLM calls don't block other requests
    server = ThreadingHTTPServer((host, port), Handler)
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
