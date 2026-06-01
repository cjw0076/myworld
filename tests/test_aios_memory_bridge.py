"""Cognition-loop bridge tests — no live memoryOS required (DI runner)."""
from __future__ import annotations

import importlib.util
import json
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
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class MemoryBridgeTest(unittest.TestCase):
    def setUp(self):
        self.bridge = _load("aios_memory_bridge")
        self.co = _load("aios_contract_object")
        self.runner = _load("aios_contract_runner")
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _closed_contract(self, cid, goal):
        c = self.co.ContractObject(contract_id=cid, goal=goal, workspace_root=str(self.root))
        c.steps.append(self.co.Step(id="s1", description="x", tool="fs.read"))
        c.transition("accepted"); c.transition("running")
        c.record_receipt(self.co.Receipt(step_id="s1", timestamp="now", success=True,
                                         summary="did the thing", artifacts=["/tmp/a"]))
        c.transition("verified"); c.transition("closed")
        return c

    def test_review_packet_is_draft_first_shape(self):
        c = self._closed_contract("co-a", "tidy the inbox")
        packet, src = self.bridge.build_review_packet(c, self.root)
        self.assertEqual(packet["schema_version"], "aios.memory_draft_review_request.v1")
        self.assertTrue(packet["draft_id"])
        self.assertIn("tidy the inbox", packet["draft"]["content"])
        self.assertTrue(Path(packet["source_artifact"]).exists())
        # draft-first: nothing about it says "accepted"
        self.assertEqual(packet["draft"]["type"], "decision")

    def test_writeback_queues_when_memoryos_absent(self):
        # temp root has no memoryOS/ -> named exit to local queue, not a crash
        c = self._closed_contract("co-b", "find duplicate files")
        res = self.bridge.writeback(c, self.root, runner=lambda *a: (0, "", ""))
        self.assertEqual(res["status"], "queued", res)
        self.assertTrue(Path(res["where"]).exists())

    def test_writeback_drafts_when_memoryos_present(self):
        # simulate a memoryOS/ presence + a successful ingest
        (self.root / "memoryOS" / "memoryos").mkdir(parents=True)
        (self.root / "memoryOS" / "memoryos" / "cli.py").write_text("# stub")
        c = self._closed_contract("co-c", "summarize the repo")
        calls = []
        def fake_runner(argv, cwd, timeout):
            calls.append((argv, cwd))
            return 0, json.dumps({"status": "needs_more_evidence"}), ""
        res = self.bridge.writeback(c, self.root, runner=fake_runner)
        self.assertEqual(res["status"], "drafted", res)
        self.assertIn("import-review-request", calls[0][0])

    def test_writeback_queues_on_ingest_failure(self):
        (self.root / "memoryOS" / "memoryos").mkdir(parents=True)
        (self.root / "memoryOS" / "memoryos" / "cli.py").write_text("# stub")
        c = self._closed_contract("co-d", "x")
        res = self.bridge.writeback(c, self.root, runner=lambda *a: (1, "", "boom"))
        self.assertEqual(res["status"], "queued")  # never loses the trace
        self.assertIn("boom", res["detail"])

    def test_retrieve_falls_back_to_local_queue(self):
        # write two runs to the queue, then retrieve by overlapping goal
        c1 = self._closed_contract("co-e", "organize photos from the festival")
        self.bridge.writeback(c1, self.root, runner=lambda *a: (0, "", ""))
        c2 = self._closed_contract("co-f", "compute taxes")
        self.bridge.writeback(c2, self.root, runner=lambda *a: (0, "", ""))
        # no memoryOS -> queue fallback; goal overlaps c1
        hits = self.bridge.retrieve("organize festival photos", self.root,
                                    runner=lambda *a: (1, "", ""))
        self.assertTrue(any("festival" in h for h in hits), hits)
        self.assertFalse(any("taxes" in h for h in hits))

    def test_full_loop_writeback_then_retrieve(self):
        # the compounding property: run -> remember -> recall changes next context
        c = self._closed_contract("co-loop", "deduplicate downloads folder")
        sink = lambda cc: self.bridge.writeback(cc, self.root, runner=lambda *a: (0, "", ""))
        # re-run through the runner's sink path on an already-closed contract is
        # not the point; just exercise writeback as the sink would
        sink(c)
        recalled = self.bridge.retrieve("dedupe the downloads", self.root,
                                        runner=lambda *a: (1, "", ""))
        self.assertTrue(any("deduplicate" in r for r in recalled), recalled)


class RunnerMemorySinkTest(unittest.TestCase):
    def setUp(self):
        self.co = _load("aios_contract_object")
        self.runner = _load("aios_contract_runner")
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def test_runner_calls_memory_sink_at_closeout(self):
        target = self.root / "f.txt"
        c = self.co.ContractObject(contract_id="co-sink", goal="write", workspace_root=str(self.root))
        c.filesystem_scope = self.co.FilesystemScope(write_paths=[str(self.root) + "/"])
        c.steps.append(self.co.Step(id="w1", description="w", tool="fs.write",
                                    inputs={"path": str(target), "content": "hi"}))
        seen = {}
        def sink(contract):
            seen["called"] = contract.contract_id
            return {"status": "drafted"}
        summary = self.runner.run_contract(c, memory_sink=sink)
        self.assertEqual(summary["status"], "closed")
        self.assertEqual(seen.get("called"), "co-sink")
        self.assertEqual(summary["memory"]["status"], "drafted")

    def test_sink_error_does_not_fail_closed_run(self):
        c = self.co.ContractObject(contract_id="co-sink2", goal="x", workspace_root=str(self.root))
        c.filesystem_scope = self.co.FilesystemScope(read_paths=[str(self.root) + "/"])
        (self.root / "a").write_text("x")
        c.steps.append(self.co.Step(id="r", description="r", tool="fs.read",
                                    inputs={"path": str(self.root / "a")}))
        def boom(contract):
            raise RuntimeError("memory down")
        summary = self.runner.run_contract(c, memory_sink=boom)
        self.assertEqual(summary["status"], "closed")  # run still closes
        self.assertEqual(summary["memory"]["status"], "error")


if __name__ == "__main__":
    unittest.main()
