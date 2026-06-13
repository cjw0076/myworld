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
        self.assertEqual(co.schema_version, "aios.contract_object.v0")
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

    def test_validate_rejects_duplicate_step_ids(self):
        co = self.mod.ContractObject(contract_id="co-dup", goal="x")
        co.steps.append(self.mod.Step(id="same", description="one", tool="user.checkpoint"))
        co.steps.append(self.mod.Step(id="same", description="two", tool="user.checkpoint"))
        self.assertTrue(any("duplicate step_id" in e for e in co.validate()))

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

    def test_personal_files_specimen_is_privacy_gated(self):
        co = self.mod.personal_files_specimen(
            goal="organize my desktop files",
            input_root="/home/user/Desktop",
            output_root="/home/user/Organized",
            deny_paths=["/home/user/Desktop/private"],
            provider="codex",
            local_llm="ollama_local",
            workspace_root="/home/user",
        )
        self.assertEqual(co.schema_version, "aios.contract_object.v0")
        self.assertFalse(co.authority_scope.network)
        self.assertEqual(co.authority_scope.device_authority, "delegated")
        self.assertIn("/home/user/Desktop/private/", co.filesystem_scope.deny_paths)
        self.assertIn("fs.delete", co.capability_route["forbidden_tools"])
        self.assertIn("plan_review", [s.id for s in co.steps])
        self.assertIn("memory_writeback_review", [s.id for s in co.steps])
        self.assertEqual(co.validate(), [])

    def test_cli_personal_files_specimen(self):
        import subprocess
        r = subprocess.run(
            [
                sys.executable, str(SCRIPT), "specimen", "personal-files",
                "--input-root", "/tmp/in",
                "--output-root", "/tmp/out",
                "--deny-path", "/tmp/in/private",
            ],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertEqual(data["schema_version"], "aios.contract_object.v0")
        self.assertEqual(data["authority_scope"]["device_authority"], "delegated")
        self.assertFalse(data["authority_scope"]["network"])
        self.assertEqual(data["state"], "proposed")
        self.assertTrue(any(s["id"] == "apply_moves" for s in data["steps"]))

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


    def test_authorize_step_blocks_fs_list_outside_scope(self) -> None:
        """fs.list must check allows_read — not silently bypass authorization."""
        scope = self.mod.FilesystemScope(read_paths=["/allowed/dir/"])
        obj = self._make_contract(filesystem_scope=scope)
        step = self.mod.Step(id="s1", description="list outside", tool="fs.list",
                             inputs={"path": "/forbidden/dir"})
        errors = obj.authorize_step(step)
        self.assertTrue(errors, "fs.list outside read_paths should produce errors")

    def test_authorize_step_allows_fs_list_inside_scope(self) -> None:
        """fs.list inside read_paths must be allowed."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            scope = self.mod.FilesystemScope(read_paths=[tmp + "/"])
            obj = self._make_contract(filesystem_scope=scope)
            step = self.mod.Step(id="s1", description="list inside", tool="fs.list",
                                 inputs={"path": tmp})
            errors = obj.authorize_step(step)
            self.assertEqual(errors, [])

    def test_canonical_path_blocks_traversal(self) -> None:
        """Path traversal via ../ must be caught by canonical resolution."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            allowed = tmp + "/allowed/"
            scope = self.mod.FilesystemScope(read_paths=[allowed])
            obj = self._make_contract(filesystem_scope=scope)
            traversal = allowed + "../outside_file.txt"
            step = self.mod.Step(id="s1", description="traversal attempt", tool="fs.read",
                                 inputs={"path": traversal})
            errors = obj.authorize_step(step)
            self.assertTrue(errors, "path traversal should be blocked")

    def test_canonical_path_blocks_symlink_escape(self) -> None:
        """Symlink pointing outside allowed scope must be caught by canonical resolution."""
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            allowed_dir = Path(tmp) / "allowed"
            allowed_dir.mkdir()
            outside_dir = Path(tmp) / "outside"
            outside_dir.mkdir()
            (outside_dir / "secret.txt").write_text("secret", encoding="utf-8")
            link = allowed_dir / "escape_link"
            link.symlink_to(outside_dir / "secret.txt")
            scope = self.mod.FilesystemScope(read_paths=[str(allowed_dir) + "/"])
            obj = self._make_contract(filesystem_scope=scope)
            step = self.mod.Step(id="s1", description="symlink read", tool="fs.read",
                                 inputs={"path": str(link)})
            errors = obj.authorize_step(step)
            self.assertTrue(errors, "symlink escaping scope should be blocked")

    def _make_contract(self, filesystem_scope=None, **kwargs):
        return self.mod.ContractObject(
            contract_id="TEST-001",
            goal="test",
            workspace_root="/tmp",
            authority_scope=self.mod.AuthorityScope(),
            filesystem_scope=filesystem_scope or self.mod.FilesystemScope(),
            provider_routes=[],
            **kwargs,
        )


if __name__ == "__main__":
    unittest.main()
