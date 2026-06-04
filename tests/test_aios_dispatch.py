import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_dispatch.py"


CONTRACT = """---
contract_id: ASC-0999
status: proposed
goal: Test dispatch flow.
accepted:
closed:
---

# ASC-0999 Test

repos:

- `hivemind`
- `memoryOS`

allowed_files:

- `hivemind/hivemind/memory_bridge.py`
- `memoryOS/memoryos/cli.py`

allowed_existing_dirty:

- `memoryOS/.tmp_uri_cleanroom_seed.md`

forbidden_files:

- `CapabilityOS/docs`
- `.env`
"""


ACCEPTED_MYWORLD_CONTRACT = """---
contract_id: ASC-0998
status: accepted
goal: Test watcher flow.
accepted: now
closed:
---

# ASC-0998 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

## Verification Gate

Commands:

```bash
cd {root}
python -c "print('watch-ok')"
```
"""


ENRICHED_CONTRACT = """---
contract_id: ASC-0997
status: accepted
goal: Test enriched packet.
accepted: now
closed:
---

# ASC-0997 Test

repos:

- `memoryOS`

allowed_files:

- `memoryOS/memoryos/cli.py`

forbidden_files:

- `.env`

## Responsibilities

### MemoryOS

must_produce:

- `context_pack.md` output
- RetrievalTrace with provenance

## Verification Gate

```bash
cd {root}/memoryOS
python -m pytest tests/test_import_run.py -v
```
"""


CHECKPOINT_CONTRACT = """---
contract_id: ASC-0996
status: accepted
goal: Test checkpoint packet.
accepted: now
closed:
---

# ASC-0996 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

## Trigger

This asks for a public statement on behalf of the system.
"""


DELIBERATION_ONLY_EXTERNAL_TOPIC_CONTRACT = """---
contract_id: ASC-0992
status: accepted
goal: Debate whether AIOS should deploy a hosted endpoint.
accepted: now
human_approved: true
closed:
---

# ASC-0992 Test

repos:

- `hivemind`

allowed_files:

- `hivemind/.runs/hosting_debate/**`

forbidden_files:

- any deployment manifest, hosting config, or cloud-provider code
- `.env`

## Scope

This contract deliberates; it does not deploy. It produces only deliberation
artifacts and bans implementation creep.
"""


PATH_TERM_CONTRACT = """---
contract_id: ASC-0995
status: accepted
goal: Test path term packet.
accepted: now
closed:
---

# ASC-0995 Test

repos:

- `myworld`

allowed_files:

- `tests/test_aios_dispatch.py`

forbidden_files:

- `.env`

## Verification Gate

```bash
cd {root}
python -m unittest tests/test_aios_web_research_receipt.py
```
"""


BASH_GATE_CONTRACT = """---
contract_id: ASC-0993
status: accepted
goal: Test bash verification packet.
accepted: now
closed:
---

# ASC-0993 Test

repos:

- `myworld`

allowed_files:

- `scripts/check.sh`

forbidden_files:

- `.env`

## Verification Gate

```bash
cd {root}
bash scripts/check.sh
```
"""


GIT_DIFF_CHECK_CONTRACT = """---
contract_id: ASC-0991
status: accepted
goal: Test safe git diff check verification.
accepted: now
closed:
---

# ASC-0991 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

## Verification Gate

```bash
cd {root}
git diff --check -- scripts/aios_dispatch.py tests/test_aios_dispatch.py
```
"""


LOCAL_EVIDENCE_CONTRACT = """---
contract_id: ASC-0994
status: accepted
goal: Turn validated web evidence into local review candidates.
accepted: now
closed:
---

# ASC-0994 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_web_evidence_memory_review.py`

forbidden_files:

- `.env`
- raw private exports

## Scope

This reads an existing public source receipt from disk and writes local draft
review candidates. It uses the local filesystem only and performs no outbound
publication.
"""


GENESIS_CONTRACT = """---
contract_id: ASC-0989
status: accepted
goal: Test GenesisOS dispatch target.
accepted: now
closed:
---

# ASC-0989 Test

repos:

- `GenesisOS`

allowed_files:

- `GenesisOS/genesisos/critic.py`

forbidden_files:

- `.env`

## Responsibilities

### GenesisOS

must_produce:

- prompt-prison critic advisory output
"""


