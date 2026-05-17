import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import aios_gate_sleep


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_gate_sleep.py"


class AiosGateSleepTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        chat = root / ".aios" / "chat" / "demo"
        (chat / "gate_decisions").mkdir(parents=True)
        turn_id = "turn-a"
        (chat / "messages.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"turn_id": turn_id, "role": "user", "content": "오늘 날씨는 ?", "created_at": "2026-05-14T00:00:00+09:00"}),
                    json.dumps(
                        {
                            "turn_id": turn_id,
                            "role": "assistant",
                            "content": "어느 지역 날씨인지 알려줘.",
                            "substrate": "gate_clarification",
                            "route_reason": "gate_requires_input",
                            "created_at": "2026-05-14T00:00:01+09:00",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (chat / "gate_decisions" / f"{turn_id}.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.chat.gate_decision.v1",
                    "turn_id": turn_id,
                    "decision": "clarify_location",
                    "input_class": "current_info",
                    "route": "CapabilityOS.current_info",
                    "provider_execution": "held",
                    "missing_inputs": ["location"],
                }
            ),
            encoding="utf-8",
        )
        memory = root / "memoryOS" / "memory"
        memory.mkdir(parents=True)
        (memory / "objects.jsonl").write_text(
            json.dumps(
                {
                    "id": "mem_gate",
                    "status": "draft",
                    "project": "AIOS",
                    "type": "observation",
                    "content": "AIOS Gate should treat provider CLIs as substrates behind MemoryOS and CapabilityOS routing.",
                    "raw_refs": ["docs/AIOS_CHAT.md"],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (memory / "reviews.jsonl").write_text(
            json.dumps({"memory_object_id": "mem_gate", "new_status": "accepted"}) + "\n",
            encoding="utf-8",
        )

    def test_sleep_builds_loop_pairs_and_gate_pack(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_fixture(root)

            report = aios_gate_sleep.run_sleep(root, user="founder", pair_limit=20)

            self.assertEqual(report["schema_version"], "aios.gate.sleep_report.v1")
            self.assertEqual(report["source_pair_count"], 1)
            self.assertFalse(report["finetune_ready"])
            pack = json.loads((root / report["pack_path"]).read_text(encoding="utf-8"))
            self.assertEqual(pack["schema_version"], "aios.gate.pack.v1")
            self.assertTrue(pack["rules"]["current_info_requires_source"])
            self.assertTrue(pack["rules"]["provider_is_substrate_not_identity"])
            self.assertFalse(pack["rules"]["finetune_ready"])
            self.assertEqual(pack["accepted_memory_hints"][0]["id"], "mem_gate")
            pair_text = (root / report["pair_path"]).read_text(encoding="utf-8")
            self.assertIn("clarify_location", pair_text)
            self.assertNotIn("q1q1e3e3", json.dumps(pack, ensure_ascii=False).lower())

    def test_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.write_fixture(root)

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue((root / payload["pack_path"]).exists())


if __name__ == "__main__":
    unittest.main()
