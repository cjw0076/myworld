"""ASC-0214 dogfood-route tests."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
import importlib.util

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "aios_dogfood_route.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("aios_dogfood_route_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _seed(td: Path) -> tuple[Path, Path]:
    mem = td / "memory"
    contracts = td / "contracts"
    mem.mkdir()
    contracts.mkdir()

    (mem / "reference_alpha.md").write_text(
        "---\nname: reference-alpha\ndescription: cited by a contract.\nmetadata:\n  type: reference\n---\n\nbody.\n",
        encoding="utf-8",
    )
    (mem / "reference_beta.md").write_text(
        "---\nname: reference-beta\ndescription: uncited topic.\nmetadata:\n  type: reference\n---\n\nbody.\n",
        encoding="utf-8",
    )

    (contracts / "ASC-9001-demo.md").write_text(
        "---\ncontract_id: ASC-9001\n---\n\nThis cites [[reference-alpha]] here.\n",
        encoding="utf-8",
    )
    return mem, contracts


class DogfoodRouteTest(unittest.TestCase):
    def test_uncited_detected(self):
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _seed(Path(td))
            mod = _load_module()
            corpus = mod.contracts_corpus(contracts)
            uncited = mod.uncited_references(mem, corpus)
        names = [p.name for p in uncited]
        self.assertIn("reference_beta.md", names)
        self.assertNotIn("reference_alpha.md", names)

    def test_candidate_payload_shape(self):
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _seed(Path(td))
            mod = _load_module()
            corpus = mod.contracts_corpus(contracts)
            uncited = mod.uncited_references(mem, corpus)
            cand = mod.candidate_from_memo(uncited[0])
        self.assertEqual(cand["memo"], "reference_beta.md")
        self.assertEqual(cand["slug"], "reference-beta")
        self.assertIn("uncited topic", cand["description"])
        self.assertIn("staleness_days", cand)
        self.assertIn("proposed_action_prompt", cand)

    def test_cli_json_output(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            mem, contracts = _seed(Path(td))
            r = subprocess.run(
                [sys.executable, str(SCRIPT),
                 "--memory-dir", str(mem),
                 "--contracts-dir", str(contracts),
                 "--threshold-days", "0",
                 "--json"],
                capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
        self.assertEqual(out["schema_version"], "aios.dogfood_route.v1")
        self.assertEqual(out["uncited_total"], 1)
        self.assertEqual(out["candidates_after_threshold"], 1)
        self.assertEqual(out["candidates"][0]["memo"], "reference_beta.md")


if __name__ == "__main__":
    unittest.main()
