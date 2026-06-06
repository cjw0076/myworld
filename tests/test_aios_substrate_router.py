import sys
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_substrate_router as r


class SubstrateRouterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._models = r.list_local_models
        self._gen = r.generate_local
        r.list_local_models = lambda: ["m1", "m2", "m3"]

    def tearDown(self) -> None:
        r.list_local_models = self._models
        r.generate_local = self._gen

    def test_falls_back_on_error(self) -> None:
        def gen(model, prompt, timeout=180):
            if model == "m1":
                raise RuntimeError("down")
            return "result from " + model

        r.generate_local = gen
        res = r.generate("p", prefer=["m1", "m2"])
        self.assertTrue(res["ok"])
        self.assertEqual(res["substrate"], "m2")
        self.assertEqual(res["trail"][0], {"substrate": "m1", "result": "error: down"})

    def test_all_fail_returns_not_ok(self) -> None:
        def gen(model, prompt, timeout=180):
            raise RuntimeError("x")

        r.generate_local = gen
        res = r.generate("p", prefer=["m1", "m2"])
        self.assertFalse(res["ok"])
        self.assertIsNone(res["substrate"])

    def test_skips_not_installed(self) -> None:
        r.generate_local = lambda model, prompt, timeout=180: "ok " + model
        res = r.generate("p", prefer=["notthere", "m2"])
        self.assertEqual(res["substrate"], "m2")
        self.assertEqual(res["trail"][0]["result"], "not installed")

    def test_unreachable_daemon_fails_fast(self) -> None:
        r.list_local_models = lambda: []  # ollama down / no models
        res = r.generate("p", prefer=["m1", "m2"])
        self.assertFalse(res["ok"])
        self.assertEqual(res["trail"][0]["substrate"], "ollama")

    def test_empty_falls_through(self) -> None:
        r.generate_local = lambda model, prompt, timeout=180: "" if model == "m1" else "text"
        res = r.generate("p", prefer=["m1", "m2"])
        self.assertEqual(res["substrate"], "m2")
        self.assertEqual(res["trail"][0]["result"], "empty")


if __name__ == "__main__":
    unittest.main()
