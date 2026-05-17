import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_loop_policy.py"


RADAR = """# AIOS Task Radar

## Top Task Signals

| Score | Domain | Path | Signals | Candidate Task |
| ---: | --- | --- | --- | --- |
| 90 | myworld | `myworld/docs/TODO.md` | `aios:2,verify:1` | promote this control-plane signal into an AIOS contract or readiness gate |
| 85 | myworld | `myworld/docs/contracts/ASC-0001-closed.md` | `aios:12,contract:12,verify:12` | promote this control-plane signal into an AIOS contract or readiness gate |
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
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (contract_dir / "ASC-0001-closed.md").write_text(
                "---\ncontract_id: ASC-0001\nstatus: closed\n---\n",
                encoding="utf-8",
            )
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")

            data = self.run_policy(root, "--capacity", "4")

            self.assertEqual(data["schema_version"], "aios.loop_policy.v1")
            by_path = {row["sources"][0]["path"]: row for row in data["decisions"]}
            self.assertEqual(by_path["myworld/docs/TODO.md"]["decision"], "accept_now")
            self.assertEqual(
                by_path["myworld/docs/contracts/ASC-0001-closed.md"]["decision"],
                "reject_closed_contract_reference",
            )
            self.assertEqual(by_path["_from_desktop/Uri/docs/TODO.md"]["decision"], "hold_for_operator")
            self.assertEqual(by_path["myworld/hivemind/docs/TODO.md"]["decision"], "hold_for_capability")

    def test_policy_holds_for_capacity(self) -> None:
        # ASC-0117 — the capacity gate counts IN-FLIGHT contracts (those with a
        # dispatch packet in the inbox), so the fixture dispatches 4.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
            inbox = root / ".aios" / "inbox" / "myworld"
            inbox.mkdir(parents=True)
            for idx in range(4):
                (contract_dir / f"ASC-10{idx}.md").write_text(
                    "---\nstatus: accepted\n---\n", encoding="utf-8")
                (inbox / f"asc-10{idx}.myworld.json").write_text(
                    json.dumps({"contract_id": f"ASC-10{idx}"}), encoding="utf-8")

            data = self.run_policy(root, "--capacity", "4")

            by_path = {row["sources"][0]["path"]: row for row in data["decisions"]}
            self.assertEqual(by_path["myworld/docs/TODO.md"]["decision"], "hold_for_capacity")
            self.assertEqual(data["in_flight_count"], 4)

    def test_accepted_waiting_does_not_gridlock(self) -> None:
        # ASC-0117 — many accepted contracts with NO dispatch packet are
        # *waiting*, not in flight; they must not block new acceptance.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
            for idx in range(20):
                (contract_dir / f"ASC-2{idx:03d}.md").write_text(
                    "---\nstatus: accepted\n---\n", encoding="utf-8")

            data = self.run_policy(root, "--capacity", "4")

            by_path = {row["sources"][0]["path"]: row for row in data["decisions"]}
            self.assertEqual(data["open_contract_count"], 20)
            self.assertEqual(data["in_flight_count"], 0)
            self.assertEqual(by_path["myworld/docs/TODO.md"]["decision"], "accept_now")

    def test_verifier_waiting_contract_precedes_codex_auto_when_slot_opens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
            now = int(time.time())
            (contract_dir / "ASC-1001-verifier.md").write_text(
                f"""---
contract_id: ASC-1001
status: accepted
accepted_epoch: {now - 1800}
acceptance_authority: claude@myworld (verifier role)
---
""",
                encoding="utf-8",
            )
            (contract_dir / "ASC-1002-codex.md").write_text(
                f"""---
contract_id: ASC-1002
status: accepted
accepted_epoch: {now - 300}
acceptance_authority: codex@myworld round_controller autodraft
---
""",
                encoding="utf-8",
            )

            data = self.run_policy(root, "--capacity", "4")

            self.assertGreaterEqual(data["verifier_starvation_seconds"], 1800)
            self.assertTrue(data["priority_inversion_detected"])
            order = data["open_contract_order"]
            self.assertEqual(order[0]["contract_id"], "ASC-1001")
            self.assertEqual(order[0]["issuer"], "verifier")
            self.assertEqual(order[0]["priority_reason"], "verifier_wait_threshold_met")
            self.assertEqual(order[1]["issuer"], "codex_auto")
            self.assertTrue(all(row["issuer"] for row in data["decisions"]))

    def test_founder_go_still_preempts_waiting_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (root / "docs" / "AIOS_TASK_RADAR.md").write_text(RADAR, encoding="utf-8")
            now = int(time.time())
            (contract_dir / "ASC-1001-verifier.md").write_text(
                f"""---
contract_id: ASC-1001
status: accepted
accepted_epoch: {now - 7200}
acceptance_authority: claude@myworld (verifier role)
---
""",
                encoding="utf-8",
            )
            (contract_dir / "ASC-1000-founder.md").write_text(
                f"""---
contract_id: ASC-1000
status: accepted
accepted_epoch: {now - 60}
acceptance_authority: founder explicit GO
---
""",
                encoding="utf-8",
            )

            data = self.run_policy(root, "--capacity", "4")

            self.assertEqual(data["open_contract_order"][0]["contract_id"], "ASC-1000")
            self.assertEqual(data["open_contract_order"][0]["issuer"], "founder_go")
            self.assertTrue(data["warnings"])


if __name__ == "__main__":
    unittest.main()
