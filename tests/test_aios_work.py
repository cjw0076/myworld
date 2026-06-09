import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())
import aios_work as W

class WorkTests(unittest.TestCase):
    def test_goal_spans_sessions_and_resumes(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            w = W.start_work("ship copilot", work_dir=d)
            W.attach_run(w.work_id, "run-a", work_dir=d)
            W.attach_run(w.work_id, "run-b", work_dir=d)
            W.set_status(w.work_id, "paused", work_dir=d)
            r = W.resume(w.work_id, work_dir=d, runs_dir=d)
            self.assertEqual(r["sessions"], 2)
            self.assertTrue(r["resumable"])          # paused → resumable
            self.assertEqual(r["status"], "paused")

    def test_lineage_fork(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            p = W.start_work("parent goal", work_dir=d)
            c = W.fork_work(p.work_id, "child goal", work_dir=d)
            self.assertEqual(c.parent_work, p.work_id)

    def test_completed_not_resumable(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            w = W.start_work("g", work_dir=d)
            W.set_status(w.work_id, "completed", work_dir=d)
            self.assertFalse(W.resume(w.work_id, work_dir=d, runs_dir=d)["resumable"])

    def test_bad_status_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            w = W.start_work("g", work_dir=d)
            with self.assertRaises(ValueError):
                W.set_status(w.work_id, "nonsense", work_dir=d)

if __name__ == "__main__":
    unittest.main()
