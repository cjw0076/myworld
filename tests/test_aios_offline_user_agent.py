from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import aios_offline_user_agent as offline  # noqa: E402


SCRIPT = SCRIPTS / "aios_offline_user_agent.py"


class OfflineUserAgentPacketTest(unittest.TestCase):
    def test_frontier_question_requires_routes_and_stays_draft_first(self):
        packet = offline.unknown_frontier_question(
            question="Which campus interaction should Uri test first?",
            why_known_context_is_insufficient="Internal taste is not enough.",
            risk_if_we_guess="We may build a polished flow nobody wants.",
            candidate_routes=["GenesisOS challenge", "CapabilityOS web route", "user@offline observation"],
            stop_condition="One target-user observation and one contradiction check exist.",
        )
        result = offline.validate_packet(packet)
        self.assertTrue(result["ok"], result)
        self.assertEqual(packet["review_policy"]["draft_first"], True)
        self.assertEqual(packet["review_policy"]["auto_accept"], False)

    def test_offline_task_accepts_boundary_language(self):
        packet = offline.user_offline_task(
            task="Open the Uri campus screen and note where your eye stops first.",
            time_budget="3 minutes",
            what_to_observe="First hesitation point, confusing label, and one desired tap.",
            what_not_to_share="Do not paste messages, credentials, screenshots with private data, or raw files.",
            return_format="Three bullets: first hesitation / desired action / one fix.",
            privacy_boundary="Private data and raw screenshots stay offline; only a summary enters AIOS.",
        )
        result = offline.validate_packet(packet)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["warnings"], [])

    def test_sensitive_terms_are_rejected_outside_boundary_fields(self):
        packet = offline.user_offline_task(
            task="Paste your .env token so AIOS can inspect it.",
            time_budget="1 minute",
            what_to_observe="Whether the hidden credential works.",
            what_not_to_share="Do not share secrets.",
            return_format="short answer",
            privacy_boundary="Private data stays offline.",
        )
        result = offline.validate_packet(packet)
        self.assertFalse(result["ok"])
        self.assertTrue(any("sensitive/private term" in error for error in result["errors"]))

    def test_field_observation_must_not_include_private_data(self):
        packet = offline.field_observation(
            observed_at="2026-05-20T18:00:00+09:00",
            summary="Target user understood the map faster than the dashboard.",
            confidence=0.7,
            next_question="Should the campus entry start from the map?",
        )
        self.assertTrue(offline.validate_packet(packet)["ok"])
        packet["private_data_included"] = True
        result = offline.validate_packet(packet)
        self.assertFalse(result["ok"])
        self.assertIn("field_observation.private_data_included must be false", result["errors"])

    def test_write_packet_lands_in_memoryos_inbox(self):
        with tempfile.TemporaryDirectory(prefix="aios_offline_") as tmp:
            root = Path(tmp)
            packet = offline.user_offline_task(
                task="Ask one student which first screen feels usable.",
                time_budget="5 minutes",
                what_to_observe="Which entry card they tap first and why.",
                what_not_to_share="Do not share their name, contact, private chat, or raw photo.",
                return_format="anonymous summary only",
                privacy_boundary="Private identifying data and raw notes stay offline.",
            )
            path = offline.write_packet(root, packet)
            self.assertEqual(path.parent, root / ".aios" / "inbox" / "memoryOS")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["packet_type"], "user.offline_task")

    def test_field_observation_writes_visible_memory_draft(self):
        with tempfile.TemporaryDirectory(prefix="aios_offline_") as tmp:
            root = Path(tmp)
            packet = offline.field_observation(
                observed_at="2026-05-20T18:20:00+09:00",
                summary="Target user understood the offline-user card but wanted the privacy boundary closer to the button.",
                confidence=0.72,
                next_question="Should the boundary be visually attached to Prepare Reply?",
            )
            packet_path = offline.write_packet(root, packet)
            draft_path = offline.append_field_observation_memory_draft(root, packet_path, packet)

            self.assertEqual(draft_path, root / ".aios" / "chat" / "offline-user" / "memory_drafts.json")
            payload = json.loads(draft_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "aios.chat.memory_drafts.v1")
            self.assertEqual(payload["conversation_id"], "offline-user")
            self.assertEqual(len(payload["memory_drafts"]), 1)
            draft = payload["memory_drafts"][0]
            self.assertEqual(draft["type"], "field_observation")
            self.assertEqual(draft["origin"], "offline_user_agent")
            self.assertEqual(draft["status"], "draft")
            self.assertEqual(draft["provenance"]["observed_by"], "user@offline")
            self.assertFalse(draft["provenance"]["private_data_included"])
            self.assertEqual(draft["raw_refs"], [".aios/inbox/memoryOS/asc-0210.field_observation.target-user-understood-the-offline-user-card-but-wanted-the-priv.json"])

    def test_cli_dry_run_outputs_valid_packet(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "new-offline-task",
                "--task",
                "Look at the current screen and name the first confusing element.",
                "--time-budget",
                "2 minutes",
                "--observe",
                "Visual hesitation only.",
                "--not-share",
                "Do not share private messages or raw screenshots.",
                "--return-format",
                "one sentence",
                "--privacy-boundary",
                "Private data and raw screenshots stay offline.",
                "--dry-run",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["validation"]["ok"])
        self.assertEqual(payload["packet"]["packet_type"], "user.offline_task")

    def test_cli_field_observation_outputs_memory_draft_preview(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "new-field-observation",
                "--summary",
                "Student hesitated on the privacy boundary copy but understood the action.",
                "--confidence",
                "0.64",
                "--next-question",
                "Should the boundary copy move above the CTA?",
                "--observed-at",
                "2026-05-20T18:21:00+09:00",
                "--dry-run",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["validation"]["ok"])
        self.assertEqual(payload["packet"]["packet_type"], "field_observation")
        self.assertEqual(payload["memory_draft"]["type"], "field_observation")
        self.assertEqual(payload["memory_draft"]["origin"], "offline_user_agent")


if __name__ == "__main__":
    unittest.main()
