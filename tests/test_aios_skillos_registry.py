import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_skillos_registry.py"


def touch(root: Path, rel: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# fixture\n", encoding="utf-8")


class AiosSkillosRegistryTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--json", *args],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_registry_is_recommendation_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self.run_cli(Path(tmp), "list")

            self.assertEqual(payload["schema_version"], "aios.skillos_registry.v1")
            self.assertTrue(payload["recommendation_only"])
            self.assertFalse(payload["execution_enabled"])
            self.assertTrue(payload["cards"])
            self.assertTrue(all(card["authority"] == "recommendation_only" for card in payload["cards"]))
            self.assertTrue(all(card["execution_enabled"] is False for card in payload["cards"]))

    def test_existing_markers_make_card_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root, "scripts/aios_world_readiness.py")
            touch(root, "docs/contracts/ASC-0235-world-deployment-readiness-cli.md")

            payload = self.run_cli(root, "list")
            by_id = {card["id"]: card for card in payload["cards"]}

            self.assertEqual(by_id["skill_world_readiness_gate"]["status"], "available")
            self.assertEqual(by_id["skill_credential_broker"]["status"], "partial")

    def test_recommendation_ranks_matching_domain(self) -> None:
        payload = self.run_cli(
            ROOT,
            "recommend",
            "--task",
            "need credential vault privacy broker for provider",
            "--limit",
            "2",
        )

        self.assertFalse(payload["execution_enabled"])
        self.assertEqual(payload["recommendations"][0]["id"], "skill_credential_broker")
        self.assertIn("skillos_executes_tool", payload["stop_conditions"])


if __name__ == "__main__":
    unittest.main()
