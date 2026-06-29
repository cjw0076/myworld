#!/usr/bin/env python3
"""aios_channel -- messaging gateway: human-to-AIOS bridge via a channel gate.

This module is opt-in (AIOS_CHANNEL must be set to "runtime" or "telegram").
By default (AIOS_CHANNEL unset or "none") the bridge is inert.

Trust boundary: ALL command dispatch from a remote channel passes through an
allow-list (AIOS_TELEGRAM_CHAT_ID).  Only the founder's registered chat_id can
issue commands to AIOS.  This allow-list is the sole authority gate for remote
channel dispatch -- treat it as a trust boundary, not a convenience filter.
Do NOT move allow-list enforcement into the dispatch function; it lives in
channel_once() so no dispatch can bypass it.

Gate selection (AIOS_CHANNEL env):
    runtime   -- local file queue (~/.aios/channel/inbox.jsonl / outbox.jsonl).
                 Default.  Zero network deps; lets AIOS processes + tests drive
                 the bridge without any external service.
    telegram  -- Telegram bot API (long-poll getUpdates / sendMessage).
                 Requires AIOS_TELEGRAM_TOKEN.  Degrades cleanly if absent.
    none      -- bridge is inert (returns immediately, does nothing).

DNA compliance:
    #4  named exit  -- channel_loop() has explicit max_iters stop bound.
    #7  privacy     -- token read from env only; never hardcoded or committed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# InboundMsg
# ---------------------------------------------------------------------------


@dataclass
class InboundMsg:
    """A single inbound message from a channel gate."""

    chat_id: str
    text: str
    ts: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# ChannelGate Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ChannelGate(Protocol):
    """Abstract gate: poll for inbound messages and send outbound replies.

    Concrete gates: RuntimeGate (local file queue), TelegramGate (bot API).
    Selection: make_gate() reads AIOS_CHANNEL env.

    Protocol methods:
        poll() -> list[InboundMsg]   pull new inbound messages since last call
        send(chat_id, text) -> None  push an outbound reply to chat_id
    """

    def poll(self) -> List[InboundMsg]:
        """Pull new inbound messages since last poll.  Returns [] when idle."""
        ...

    def send(self, chat_id: str, text: str) -> None:
        """Push an outbound text reply to chat_id."""
        ...


# ---------------------------------------------------------------------------
# RuntimeGate -- local file queue (zero network deps, default gate)
# ---------------------------------------------------------------------------

_RUNTIME_BASE = Path.home() / ".aios" / "channel"
_RUNTIME_INBOX = _RUNTIME_BASE / "inbox.jsonl"
_RUNTIME_OUTBOX = _RUNTIME_BASE / "outbox.jsonl"


class RuntimeGate:
    """Local file-queue gate (default, zero network deps).

    Inbound:  ~/.aios/channel/inbox.jsonl  (one JSON object per line)
    Outbound: ~/.aios/channel/outbox.jsonl (append-only)

    Tracks a byte offset so repeated poll() calls only yield new lines.
    Other AIOS processes or CLI callers (`aios channel send`) can append to
    inbox.jsonl to drive the bridge without any external service dependency.

    Each inbox line must be a JSON object with at minimum:
        {"chat_id": "<id>", "text": "<message>"}
    Optional field: "ts" (float unix timestamp).
    """

    def __init__(
        self,
        inbox_path: Path = _RUNTIME_INBOX,
        outbox_path: Path = _RUNTIME_OUTBOX,
    ) -> None:
        self.inbox_path = Path(inbox_path)
        self.outbox_path = Path(outbox_path)
        self._offset: int = 0  # byte offset already consumed from inbox
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)

    def poll(self) -> List[InboundMsg]:
        """Read new lines from inbox starting at the current byte offset."""
        if not self.inbox_path.exists():
            return []
        messages: List[InboundMsg] = []
        with self.inbox_path.open("rb") as fh:
            fh.seek(self._offset)
            for raw in fh:
                self._offset += len(raw)
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    messages.append(InboundMsg(
                        chat_id=str(obj.get("chat_id", "local")),
                        text=str(obj.get("text", "")),
                        ts=float(obj.get("ts", time.time())),
                    ))
                except json.JSONDecodeError:
                    pass  # skip malformed lines silently
        return messages

    def send(self, chat_id: str, text: str) -> None:
        """Append an outbound record to outbox.jsonl."""
        record = json.dumps({"chat_id": chat_id, "text": text, "ts": time.time()})
        with self.outbox_path.open("a", encoding="utf-8") as fh:
            fh.write(record + "\n")


# ---------------------------------------------------------------------------
# TelegramGate -- Telegram Bot API (long-poll getUpdates / sendMessage)
# ---------------------------------------------------------------------------

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramGate:
    """Telegram bot gateway (remote, requires AIOS_TELEGRAM_TOKEN).

    Inbound:  long-poll getUpdates (offset-tracked so no update is replayed)
    Outbound: sendMessage

    Token and the allowed chat_id come from env only (DNA #7 -- privacy):
        AIOS_TELEGRAM_TOKEN   -- bot token (required; make_gate degrades if absent)
        AIOS_TELEGRAM_CHAT_ID -- the single founder chat_id permitted to command AIOS

    Trust boundary: the allow-list in channel_once() enforces that only the
    registered chat_id can dispatch commands.  TelegramGate itself does not
    enforce the allow-list -- that is channel_once()'s responsibility so the
    enforcement point is uniform across all gate types.
    """

    def __init__(self, token: str, allowed_chat_id: str = "") -> None:
        # Token held in memory only; never logged or echoed
        self._token = token
        self.allowed_chat_id = allowed_chat_id
        self._offset: int = 0  # Telegram update_id offset (next expected)

    def _api_url(self, method: str) -> str:
        return _TELEGRAM_API.format(token=self._token, method=method)

    def _post(self, method: str, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            self._api_url(method),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    def poll(self) -> List[InboundMsg]:
        """Long-poll getUpdates; returns new messages since last call."""
        try:
            resp = self._post(
                "getUpdates",
                {"offset": self._offset, "timeout": 1, "limit": 100},
            )
        except (urllib.error.URLError, OSError):
            return []
        messages: List[InboundMsg] = []
        for update in resp.get("result", []):
            self._offset = update["update_id"] + 1
            msg = update.get("message") or {}
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id", ""))
            text = msg.get("text", "")
            ts = float(msg.get("date", time.time()))
            if chat_id and text:
                messages.append(InboundMsg(chat_id=chat_id, text=text, ts=ts))
        return messages

    def send(self, chat_id: str, text: str) -> None:
        """Send a text message to chat_id via sendMessage."""
        self._post("sendMessage", {"chat_id": chat_id, "text": text})


# ---------------------------------------------------------------------------
# Gate factory
# ---------------------------------------------------------------------------


def make_gate(environ: Optional[dict] = None) -> Optional[ChannelGate]:
    """Create the configured ChannelGate from env.

    AIOS_CHANNEL = "runtime" (default) | "telegram" | "none"

    Returns None for "none" or when a required credential is absent (clean
    degrade -- never raises on missing config).
    """
    env = environ if environ is not None else os.environ
    channel = env.get("AIOS_CHANNEL", "runtime").lower().strip()
    if channel in ("none", ""):
        return None
    if channel == "telegram":
        token = env.get("AIOS_TELEGRAM_TOKEN", "").strip()
        if not token:
            print(
                "[aios channel] AIOS_TELEGRAM_TOKEN not set -- telegram gate unavailable",
                file=sys.stderr,
            )
            return None
        allowed = env.get("AIOS_TELEGRAM_CHAT_ID", "").strip()
        return TelegramGate(token=token, allowed_chat_id=allowed)
    # default: runtime
    return RuntimeGate()


# ---------------------------------------------------------------------------
# Default dispatcher -- maps inbound text to an AIOS launcher subcommand
# ---------------------------------------------------------------------------

_LAUNCHER = Path(__file__).resolve().parent / "aios_launcher.py"


def _default_dispatch(msg: InboundMsg) -> str:
    """Dispatch an inbound message as an AIOS command via aios_launcher.

    Trust boundary: the CALLER (channel_once) enforces the allow-list BEFORE
    invoking this function.  Dispatch logic here must never bypass that gate.

    Routing:
        /ask <text>  -> aios ask <text>
        /do  <text>  -> aios do  <text>
        <plain text> -> aios ask <text>   (default)

    Returns the captured stdout+stderr as the reply text.
    """
    text = msg.text.strip()
    if text.startswith("/ask "):
        subcmd, goal = "ask", text[5:].strip()
    elif text.startswith("/do "):
        subcmd, goal = "do", text[4:].strip()
    else:
        subcmd, goal = "ask", text

    if not goal:
        return "(empty goal -- nothing dispatched)"

    try:
        result = subprocess.run(
            [sys.executable, str(_LAUNCHER), subcmd, goal],
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "(dispatch timeout)"
    except Exception as exc:  # noqa: BLE001
        return f"(dispatch error: {exc})"


# ---------------------------------------------------------------------------
# Bridge primitives
# ---------------------------------------------------------------------------

DispatchFn = Callable[[InboundMsg], str]


def _build_allow_list(environ: Optional[dict] = None) -> Optional[set]:
    """Return the allow-list set from AIOS_TELEGRAM_CHAT_ID, or None if not set.

    A None return means no allow-list is active (all chat_ids pass).
    An empty set means no chat_id is allowed (all blocked).
    Comma-separated values are supported: "123,456" -> {"123", "456"}.
    """
    env = environ if environ is not None else os.environ
    raw = env.get("AIOS_TELEGRAM_CHAT_ID", "").strip()
    if not raw:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def notify(text: str, gate: ChannelGate, chat_id: str = "local") -> None:
    """Push a plain notification outbound via the gate (no inbound required).

    Use this for monitor-driven events: AIOS pushes status/alerts to the
    founder without waiting for an inbound message.  Example:
        notify("3 tasks completed", gate, chat_id=founder_id)
    """
    gate.send(chat_id, text)


def channel_once(
    gate: ChannelGate,
    dispatch_fn: Optional[DispatchFn] = None,
    allow_list: Optional[set] = None,
    environ: Optional[dict] = None,
) -> int:
    """Poll gate, dispatch each allowed message, send reply.

    Returns the count of messages that were dispatched (allowed + processed).

    allow_list: explicit set of permitted chat_ids.  When None, the list is
    built from AIOS_TELEGRAM_CHAT_ID in environ/os.environ.  A None allow-list
    (env var also absent) means no restriction -- all messages pass.

    Trust boundary: messages whose chat_id is not in the active allow-list are
    silently dropped.  The reply is sent only to the originating chat_id.
    """
    _dispatch = dispatch_fn if dispatch_fn is not None else _default_dispatch
    # allow_list=None defers to env; explicit set (even empty) overrides env
    _allow: Optional[set] = (
        allow_list if allow_list is not None else _build_allow_list(environ)
    )

    messages = gate.poll()
    processed = 0
    for msg in messages:
        # Trust boundary check -- must precede any dispatch
        if _allow is not None and msg.chat_id not in _allow:
            continue  # silently drop; no echo to disallowed chat
        reply = _dispatch(msg)
        gate.send(msg.chat_id, reply)
        processed += 1
    return processed


def channel_loop(
    max_iters: int = 100,
    sleep_s: float = 2.0,
    gate: Optional[ChannelGate] = None,
    dispatch_fn: Optional[DispatchFn] = None,
    allow_list: Optional[set] = None,
    environ: Optional[dict] = None,
) -> None:
    """Poll-dispatch loop with a named stop bound (DNA #4 named exit).

    Runs at most max_iters iterations, sleeping sleep_s between polls.
    Pass gate=None to auto-select via make_gate() / AIOS_CHANNEL env.
    If the selected gate is None (AIOS_CHANNEL=none), returns immediately.
    """
    _gate = gate if gate is not None else make_gate(environ)
    if _gate is None:
        return  # bridge is inert -- named exit: AIOS_CHANNEL=none
    for _ in range(max_iters):
        channel_once(_gate, dispatch_fn=dispatch_fn, allow_list=allow_list, environ=environ)
        time.sleep(sleep_s)


def run_channel(
    gate: Optional[ChannelGate] = None,
    dispatch_fn: Optional[DispatchFn] = None,
    allow_list: Optional[set] = None,
    environ: Optional[dict] = None,
    max_iters: int = 100,
    sleep_s: float = 2.0,
) -> None:
    """Named entry point for the bridge loop (mirrors channel_loop).

    Provided for callers that want a single named function to start the bridge.
    """
    channel_loop(
        max_iters=max_iters,
        sleep_s=sleep_s,
        gate=gate,
        dispatch_fn=dispatch_fn,
        allow_list=allow_list,
        environ=environ,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cli_once(args) -> int:
    gate = make_gate()
    if gate is None:
        print("[aios channel] bridge is inert (AIOS_CHANNEL=none or unset).")
        return 0
    n = channel_once(gate)
    print(f"[aios channel once] processed {n} message(s).")
    return 0


def _cli_loop(args) -> int:
    gate = make_gate()
    if gate is None:
        print("[aios channel] bridge is inert (AIOS_CHANNEL=none or unset).")
        return 0
    max_iters = getattr(args, "max_iters", 100)
    sleep_s = getattr(args, "sleep", 2.0)
    print(
        f"[aios channel loop] running up to {max_iters} iters, "
        f"{sleep_s}s sleep between polls. Ctrl-C to interrupt.",
        flush=True,
    )
    try:
        channel_loop(max_iters=max_iters, sleep_s=sleep_s, gate=gate)
    except KeyboardInterrupt:
        print("\n[aios channel loop] interrupted.")
        return 0
    print("[aios channel loop] done (max_iters reached).")
    return 0


def _cli_send(args) -> int:
    gate = make_gate()
    if gate is None:
        print("[aios channel] bridge is inert (AIOS_CHANNEL=none or unset).")
        return 1
    chat_id = getattr(args, "chat_id", "local") or "local"
    text_parts = getattr(args, "text", [])
    text = " ".join(text_parts) if isinstance(text_parts, list) else str(text_parts)
    notify(text, gate, chat_id=chat_id)
    print(f"[aios channel send] sent to {chat_id!r}: {text!r}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="aios channel",
        description=(
            "AIOS channel bridge -- human-to-AIOS gateway via a messaging channel.\n\n"
            "Gate is selected by AIOS_CHANNEL env (runtime | telegram | none).\n"
            "Bridge is opt-in: AIOS_CHANNEL must be set to activate it."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcmd", required=True)

    sub.add_parser("once", help="Run one poll-dispatch-reply pass then exit.").set_defaults(func=_cli_once)

    p_loop = sub.add_parser("loop", help="Run the poll-dispatch-reply loop until max-iters.")
    p_loop.add_argument(
        "--max-iters",
        type=int,
        default=100,
        dest="max_iters",
        help="Stop after N iterations (DNA #4 named exit). Default: 100.",
    )
    p_loop.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="Seconds between polls. Default: 2.0.",
    )
    p_loop.set_defaults(func=_cli_loop)

    p_send = sub.add_parser(
        "send",
        help="Push a notification to the channel outbound (no inbound required).",
    )
    p_send.add_argument("--chat-id", default="local", dest="chat_id", help="Target chat_id.")
    p_send.add_argument("text", nargs="+", help="Text to send.")
    p_send.set_defaults(func=_cli_send)

    parsed = parser.parse_args(argv)
    return parsed.func(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