PRAXIS_REQUIRED_CONTRACT = """---
contract_id: ASC-0992
status: accepted
goal: Bind production praxis to dispatch.
accepted: now
closed:
praxis_required: true
---

# ASC-0992 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`
- `scripts/aios_work_praxis.py`
- `tests/test_aios_dispatch.py`

forbidden_files:

- `.env`

## Verification Gate

```bash
cd {root}
python -m unittest tests/test_aios_dispatch.py
```
"""


UNMET_CLOSED_CONTRACT = """---
contract_id: ASC-0990
status: closed
goal: Test strict close.
accepted: now
closed: now
---

# ASC-0990 Test

repos:

- `myworld`

allowed_files:

- `scripts/aios_dispatch.py`

forbidden_files:

- `.env`

Pass criteria:

- file_exists:missing.txt
"""


VALID_PRAXIS = {
    "schema_version": "aios.production_praxis.v1",
    "task": "Bind production praxis to dispatch.",
    "memory_context": {"status": "used", "evidence_refs": ["aios://memory/mem_test"]},
    "capability_routes": {"status": "used", "routes": ["aios://capability/cap_test"]},
    "external_resource_check": {"status": "optional_with_reason", "reason": "local deterministic dispatch binding"},
    "genesis_reframe": {
        "status": "used",
        "frictions": ["Agents skip OS roles when dispatch does not require them."],
        "alternative_frames": ["praxis gate", "production preflight"],
    },
    "hive_execution_plan": {"status": "planned", "verification_gate": "python -m unittest tests/test_aios_dispatch.py"},
    "specialist_assignment": [
        {"agent": "codex", "strength": "code/test", "job": "implement dispatch binding"},
        {"agent": "claude", "strength": "architecture review", "job": "review integration risk"},
    ],
    "stop_conditions": [],
}


