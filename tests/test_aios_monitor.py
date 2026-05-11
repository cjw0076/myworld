import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_monitor.py"


class AiosMonitorTest(unittest.TestCase):
    def test_snapshot_reports_contract_status_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            contract = contract_dir / "ASC-0001-test.md"
            contract.write_text(
                "---\ncontract_id: ASC-0001\nstatus: closed\naccepted: now\nclosed: now\n---\n",
                encoding="utf-8",
            )
            state = root / ".aios" / "state"
            state.mkdir(parents=True)
            (state / "dispatches.jsonl").write_text(
                json.dumps(
                    {
                        "event": "created",
                        "dispatch_id": "asc-0001",
                        "contract_id": "ASC-0001",
                        "contract_path": "docs/contracts/ASC-0001-test.md",
                        "contract_status": "proposed",
                        "status": "created",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, SCRIPT.as_posix(), "snapshot", "--json"],
                cwd=root,
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(result.stdout)

            codes = {alert["code"] for alert in payload["alerts"]}
            self.assertIn("dispatch_contract_status_stale", codes)


if __name__ == "__main__":
    unittest.main()
