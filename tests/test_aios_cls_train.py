from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def _load():
    spec = importlib.util.spec_from_file_location("aios_cls_train_uut", SCRIPTS / "aios_cls_train.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["aios_cls_train_uut"] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


def _run(ref, cat, lt, freq, weight=1.0):
    return {"ref": ref, "category": cat, "loop_type": lt, "tool_freq": freq, "weight": weight}


class TrainScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.m = _load()

    def test_pseudo_tokens_dropped(self):
        tools = self.m._real_tools({"Bash": 5, "last-prompt": 99, "queue-operation": 50, "Edit": 3})
        names = [t for t, _ in tools]
        self.assertEqual(names, ["Bash", "Edit"])           # pseudo dropped, freq-sorted

    def test_example_is_chat_format_names_only(self):
        ex = self.m.to_example(_run("r1", "code", "react_code", {"Edit": 6, "Bash": 4, "last-prompt": 9}))
        self.assertEqual([msg["role"] for msg in ex["messages"]], ["system", "user", "assistant"])
        self.assertIn("Edit", ex["messages"][-1]["content"])
        self.assertNotIn("last-prompt", ex["messages"][-1]["content"])   # privacy/noise filtered

    def test_example_none_when_no_real_tools(self):
        self.assertIsNone(self.m.to_example(_run("r", "code", "quick", {"last-prompt": 5})))

    def test_dataset_expands_by_replay_count(self):
        corpus = [_run("a", "code", "react_code", {"Edit": 6}),
                  _run("b", "docs", "exploration", {"Read": 6})]
        schedule = [{"ref": "a", "replay_count": 3}, {"ref": "b", "replay_count": 1}]
        ds = self.m.build_dataset(corpus, schedule)
        self.assertEqual(len(ds), 4)                        # 3 + 1

    def test_validate_ready_blocks_small_or_unlabeled(self):
        small = self.m.validate_ready({"training_ready": True, "provenance": "x"}, [{}], min_examples=50)
        self.assertFalse(small["ready"])
        self.assertTrue(any("too few" in b for b in small["blockers"]))
        unlabeled = self.m.validate_ready({"training_ready": False}, [{}] * 100, min_examples=50)
        self.assertFalse(unlabeled["ready"])
        ok = self.m.validate_ready({"training_ready": True, "provenance": "h"}, [{}] * 100, min_examples=50)
        self.assertTrue(ok["ready"])

    def test_validate_ready_blocks_replay_inflated_few_runs(self):
        # 100 examples but only 5 distinct runs (replay inflation) → not ready
        out = self.m.validate_ready({"training_ready": True, "provenance": "p"},
                                    [{}] * 100, min_examples=50, distinct_runs=5, min_distinct=20)
        self.assertFalse(out["ready"])
        self.assertTrue(any("distinct runs" in b for b in out["blockers"]))

    def test_qlora_config_is_pure_data_no_litellm(self):
        cfg = self.m.qlora_config()
        self.assertEqual(cfg["schema"], "aios.cls_qlora_config.v1")
        self.assertNotIn("litellm", json.dumps(cfg).lower())
        self.assertIn("trl", cfg["trainer"])

    def test_train_is_founder_gated(self):
        with tempfile.TemporaryDirectory() as d:
            ds = Path(d) / "x.jsonl"
            ds.write_text("{}\n", encoding="utf-8")
            # no apply, no GO → gated, never imports heavy deps
            out = self.m.train(ds, apply=False)
            self.assertEqual(out["status"], "gated")
            self.assertFalse(out["ran"])

    def test_export_dry_run_is_safe(self):
        with tempfile.TemporaryDirectory() as d:
            out = self.m.export(Path(d) / "ds.jsonl", apply=False)
            self.assertEqual(out["schema"], "aios.cls_trainset.v1")
            self.assertEqual(out["written"], 0)             # dry-run writes nothing
            self.assertIn("dry-run", out["mode"])


if __name__ == "__main__":
    unittest.main()