class AiosDispatchTest(unittest.TestCase):
    def run_cli(self, root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, SCRIPT.as_posix(), *args],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def test_create_records_dispatch_without_inbox_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")

            result = self.run_cli(root, "create", contract.as_posix())
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["dispatch_id"], "asc-0999")
            state = root / ".aios" / "state" / "dispatches.jsonl"
            self.assertTrue(state.exists())
            self.assertFalse(list((root / ".aios" / "inbox" / "hivemind").glob("*.json")))

    def test_send_requires_accepted_contract_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "hivemind", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("operator acceptance required", result.stderr)

    def test_send_writes_scoped_packet_when_allowed_for_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "memoryOS", "--agent", "codex", "--allow-proposed")

            packet_path = root / ".aios" / "inbox" / "memoryOS" / "asc-0999.memoryOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["target_repo"], "memoryOS")
            self.assertEqual(packet["contract_status"], "proposed")
            self.assertIn("memoryOS/memoryos/cli.py", packet["scope"]["allowed_files"])
            self.assertEqual(packet["scope"]["allowed_existing_dirty"], ["memoryOS/.tmp_uri_cleanroom_seed.md"])
            self.assertEqual(packet["control_plane"]["root"], "myworld")
            self.assertIn("docs/AIOS_BUILD_METHOD.md", packet["required_reading"])
            self.assertEqual(packet["result_schema_version"], "aios.dispatch.result.v1")
            self.assertIn("must_produce", packet)
            self.assertIn("verification_commands", packet)
            self.assertEqual(packet["action_policy"]["decision"], "allow")
            self.assertIn("allow_proposed_test_bypass", packet["action_policy"]["reason_codes"])

    def test_send_captures_allowed_existing_dirty_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memoryos = root / "memoryOS"
            memoryos.mkdir()
            subprocess.run(["git", "init"], cwd=memoryos, text=True, capture_output=True, check=True)
            seed = memoryos / ".tmp_uri_cleanroom_seed.md"
            seed.write_text("cleanup input\n", encoding="utf-8")
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "memoryOS", "--agent", "codex", "--allow-proposed")

            packet_path = root / ".aios" / "inbox" / "memoryOS" / "asc-0999.memoryOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            baseline = packet["scope"]["allowed_existing_dirty_baseline"]
            self.assertEqual(
                baseline,
                [
                    {
                        "path": "memoryOS/.tmp_uri_cleanroom_seed.md",
                        "repo_path": ".tmp_uri_cleanroom_seed.md",
                        "status_code": "??",
                        "sha256": hashlib.sha256(b"cleanup input\n").hexdigest(),
                    }
                ],
            )

    def test_send_enriches_packet_with_repo_slice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0997-test.md"
            contract.write_text(ENRICHED_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "memoryOS", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "memoryOS" / "asc-0997.memoryOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["schema_version"], "aios.dispatch.v1")
            self.assertEqual(packet["result_schema_version"], "aios.dispatch.result.v1")
            self.assertIn("context_pack.md", " ".join(packet["must_produce"]))
            self.assertEqual(packet["verification_commands"][0]["command"], "python -m pytest tests/test_import_run.py -v")
            self.assertTrue(packet["verification_commands"][0]["cwd"].endswith("/memoryOS"))
            self.assertEqual(packet["result_contract"]["schema_version"], "aios.dispatch.result.v1")
            self.assertEqual(packet["action_policy"]["decision"], "allow")
            self.assertTrue(packet["action_policy"]["allowed_to_execute"])

    def test_send_blocks_checkpoint_required_packet_before_inbox_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0996-test.md"
            contract.write_text(CHECKPOINT_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", check=False)

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["status"], "escalated")
            self.assertEqual(payload["policy"]["decision"], "escalate")
            self.assertFalse((root / ".aios" / "inbox" / "myworld" / "asc-0996.myworld.json").exists())
            status = json.loads(self.run_cli(root, "status", "--json").stdout)
            self.assertEqual(status["dispatches"][0]["status"], "escalated")
            self.assertEqual(status["dispatches"][0]["reason"], "action_policy_escalate")

    def test_policy_allows_human_approved_deliberation_about_external_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0992-test.md"
            contract.write_text(DELIBERATION_ONLY_EXTERNAL_TOPIC_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "hivemind", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "hivemind" / "asc-0992.hivemind.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            policy = packet["action_policy"]
            self.assertEqual(policy["decision"], "allow")
            self.assertTrue(policy["allowed_to_execute"])
            self.assertTrue(policy["action"]["external_topic"])
            self.assertTrue(policy["action"]["deliberation_only_external_topic"])
            self.assertFalse(policy["action"]["external_effect"])
            self.assertEqual(policy["action"]["privacy"], "local")

    def test_policy_gate_does_not_escalate_path_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0995-test.md"
            contract.write_text(PATH_TERM_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0995.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["action_policy"]["decision"], "allow")
            self.assertEqual(packet["verification_commands"][0]["command"], "python -m unittest tests/test_aios_web_research_receipt.py")

    def test_send_allows_repo_local_bash_verification_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0993-test.md"
            contract.write_text(BASH_GATE_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0993.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["verification_commands"][0]["command"], "bash scripts/check.sh")
            self.assertTrue(packet["verification_commands"][0]["cwd"].endswith(root.name))

    def test_send_allows_git_diff_check_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0991-test.md"
            contract.write_text(GIT_DIFF_CHECK_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0991.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["verification_commands"][0]["command"], "git diff --check -- scripts/aios_dispatch.py tests/test_aios_dispatch.py")
            self.assertTrue(packet["verification_commands"][0]["cwd"].endswith(root.name))

    def test_policy_gate_allows_local_web_evidence_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0994-test.md"
            contract.write_text(LOCAL_EVIDENCE_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0994.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["action_policy"]["decision"], "allow")
            self.assertTrue(packet["action_policy"]["allowed_to_execute"])

    def test_genesisos_is_supported_dispatch_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0989-test.md"
            contract.write_text(GENESIS_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "GenesisOS", "--agent", "codex")

            packet_path = root / ".aios" / "inbox" / "GenesisOS" / "asc-0989.GenesisOS.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["target_repo"], "GenesisOS")
            self.assertIn("prompt-prison critic", " ".join(packet["must_produce"]))
            status = json.loads(self.run_cli(root, "status", "--json").stdout)
            self.assertIn("GenesisOS", status["inbox"])
            self.assertEqual(status["inbox"]["GenesisOS"], 1)

    def test_praxis_required_contract_blocks_send_without_praxis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0992-test.md"
            contract.write_text(PRAXIS_REQUIRED_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", check=False)

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "held")
            self.assertEqual(payload["reason"], "praxis_required_missing")
            self.assertFalse((root / ".aios" / "inbox" / "myworld" / "asc-0992.myworld.json").exists())

    def test_praxis_required_contract_attaches_valid_praxis_to_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0992-test.md"
            contract.write_text(PRAXIS_REQUIRED_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            praxis = root / "praxis.json"
            praxis.write_text(json.dumps(VALID_PRAXIS), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", "--praxis", praxis.as_posix())

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0992.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["production_praxis"]["schema_version"], "aios.production_praxis.v1")
            self.assertEqual(packet["production_praxis"]["ref"], praxis.as_posix())
            self.assertIn("memory_context_missing", packet["stop_conditions"])

    def test_send_attaches_session_envelope_and_watch_echoes_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0998-test.md"
            contract.write_text(ACCEPTED_MYWORLD_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            envelope_path = root / ".aios" / "invocations" / "test-envelope" / "session_envelope.json"
            envelope_path.parent.mkdir(parents=True)
            envelope_path.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "envelope_id": "se-test",
                        "invocation_id": "test-envelope",
                        "goal_hash": "abc123",
                        "required_before_execution": True,
                        "role_statuses": {"genesis": "passed", "memory": "passed", "capability": "passed", "hive": "passed"},
                        "role_artifacts": {"hive_execution_plan": ".aios/invocations/test-envelope/hive/execution_plan.json"},
                        "executor_assignment": {"default_executor": "codex", "requires_dispatch_packet": True},
                        "degraded_roles": [],
                        "failed_roles": [],
                        "degraded_receipt": {"status": "not_needed", "stop_conditions_triggered": []},
                    }
                ),
                encoding="utf-8",
            )
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--session-envelope", envelope_path.as_posix())

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0998.myworld.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["session_envelope"]["schema_version"], "aios.session_envelope.v1")
            self.assertEqual(packet["session_envelope"]["ref"], ".aios/invocations/test-envelope/session_envelope.json")
            self.assertEqual(packet["session_envelope"]["executor_assignment"]["default_executor"], "codex")
            self.assertIn("session_envelope_missing", packet["stop_conditions"])

            result = self.run_cli(root, "watch", "--repo", "myworld", "--dispatch-id", "asc-0998", "--once")
            result_payload = json.loads(result.stdout)
            data = json.loads((root / result_payload["result"]).read_text(encoding="utf-8"))
            self.assertEqual(data["session_envelope"]["ref"], ".aios/invocations/test-envelope/session_envelope.json")

    def test_session_envelope_required_contract_blocks_missing_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0998-test.md"
            contract.write_text(
                ACCEPTED_MYWORLD_CONTRACT.replace("closed:\n", "closed:\nsession_envelope_required: true\n").format(root=root.as_posix()),
                encoding="utf-8",
            )
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", check=False)

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "held")
            self.assertEqual(payload["reason"], "session_envelope_required_missing")
            self.assertFalse((root / ".aios" / "inbox" / "myworld" / "asc-0998.myworld.json").exists())

    def test_memory_retrieval_required_envelope_attaches_trace_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0998-test.md"
            contract.write_text(
                ACCEPTED_MYWORLD_CONTRACT.replace(
                    "closed:\n",
                    "closed:\nsession_envelope_required: true\nmemory_retrieval_required: true\n",
                ).format(root=root.as_posix()),
                encoding="utf-8",
            )
            invocation = root / ".aios" / "invocations" / "trace-envelope"
            context = invocation / "memory" / "context_pack.md"
            context.parent.mkdir(parents=True)
            context.write_text(
                "\n".join(
                    [
                        "# Context pack",
                        "- selected_memory_ids: [\"mem_a\"]",
                        "- trace_id: rtrace_required123",
                        "- signal_coverage: 1.0",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            envelope_path = invocation / "session_envelope.json"
            envelope_path.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_envelope.v1",
                        "envelope_id": "se-trace",
                        "invocation_id": "trace-envelope",
                        "goal_hash": "tracehash",
                        "required_before_execution": True,
                        "role_statuses": {"genesis": "passed", "memory": "passed", "capability": "passed", "hive": "passed"},
                        "role_artifacts": {"memory_context_pack": ".aios/invocations/trace-envelope/memory/context_pack.md"},
                        "executor_assignment": {"default_executor": "codex", "requires_dispatch_packet": True},
                        "degraded_roles": [],
                        "failed_roles": [],
                        "degraded_receipt": {"status": "not_needed", "stop_conditions_triggered": []},
                    }
                ),
                encoding="utf-8",
            )
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", "--session-envelope", envelope_path.as_posix())

            packet = json.loads((root / ".aios" / "inbox" / "myworld" / "asc-0998.myworld.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["session_envelope"]["memory_context"]["retrieval_trace"], "rtrace_required123")
            self.assertEqual(packet["session_envelope"]["memory_context"]["signal_coverage"], "1.0")

    def test_invalid_praxis_blocks_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0992-test.md"
            contract.write_text(PRAXIS_REQUIRED_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            praxis = root / "praxis.json"
            invalid = dict(VALID_PRAXIS)
            invalid["specialist_assignment"] = [{"agent": "codex", "strength": "general", "job": "do everything"}]
            praxis.write_text(json.dumps(invalid), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", "--praxis", praxis.as_posix(), check=False)

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["reason"], "praxis_invalid")
            self.assertIn("specialist_assignment_too_flat", payload["praxis_errors"])

    def test_release_transition_is_first_class_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            self.run_cli(root, "release", "--dispatch-id", "asc-0999", "--reason", "verified")

            status = self.run_cli(root, "status", "--json")
            data = json.loads(status.stdout)
            self.assertEqual(data["dispatches"][0]["status"], "released")
            self.assertEqual(data["dispatches"][0]["reason"], "verified")

    def test_release_blocks_authority_hard_denial(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(
                root,
                "release",
                "--dispatch-id",
                "asc-0999",
                "--reason",
                "verified",
                "--agent",
                "outsider_peer",
                check=False,
            )
            payload = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["status"], "authority_denied")
            self.assertFalse(payload["authority"]["allowed"])
            self.assertIsNone(payload["memory_writeback"])
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "authority_check" for event in events))
            self.assertFalse(any(event.get("event") == "released" and event.get("status") == "released" for event in events))
            self.assertTrue((root / ".aios" / "state" / "authority.jsonl").exists())

    def test_release_authority_override_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0999-test.md"
            contract.write_text(CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())

            result = self.run_cli(
                root,
                "release",
                "--dispatch-id",
                "asc-0999",
                "--reason",
                "operator override for test",
                "--agent",
                "outsider_peer",
                "--override-authority",
            )
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["status"], "released")
            self.assertFalse(payload["authority"]["allowed"])
            self.assertTrue(payload["authority"]["override"])
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event.get("event") == "released" and event.get("status") == "released" for event in events))

    def test_release_after_escalation_recovers_inbox_packet_with_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0996-test.md"
            contract.write_text(CHECKPOINT_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())
            self.run_cli(root, "send", "--repo", "myworld", "--agent", "codex", check=False)

            result = self.run_cli(root, "release", "--dispatch-id", "asc-0996", "--reason", "operator_approved")
            payload = json.loads(result.stdout)

            packet_path = root / ".aios" / "inbox" / "myworld" / "asc-0996.myworld.json"
            self.assertTrue(packet_path.exists())
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertTrue(packet["operator_override"])
            self.assertEqual(packet["override_reason"], "operator_approved")
            self.assertEqual(packet["action_policy"]["decision"], "allow")
            self.assertTrue(packet["action_policy"]["operator_override"])
            self.assertEqual(payload["recovery"]["packet"], ".aios/inbox/myworld/asc-0996.myworld.json")

            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "dispatch.recovery" for event in events))
            status = json.loads(self.run_cli(root, "status", "--json").stdout)
            self.assertEqual(status["dispatches"][0]["status"], "released")
            self.assertEqual(status["dispatches"][0]["sent"], ["myworld"])

    def test_release_blocks_closed_contract_with_unmet_criteria_without_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0990-test.md"
            contract.write_text(UNMET_CLOSED_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix(), "--dispatch-id", "asc-0990")

            result = self.run_cli(root, "release", "--dispatch-id", "asc-0990", "--reason", "verified", check=False)

            self.assertNotEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "held")
            self.assertEqual(payload["strict_close"]["reason"], "strict_close_unclassified")
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "strict_close_blocked" for event in events))

    def test_release_allows_partial_close_with_followup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0990-test.md"
            contract.write_text(UNMET_CLOSED_CONTRACT, encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix(), "--dispatch-id", "asc-0990")

            result = self.run_cli(
                root,
                "release",
                "--dispatch-id",
                "asc-0990",
                "--reason",
                "partial_with_followup",
                "--close-type",
                "closed_partial_with_followup",
                "--followup-asc",
                "ASC-0991",
            )
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            events = [
                json.loads(line)
                for line in (root / ".aios" / "state" / "dispatches.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(any(event["event"] == "strict_close_classified" for event in events))

    def test_watch_once_runs_verification_and_writes_result_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "ASC-0998-test.md"
            contract.write_text(ACCEPTED_MYWORLD_CONTRACT.format(root=root.as_posix()), encoding="utf-8")
            self.run_cli(root, "create", contract.as_posix())
            self.run_cli(root, "send", "--repo", "myworld")

            result = self.run_cli(root, "watch", "--repo", "myworld", "--dispatch-id", "asc-0998", "--once")
            payload = json.loads(result.stdout)

            self.assertTrue(payload["ok"])
            result_path = root / payload["result"]
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "aios.dispatch.result.v1")
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["target_repo"], "myworld")
            self.assertFalse(data["stop_conditions_triggered"])
            self.assertTrue((root / ".aios" / "logs" / "asc-0998.myworld.log").exists())

    def test_collect_skips_already_collected_result_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "myworld"
            result_dir.mkdir(parents=True)
            (result_dir / "asc-0998.myworld.result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "myworld",
                        "dispatch_id": "asc-0998",
                        "contract_id": "ASC-0998",
                        "status": "passed",
                        "evidence": [],
                        "stop_conditions_triggered": [],
                    }
                ),
                encoding="utf-8",
            )

            first = self.run_cli(root, "collect", "--repo", "myworld")
            second = self.run_cli(root, "collect", "--repo", "myworld")

            self.assertEqual(len(json.loads(first.stdout)["collected"]), 1)
            self.assertEqual(json.loads(second.stdout)["collected"], [])

    def test_collect_rejects_malformed_v1_result_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "myworld"
            result_dir.mkdir(parents=True)
            (result_dir / "bad.myworld.result.json").write_text(
                json.dumps({"schema_version": "aios.dispatch.result.v1", "dispatch_id": "bad"}),
                encoding="utf-8",
            )

            result = self.run_cli(root, "collect", "--repo", "myworld", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("malformed result packet", result.stderr)

    def test_collect_rejects_result_packet_with_wrong_dispatch_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result_dir = root / ".aios" / "outbox" / "CapabilityOS"
            result_dir.mkdir(parents=True)
            (result_dir / "asc-0012.CapabilityOS.result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.dispatch.result.v1",
                        "target_repo": "CapabilityOS",
                        "dispatch_id": "asc-0012.CapabilityOS",
                        "contract_id": "ASC-0012",
                        "status": "passed",
                        "evidence": [],
                        "stop_conditions_triggered": [],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(root, "collect", "--repo", "CapabilityOS", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("dispatch_id asc-0012.CapabilityOS != asc-0012", result.stderr)


if __name__ == "__main__":
    unittest.main()
