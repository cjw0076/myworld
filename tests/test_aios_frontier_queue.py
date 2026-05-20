"""ASC-0211 L4 — frontier_queue snapshot block + frontier_show CLI tests."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_SCRIPT = REPO_ROOT / "scripts" / "aios_control_snapshot.py"
SHOW_SCRIPT = REPO_ROOT / "scripts" / "aios_frontier_show.py"


def _load_snapshot_module():
    spec = importlib.util.spec_from_file_location("aios_control_snapshot_under_test", SNAPSHOT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FrontierQueueTest(unittest.TestCase):
    def _seed_drafts(self, inbox: Path) -> None:
        inbox.mkdir(parents=True, exist_ok=True)
        # discomfort
        (inbox / "a.json").write_text(json.dumps({
            "request_id": "discomfort-a",
            "draft": {
                "origin": "aios_discomfort_inject",
                "content": "discomfort signal one",
                "provenance": {"audit_verdict": "mixed", "footprint_score": 3},
            },
        }), encoding="utf-8")
        # frontier
        (inbox / "b.json").write_text(json.dumps({
            "request_id": "frontier-b",
            "draft": {
                "origin": "aios_frontier_question",
                "content": "frontier question one",
                "provenance": {"kind": "uncited_reference", "memo": "ref_x.md"},
            },
        }), encoding="utf-8")
        # boundary probe
        (inbox / "c.json").write_text(json.dumps({
            "request_id": "probe-c",
            "draft": {
                "origin": "aios_boundary_probe",
                "content": "probe ecology one",
                "provenance": {"kind": "cross_domain_probe", "domain": "ecology",
                               "target_id": "ASC-XYZ"},
            },
        }), encoding="utf-8")
        # noise — different origin must be ignored
        (inbox / "d.json").write_text(json.dumps({
            "draft": {"origin": "aios_chat_genesis", "content": "ignore me"},
        }), encoding="utf-8")

    def test_build_frontier_queue_filters_to_transcendence_origins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_drafts(root / ".aios" / "inbox" / "memoryOS")
            snap = _load_snapshot_module()
            fq = snap.build_frontier_queue(root)
        self.assertEqual(fq["schema_version"], "aios.frontier_queue.v1")
        self.assertEqual(fq["queued"], 3)
        self.assertEqual(set(fq["by_origin"].keys()),
                         {"aios_discomfort_inject", "aios_frontier_question",
                          "aios_boundary_probe"})
        contents = [d["content"] for d in fq["drafts"]]
        self.assertNotIn("ignore me", contents)

    def test_show_cli_respects_origin_filter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_drafts(root / ".aios" / "inbox" / "memoryOS")
            snap = _load_snapshot_module()
            fq = snap.build_frontier_queue(root)
            snapshot_path = root / "aios-control-snapshot.json"
            snapshot_path.write_text(json.dumps({"frontier_queue": fq}), encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SHOW_SCRIPT),
                 "--snapshot", str(snapshot_path),
                 "--origin", "aios_boundary_probe",
                 "--json"],
                capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["queued"], 3)  # by_origin counts pre-filter
            self.assertEqual(len(out["drafts"]), 1)
            self.assertEqual(out["drafts"][0]["origin"], "aios_boundary_probe")


if __name__ == "__main__":
    unittest.main()
