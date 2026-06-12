"""ID allocation must survive the fossil quarantine: an ASC number is never reissued,
even after the contract that carried it moves to docs/_history/contracts/."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

from aios_contract_autodraft import next_contract_id


class HistoryAwareNumberingTests(unittest.TestCase):
    def test_quarantined_ids_still_count(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            docs = Path(t)
            contracts = docs / "contracts"
            history = docs / "_history" / "contracts"
            contracts.mkdir(parents=True)
            history.mkdir(parents=True)
            (contracts / "ASC-0010-active.md").write_text("status: accepted\n")
            (history / "ASC-0224-old.md").write_text("status: closed\n")
            # without history-awareness this would mint ASC-0011 — a reused identity
            self.assertEqual(next_contract_id(contracts), "ASC-0225")

    def test_plain_dir_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            contracts = Path(t) / "contracts"
            contracts.mkdir()
            (contracts / "ASC-0003-x.md").write_text("status: proposed\n")
            self.assertEqual(next_contract_id(contracts), "ASC-0004")


if __name__ == "__main__":
    unittest.main()
