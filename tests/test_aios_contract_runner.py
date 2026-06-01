"""ContractObject runtime kernel tests."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    # the runner imports aios_contract_object by canonical name; make sure the
    # scripts dir is importable for that side-load
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class ContractRunnerTest(unittest.TestCase):
    def setUp(self):
        self.runner = _load("aios_contract_runner")
        self.co = self.runner.co
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _contract(self, **kw):
        c = self.co.ContractObject(
            contract_id=kw.pop("contract_id", "co-run-test"),
            goal=kw.pop("goal", "test"),
            workspace_root=str(self.root),
        )
        return c

    def test_fs_read_within_scope_succeeds(self):
        target = self.root / "note.txt"
        target.write_text("hello kernel", encoding="utf-8")
        c = self._contract()
        c.filesystem_scope = self.co.FilesystemScope(read_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="s1", description="read", tool="fs.read",
                                    inputs={"path": str(target)}))
        c.evals.append(self.co.Eval(name="all_ok", check="receipts_all_success"))
        summary = self.runner.run_contract(c)
        self.assertEqual(summary["status"], "closed", summary)
        self.assertEqual(len(c.receipts), 1)
        self.assertTrue(c.receipts[0].success)

    def test_fs_read_outside_scope_blocks(self):
        target = self.root / "secret.txt"
        target.write_text("x", encoding="utf-8")
        c = self._contract()
        # scope allows a different dir only
        c.filesystem_scope = self.co.FilesystemScope(read_paths=[str(self.root / "allowed") + "/"])
        c.steps.append(self.co.Step(id="s1", description="read", tool="fs.read",
                                    inputs={"path": str(target)}))
        # validate() itself will flag the unauthorized step
        summary = self.runner.run_contract(c)
        self.assertEqual(summary["status"], "invalid", summary)

    def test_fs_write_is_reversible(self):
        target = self.root / "data.txt"
        target.write_text("original", encoding="utf-8")
        c = self._contract(contract_id="co-write")
        c.filesystem_scope = self.co.FilesystemScope(write_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="w1", description="write", tool="fs.write",
                                    inputs={"path": str(target), "content": "changed"}))
        summary = self.runner.run_contract(c)
        self.assertEqual(summary["status"], "closed", summary)
        self.assertEqual(target.read_text(encoding="utf-8"), "changed")
        rb = self.runner.rollback(c)
        self.assertEqual(rb["status"], "rolled_back")
        self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_fs_write_new_file_rollback_removes_it(self):
        target = self.root / "fresh.txt"
        c = self._contract(contract_id="co-fresh")
        c.filesystem_scope = self.co.FilesystemScope(write_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="w1", description="write", tool="fs.write",
                                    inputs={"path": str(target), "content": "new"}))
        self.runner.run_contract(c)
        self.assertTrue(target.exists())
        self.runner.rollback(c)
        self.assertFalse(target.exists())

    def test_checkpoint_halts_run(self):
        target = self.root / "x.txt"
        c = self._contract(contract_id="co-ckpt")
        c.filesystem_scope = self.co.FilesystemScope(write_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="w1", description="gated write", tool="fs.write",
                                    inputs={"path": str(target), "content": "y"},
                                    requires_checkpoint=True))
        summary = self.runner.run_contract(c)
        self.assertEqual(summary["status"], "waiting_user", summary)
        self.assertFalse(target.exists())  # halted before write
        self.assertIn("w1", c.user_checkpoints)
        # approving proceeds
        summary2 = self.runner.run_contract(c, approve_checkpoints=True)
        # state was waiting_user -> running -> ... handled by run loop
        self.assertTrue(target.exists())

    def test_provider_without_adapter_is_named_exit(self):
        c = self._contract(contract_id="co-prov")
        c.provider_routes.append(self.co.ProviderRoute(provider="claude", auth_mode="session", role="planner"))
        c.steps.append(self.co.Step(id="p1", description="ask", tool="provider.claude",
                                    inputs={"prompt": "hi", "hard": False}))
        summary = self.runner.run_contract(c)
        # offline: provider step fails softly (hard=False) so run still closes
        self.assertEqual(summary["status"], "closed", summary)
        self.assertFalse(c.receipts[0].success)
        self.assertIn("no live adapter", c.receipts[0].error)

    def test_provider_with_adapter_runs(self):
        c = self._contract(contract_id="co-prov2")
        c.provider_routes.append(self.co.ProviderRoute(provider="echo", auth_mode="session", role="planner"))
        c.steps.append(self.co.Step(id="p1", description="ask", tool="provider.echo",
                                    inputs={"prompt": "hello"}))
        summary = self.runner.run_contract(c, adapters={"echo": lambda p: p.upper()})
        self.assertEqual(summary["status"], "closed", summary)
        self.assertTrue(c.receipts[0].success)

    def test_dry_run_executes_nothing(self):
        target = self.root / "dry.txt"
        c = self._contract(contract_id="co-dry")
        c.filesystem_scope = self.co.FilesystemScope(write_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="w1", description="write", tool="fs.write",
                                    inputs={"path": str(target), "content": "z"}))
        summary = self.runner.run_contract(c, dry_run=True)
        self.assertTrue(summary["dry_run"])
        self.assertFalse(target.exists())
        self.assertEqual(len(c.receipts), 0)


if __name__ == "__main__":
    unittest.main()
