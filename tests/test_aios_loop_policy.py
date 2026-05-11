import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_loop_policy.py"


RADAR = """# AIOS Task Radar

## Top Task Signals

| Score | Domain | Path | Signals | Candidate Task |
| ---: | --- | --- | --- | --- |
| 90 | myworld | `myworld/docs/TODO.md` | `aios:2,verify:1` | promote this control-plane signal into an AIOS contract or readiness gate |
| 80 | _from_desktop | `_from_desktop/Uri/docs/TODO.md` | `p0:2,next:1` | triage as external workspace context before importing into AIOS |
| 70 | hivemind | `myworld/hivemind/docs/TODO.md` | `capabilityos:9,hivemind:4` | issue a Hive Mind packet for execution, harness, or verification follow-up |
"""


class AiosLoopPolicyTest(unittest.TestCase):
    def run_policy(self, root: Path, *args: str) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), "--json", *args],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_policy_accepts_when_capacity_available_and_holds_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")

            data = self.run_policy(root, "--capacity", "4")

            self.assertEqual(data["schema_version"], "aios.loop_policy.v1")
            by_path = {row["sources"][0]["path"]: row for row in data["decisions"]}
            self.assertEqual(by_path["myworld/docs/TODO.md"]["decision"], "accept_now")
            self.assertEqual(by_path["_from_desktop/Uri/docs/TODO.md"]["decision"], "hold_for_operator")
            self.assertEqual(by_path["myworld/hivemind/docs/TODO.md"]["decision"], "hold_for_capability")

    def test_policy_holds_for_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
            for idx in range(4):
                (contract_dir / f"ASC-10{idx}.md").write_text(
                    "---\nstatus: accepted\n---\n",
                    encoding="utf-8",
                )

            data = self.run_policy(root, "--capacity", "4")

            by_path = {row["sources"][0]["path"]: row for row in data["decisions"]}
            self.assertEqual(by_path["myworld/docs/TODO.md"]["decision"], "hold_for_capacity")
            self.assertEqual(data["open_contract_count"], 4)


if __name__ == "__main__":
    unittest.main()
