"""ContractObject v0 tests."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "aios_contract_object.py"


def _load():
    name = "aios_contract_object_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m  # @dataclass needs the module discoverable via sys.modules
    spec.loader.exec_module(m)
    return m


class ContractObjectTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_new_contract_default_state_is_proposed(self):
        co = self.mod.ContractObject(contract_id="co-test", goal="do a thing")
        self.assertEqual(co.state, "proposed")
        self.assertEqual(co.validate(), [])

    def test_state_machine_legal_transitions(self):
        co = self.mod.ContractObject(contract_id="co-1", goal="x")
        co.transition("accepted")
        self.assertEqual(co.state, "accepted")
        co.transition("running")
        co.transition("waiting_user", reason="checkpoint")
        co.transition("running")
        co.transition("verified")
        co.transition("closed")
        self.assertEqual(co.state, "closed")

    def test_state_machine_illegal_transition_raises(self):
        co = self.mod.ContractObject(contract_id="co-2", goal="x")
        with self.assertRaises(ValueError):
            co.transition("closed")  # cannot skip from proposed to closed
        with self.assertRaises(ValueError):
            co.transition("verified")

    def test_filesystem_scope_deny_overrides_allow(self):
        FS = self.mod.FilesystemScope
        fs = FS(read_paths=["/home/user/"], deny_paths=["/home/user/dain/"])
        self.assertTrue(fs.allows_read("/home/user/Documents/x.md"))
        # Wait — current pattern matching: read_paths must contain "/home/user/" with trailing /,
        # which matches any /home/user/* path. deny matches /home/user/dain/*
        self.assertFalse(fs.allows_read("/home/user/dain/secret.txt"))

    def test_authorize_step_blocks_provider_not_in_routes(self):
        co = self.mod.ContractObject(contract_id="co-3", goal="x")
        co.steps.append(self.mod.Step(id="s1", description="ask claude", tool="provider.claude"))
        errors = co.authorize_step(co.steps[0])
        self.assertTrue(errors)  # no provider routes declared

        co.provider_routes.append(self.mod.ProviderRoute(provider="claude", auth_mode="session", role="planner"))
        errors2 = co.authorize_step(co.steps[0])
        self.assertEqual(errors2, [])

    def test_authorize_step_blocks_fs_write_outside_scope(self):
        co = self.mod.ContractObject(contract_id="co-4", goal="x")
        co.filesystem_scope = self.mod.FilesystemScope(write_paths=["/tmp/aios_test/"])
        s = self.mod.Step(id="s", description="write", tool="fs.write",
                          inputs={"path": "/etc/passwd"})
        co.steps.append(s)
        errors = co.authorize_step(s)
        self.assertTrue(errors)
        self.assertIn("not in scope", errors[0])

    def test_authorize_step_blocks_web_when_network_false(self):
        co = self.mod.ContractObject(contract_id="co-5", goal="x")
        s = self.mod.Step(id="s", description="search", tool="web", inputs={"query": "..."})
        co.steps.append(s)
        errors = co.authorize_step(s)
        self.assertTrue(errors)
        co.authority_scope.network = True
        self.assertEqual(co.authorize_step(s), [])

    def test_receipt_validation(self):
        co = self.mod.ContractObject(contract_id="co-6", goal="x")
        co.steps.append(self.mod.Step(id="step-1", description="...", tool="fs.read"))
        r_ok = self.mod.Receipt(step_id="step-1", timestamp="now", success=True)
        co.record_receipt(r_ok)
        self.assertEqual(len(co.receipts), 1)
        r_bad = self.mod.Receipt(step_id="step-99", timestamp="now", success=True)
        with self.assertRaises(ValueError):
            co.record_receipt(r_bad)

    def test_roundtrip_json(self):
        co = self.mod.ContractObject(
            contract_id="co-7",
            goal="round trip",
            workspace_root="/tmp/x",
        )
        co.filesystem_scope = self.mod.FilesystemScope(
            read_paths=["/tmp/x/"], write_paths=["/tmp/x/out/"],
            deny_paths=["/tmp/x/secrets/"],
        )
        co.provider_routes.append(self.mod.ProviderRoute(
            provider="claude", auth_mode="session", role="planner"))
        co.steps.append(self.mod.Step(id="s1", description="...", tool="fs.read"))
        co.evals.append(self.mod.Eval(name="files_categorized", check="result count > 0"))
        co.memory_effects.append(self.mod.MemoryEffect(
            target="memoryOS.draft", op="draft", content_ref="step:s1"))
        text = co.to_json()
        co2 = self.mod.ContractObject.from_dict(json.loads(text))
        self.assertEqual(co.contract_id, co2.contract_id)
        self.assertEqual(co.goal, co2.goal)
        self.assertEqual(co.filesystem_scope.deny_paths, co2.filesystem_scope.deny_paths)
        self.assertEqual([r.provider for r in co2.provider_routes], ["claude"])
        self.assertEqual(len(co2.steps), 1)
        self.assertEqual(len(co2.evals), 1)
        self.assertEqual(len(co2.memory_effects), 1)

    def test_cli_new_command(self):
        import subprocess
        r = subprocess.run(
            [sys.executable, str(SCRIPT), "new", "--goal", "test goal"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["goal"], "test goal")
        self.assertEqual(data["state"], "proposed")

    def test_cli_validate_and_transition(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, str(SCRIPT), "new", "--goal", "x"],
                capture_output=True, text=True, check=False)
            p = Path(td) / "co.json"
            p.write_text(r.stdout, encoding="utf-8")
            r2 = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", str(p)],
                capture_output=True, text=True, check=False)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("ok", r2.stdout)
            r3 = subprocess.run(
                [sys.executable, str(SCRIPT), "transition", str(p),
                 "--to", "accepted", "--reason", "operator GO", "--write"],
                capture_output=True, text=True, check=False)
            self.assertEqual(r3.returncode, 0, r3.stderr)
            data = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(data["state"], "accepted")


if __name__ == "__main__":
    unittest.main()
