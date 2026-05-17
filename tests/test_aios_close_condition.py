import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "aios_close_condition.py"
RETRO = ROOT / "scripts" / "aios_retro_close_classify.py"


class AiosCloseConditionTest(unittest.TestCase):
    def run_close(self, root: Path, contract: Path) -> dict:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), contract.as_posix(), "--root", root.as_posix(), "--json"],
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_file_exists_criterion_can_be_met(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "artifact.txt").write_text("ok", encoding="utf-8")
            contract = root / "docs" / "contracts" / "ASC-9999-test.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                """---
contract_id: ASC-9999
status: closed
---

# Test

Pass criteria:

- file_exists:artifact.txt
""",
                encoding="utf-8",
            )

            payload = self.run_close(root, contract)

        self.assertEqual(payload["met"], 1)
        self.assertEqual(payload["unmet"], 0)
        self.assertEqual(payload["recommended_close_type"], "closed_goal_met")

    def test_missing_file_criterion_is_unmet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract = root / "docs" / "contracts" / "ASC-9998-test.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                """---
contract_id: ASC-9998
status: closed
---

# Test

Pass criteria:

- file_exists:missing.txt
""",
                encoding="utf-8",
            )

            payload = self.run_close(root, contract)

        self.assertEqual(payload["unmet"], 1)
        self.assertEqual(payload["recommended_close_type"], "closed_goal_unmet_documented")

    def test_verification_gate_pass_criteria_is_preferred_over_explanatory_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "ok.txt").write_text("ok", encoding="utf-8")
            contract = root / "docs" / "contracts" / "ASC-9996-test.md"
            contract.parent.mkdir(parents=True)
            contract.write_text(
                """---
contract_id: ASC-9996
status: closed
---

# Test

This explains that pass criteria may appear in the contract body:

- explanatory bullet that must not be captured

## Verification Gate

```bash
true
```

Pass criteria:

- file_exists:ok.txt
""",
                encoding="utf-8",
            )

            payload = self.run_close(root, contract)

        self.assertEqual(len(payload["criteria"]), 1)
        self.assertEqual(payload["met"], 1)
        self.assertEqual(payload["manual"], 0)

    def test_asc_0110_is_not_classified_as_goal_met(self) -> None:
        payload = self.run_close(ROOT, ROOT / "docs" / "contracts" / "ASC-0110-memoryos-retrieval-broken.md")

        self.assertGreater(payload["unmet"], 0)
        self.assertIn(payload["recommended_close_type"], {"closed_partial_with_followup", "closed_goal_unmet_documented"})

    def test_retro_classifier_counts_closed_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contracts = root / "docs" / "contracts"
            contracts.mkdir(parents=True)
            (contracts / "ASC-9997-a.md").write_text(
                """---
contract_id: ASC-9997
status: closed
---

Pass criteria:

- file_exists:ok.txt
""",
                encoding="utf-8",
            )
            (root / "ok.txt").write_text("ok", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, RETRO.as_posix(), "--root", root.as_posix(), "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["goal_met"], 1)


if __name__ == "__main__":
    unittest.main()
