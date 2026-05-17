import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_round_controller.py"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def write_contract(path: Path, contract_id: str, *, accepted: str, issuer: str) -> None:
    path.write_text(
        f"""---
contract_id: {contract_id}
status: accepted
goal: Dispatch {contract_id}
accepted: {accepted}
acceptance_authority: {issuer}
---

# {contract_id}

## Scope

repos: `myworld`

allowed_files:
- docs/contracts/{path.name}

forbidden_files:
- .env

## Verification Gate

```bash
python -V
```
""",
        encoding="utf-8",
    )


class AiosLoopPolicyBindingTest(unittest.TestCase):
    def run_controller(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "once", "--root", root.as_posix(), "--json"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_fixture(self, root: Path) -> None:
        scripts = root / "scripts"
        contracts = root / "docs" / "contracts"
        goal = root / "docs" / "goals" / "AIOS-GOAL-0001-make-something-great.md"
        scripts.mkdir(parents=True)
        contracts.mkdir(parents=True)
        goal.parent.mkdir(parents=True)
        goal.write_text("---\ngoal_id: AIOS-GOAL-0001\nstatus: active\n---\n# Goal\n", encoding="utf-8")
        write_executable(
            scripts / "aios_monitor.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({"schema_version":"aios.monitor.assessment.v1","health":"clear","findings":[]}))
""",
        )
        write_executable(
            scripts / "aios_goal_evolution.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({"schema_version":"aios.goal_evolution.v1","recommendation":{},"stop_conditions":[]}))
""",
        )
        coevolution = scripts / "aios_coevolution"
        coevolution.mkdir()
        write_executable(
            coevolution / "persistent.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({"schema_version":"aios.coevolution.persistent.v1","status":"passed","started":0,"failed":0}))
""",
        )
        write_executable(
            scripts / "aios_child_watcher.sh",
            """#!/usr/bin/env bash
set -euo pipefail
echo "hivemind running=false inbox=0 outbox=0 pending=0"
echo "memoryOS running=false inbox=0 outbox=0 pending=0"
echo "CapabilityOS running=false inbox=0 outbox=0 pending=0"
""",
        )
        write_executable(
            scripts / "aios_loop.py",
            """#!/usr/bin/env python3
import json
print(json.dumps({"schema_version":"aios.loop.v1","actions":[],"observations":[]}))
""",
        )
        write_contract(
            contracts / "ASC-2001-verifier.md",
            "ASC-2001",
            accepted="2026-05-13 00:00 KST by claude as verifier",
            issuer="claude as verifier",
        )
        write_contract(
            contracts / "ASC-2002-codex.md",
            "ASC-2002",
            accepted="2026-05-13 00:25 KST by codex_auto",
            issuer="codex_auto",
        )
        write_contract(
            contracts / "ASC-2003-codex.md",
            "ASC-2003",
            accepted="2026-05-13 00:26 KST by codex_auto",
            issuer="codex_auto",
        )
        policy = {
            "schema_version": "aios.loop_policy.v1",
            "open_contract_count": 3,
            "verifier_starvation_seconds": 1800,
            "priority_inversion_detected": True,
            "open_contract_order": [
                {
                    "contract_id": "ASC-2001",
                    "path": "docs/contracts/ASC-2001-verifier.md",
                    "status": "accepted",
                    "issuer": "verifier",
                    "priority_reason": "verifier_wait_threshold_met",
                    "wait_seconds": 1800,
                },
                {
                    "contract_id": "ASC-2002",
                    "path": "docs/contracts/ASC-2002-codex.md",
                    "status": "accepted",
                    "issuer": "codex_auto",
                    "priority_reason": "codex_auto_fifo",
                    "wait_seconds": 300,
                },
                {
                    "contract_id": "ASC-2003",
                    "path": "docs/contracts/ASC-2003-codex.md",
                    "status": "accepted",
                    "issuer": "codex_auto",
                    "priority_reason": "codex_auto_fifo",
                    "wait_seconds": 300,
                },
            ],
            "decisions": [],
        }
        write_executable(
            scripts / "aios_loop_policy.py",
            "#!/usr/bin/env python3\nprint(" + repr(json.dumps(policy)) + ")\n",
        )

    def test_round_controller_dispatches_policy_verifier_before_codex_auto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_controller(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            actions = payload["steps"]["dispatch_loop"]["parsed"]["actions"]
            self.assertEqual("ASC-2001", actions[0]["contract_id"])
            self.assertTrue((root / ".aios" / "inbox" / "myworld" / "asc-2001.myworld.json").exists())
            self.assertFalse((root / ".aios" / "inbox" / "myworld" / "asc-2002.myworld.json").exists())
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            decisions = [event for event in events if event.get("event") == "policy_dispatch_decision"]
            self.assertTrue(decisions)
            self.assertTrue(decisions[-1]["policy_recommendation_followed"])


if __name__ == "__main__":
    unittest.main()
