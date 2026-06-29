#!/usr/bin/env python3
"""Tests for aios_channel.py.

Covers:
  - RuntimeGate round-trip (inbox -> poll -> channel_once dispatch -> outbox)
  - Gate selection via AIOS_CHANNEL env
  - Allow-list enforcement (trust boundary)
  - notify() outbound-only path

No real network calls, no Telegram API, no aios_launcher subprocess.
All dispatch is injected as a hermetic mock function.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Load the channel module from scripts/
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load_channel():
    spec = importlib.util.spec_from_file_location(
        "aios_channel_under_test",
        SCRIPTS / "aios_channel.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_channel_under_test"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


ch = _load_channel()

InboundMsg = ch.InboundMsg
RuntimeGate = ch.RuntimeGate
TelegramGate = ch.TelegramGate
make_gate = ch.make_gate
channel_once = ch.channel_once
notify = ch.notify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockDispatch:
    """Hermetic dispatch mock: captures calls, returns a fixed reply."""

    def __init__(self, reply: str = "mock reply") -> None:
        self.calls: list[InboundMsg] = []
        self._reply = reply

    def __call__(self, msg: InboundMsg) -> str:
        self.calls.append(msg)
        return self._reply


def _make_gate(tmp: Path) -> RuntimeGate:
    return RuntimeGate(
        inbox_path=tmp / "inbox.jsonl",
        outbox_path=tmp / "outbox.jsonl",
    )


def _append_inbox(gate: RuntimeGate, chat_id: str, text: str) -> None:
    record = json.dumps({"chat_id": chat_id, "text": text, "ts": time.time()})
    with gate.inbox_path.open("a", encoding="utf-8") as fh:
        fh.write(record + "\n")


def _read_outbox(gate: RuntimeGate) -> list[dict]:
    if not gate.outbox_path.exists():
        return []
    lines = [ln.strip() for ln in gate.outbox_path.read_text().splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


# ---------------------------------------------------------------------------
# RuntimeGate round-trip
# ---------------------------------------------------------------------------


class TestRuntimeGateRoundTrip(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.gate = _make_gate(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_poll_returns_empty_when_no_inbox(self):
        msgs = self.gate.poll()
        self.assertEqual(msgs, [])

    def test_poll_returns_message_from_inbox(self):
        _append_inbox(self.gate, "c1", "hello")
        msgs = self.gate.poll()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].chat_id, "c1")
        self.assertEqual(msgs[0].text, "hello")

    def test_poll_does_not_replay_consumed_messages(self):
        _append_inbox(self.gate, "c1", "first")
        self.gate.poll()  # consume
        _append_inbox(self.gate, "c1", "second")
        msgs = self.gate.poll()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].text, "second")

    def test_channel_once_dispatches_and_writes_outbox(self):
        mock = MockDispatch("pong")
        _append_inbox(self.gate, "c1", "ping")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list=None, environ={})
        self.assertEqual(n, 1)
        self.assertEqual(len(mock.calls), 1)
        self.assertEqual(mock.calls[0].text, "ping")
        records = _read_outbox(self.gate)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["text"], "pong")
        self.assertEqual(records[0]["chat_id"], "c1")

    def test_channel_once_processes_multiple_messages(self):
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "c1", "msg1")
        _append_inbox(self.gate, "c1", "msg2")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list=None, environ={})
        self.assertEqual(n, 2)
        self.assertEqual(len(mock.calls), 2)
        records = _read_outbox(self.gate)
        self.assertEqual(len(records), 2)

    def test_send_appends_to_outbox(self):
        self.gate.send("c1", "hello from AIOS")
        records = _read_outbox(self.gate)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["chat_id"], "c1")
        self.assertEqual(records[0]["text"], "hello from AIOS")

    def test_malformed_inbox_line_is_skipped(self):
        # Write a broken line followed by a valid one
        with self.gate.inbox_path.open("a") as fh:
            fh.write("not-json\n")
            fh.write(json.dumps({"chat_id": "c1", "text": "valid"}) + "\n")
        msgs = self.gate.poll()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].text, "valid")


# ---------------------------------------------------------------------------
# Gate selection
# ---------------------------------------------------------------------------


class TestGateSelection(unittest.TestCase):
    def test_runtime_selection_returns_runtime_gate(self):
        gate = make_gate(environ={"AIOS_CHANNEL": "runtime"})
        self.assertIsNotNone(gate)
        self.assertIsInstance(gate, RuntimeGate)

    def test_none_selection_returns_none(self):
        gate = make_gate(environ={"AIOS_CHANNEL": "none"})
        self.assertIsNone(gate)

    def test_unset_aios_channel_is_inert(self):
        # Empty environ dict has no AIOS_CHANNEL key -> defaults to "none" (inert,
        # opt-in). The bridge is OFF until explicitly activated.
        gate = make_gate(environ={})
        self.assertIsNone(gate)

    def test_telegram_without_token_degrades_cleanly(self):
        # No AIOS_TELEGRAM_TOKEN -> returns None, does not raise
        gate = make_gate(environ={"AIOS_CHANNEL": "telegram"})
        self.assertIsNone(gate)

    def test_telegram_without_chat_id_fails_closed(self):
        # Token present but NO allow-list (AIOS_TELEGRAM_CHAT_ID) -> the remote
        # gate is refused (fail closed), NOT constructed wide-open. This is the
        # critical trust-boundary fix: a remote command surface must never run
        # unauthenticated.
        env = {
            "AIOS_CHANNEL": "telegram",
            "AIOS_TELEGRAM_TOKEN": "fake-token-for-test",
        }
        gate = make_gate(environ=env)
        self.assertIsNone(gate)

    def test_telegram_with_token_and_chat_id_returns_telegram_gate(self):
        env = {
            "AIOS_CHANNEL": "telegram",
            "AIOS_TELEGRAM_TOKEN": "fake-token-for-test",
            "AIOS_TELEGRAM_CHAT_ID": "founder-123",
        }
        gate = make_gate(environ=env)
        self.assertIsNotNone(gate)
        self.assertIsInstance(gate, TelegramGate)
        self.assertTrue(getattr(gate, "remote", False))  # remote gate marker

    def test_telegram_gate_does_not_expose_token_in_repr(self):
        env = {
            "AIOS_CHANNEL": "telegram",
            "AIOS_TELEGRAM_TOKEN": "secret-abc-123",
            "AIOS_TELEGRAM_CHAT_ID": "founder-123",
        }
        gate = make_gate(environ=env)
        assert gate is not None
        rep = repr(gate)
        self.assertNotIn("secret-abc-123", rep)


# ---------------------------------------------------------------------------
# Allow-list (trust boundary)
# ---------------------------------------------------------------------------


class TestAllowList(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.gate = _make_gate(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_allowed_chat_is_dispatched(self):
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "founder", "hello")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list={"founder"})
        self.assertEqual(n, 1)
        self.assertEqual(len(mock.calls), 1)

    def test_disallowed_chat_is_silently_rejected(self):
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "stranger", "hack attempt")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list={"founder"})
        self.assertEqual(n, 0)
        self.assertEqual(len(mock.calls), 0)
        # No reply sent to the disallowed chat
        self.assertEqual(_read_outbox(self.gate), [])

    def test_empty_allow_list_blocks_all_chats(self):
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "anyone", "hello")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list=set())
        self.assertEqual(n, 0)
        self.assertEqual(len(mock.calls), 0)

    def test_local_gate_none_allow_list_passes_all(self):
        # LOCAL (non-remote) gate + allow_list=None + no env -> no restriction.
        # The local runtime queue keeps its convenience (it already requires
        # local filesystem write access to drive).
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "anyone", "hello")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list=None, environ={})
        self.assertEqual(n, 1)
        self.assertEqual(len(mock.calls), 1)

    def test_remote_gate_none_allow_list_fails_closed(self):
        # CRITICAL trust-boundary: a REMOTE gate with no active allow-list must
        # drop ALL messages (fail closed), even if such a gate is constructed
        # outside make_gate(). Defense-in-depth beyond make_gate's refusal.
        class FakeRemoteGate:
            remote = True

            def __init__(self):
                self.sent = []

            def poll(self):
                return [InboundMsg(chat_id="stranger", text="hack")]

            def send(self, chat_id, text):
                self.sent.append((chat_id, text))

        mock = MockDispatch("ok")
        gate = FakeRemoteGate()
        n = channel_once(gate, dispatch_fn=mock, allow_list=None, environ={})
        self.assertEqual(n, 0)                 # nothing dispatched
        self.assertEqual(len(mock.calls), 0)
        self.assertEqual(gate.sent, [])        # no reply to the unauthorized chat

    def test_allow_list_from_env_is_respected(self):
        # allow_list=None but AIOS_TELEGRAM_CHAT_ID set in environ
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "founder", "hi")
        _append_inbox(self.gate, "stranger", "bye")
        environ = {"AIOS_TELEGRAM_CHAT_ID": "founder"}
        n = channel_once(self.gate, dispatch_fn=mock, allow_list=None, environ=environ)
        self.assertEqual(n, 1)
        self.assertEqual(mock.calls[0].chat_id, "founder")

    def test_mixed_allowed_and_blocked_in_one_poll(self):
        mock = MockDispatch("ok")
        _append_inbox(self.gate, "founder", "authorized")
        _append_inbox(self.gate, "bot", "spam")
        _append_inbox(self.gate, "founder", "also authorized")
        n = channel_once(self.gate, dispatch_fn=mock, allow_list={"founder"})
        self.assertEqual(n, 2)
        self.assertEqual(len(mock.calls), 2)
        texts = [c.text for c in mock.calls]
        self.assertIn("authorized", texts)
        self.assertIn("also authorized", texts)


# ---------------------------------------------------------------------------
# notify() outbound-only path
# ---------------------------------------------------------------------------


class TestNotifyOutbound(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.gate = _make_gate(Path(self._tmpdir.name))

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_notify_writes_to_outbox(self):
        notify("AIOS monitor alert: 3 tasks complete", self.gate, chat_id="founder")
        records = _read_outbox(self.gate)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["text"], "AIOS monitor alert: 3 tasks complete")
        self.assertEqual(records[0]["chat_id"], "founder")

    def test_notify_default_chat_id_is_local(self):
        notify("hello", self.gate)
        records = _read_outbox(self.gate)
        self.assertEqual(records[0]["chat_id"], "local")

    def test_notify_multiple_pushes_accumulate(self):
        notify("event 1", self.gate, chat_id="founder")
        notify("event 2", self.gate, chat_id="founder")
        records = _read_outbox(self.gate)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["text"], "event 1")
        self.assertEqual(records[1]["text"], "event 2")

    def test_notify_does_not_consume_inbox(self):
        _append_inbox(self.gate, "c1", "inbound")
        notify("outbound", self.gate)
        # inbox offset should not advance
        msgs = self.gate.poll()
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].text, "inbound")


class TestDispatchGuards(unittest.TestCase):
    """_default_dispatch argument-injection + empty-goal guards (no subprocess)."""

    def test_rejects_goal_starting_with_dash(self):
        # A goal that is a bare flag would be parsed as an option downstream
        # (e.g. --root / --base-url redirection). It must be rejected before
        # any subprocess dispatch.
        for evil in ("--root=/tmp/evil", "--base-url=http://attacker/v1", "-x"):
            out = ch._default_dispatch(InboundMsg(chat_id="founder", text="/do " + evil))
            self.assertIn("rejected", out)
            self.assertNotIn("output", out)  # never reached subprocess capture

    def test_rejects_leading_dash_for_plain_text_too(self):
        out = ch._default_dispatch(InboundMsg(chat_id="founder", text="--help"))
        self.assertIn("rejected", out)

    def test_empty_goal_is_not_dispatched(self):
        # An empty / whitespace-only message strips to "" -> empty goal guard
        # returns early (no subprocess). (A bare "/ask   " strips to "/ask" and
        # is treated as plain text, so the empty path is reached via "" itself.)
        for blank in ("", "   ", "\n\t"):
            out = ch._default_dispatch(InboundMsg(chat_id="founder", text=blank))
            self.assertIn("empty goal", out)


if __name__ == "__main__":
    unittest.main()
