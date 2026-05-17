import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.aios_address import build_index, parse_address, resolve


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


class AiosAddressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs" / "contracts").mkdir(parents=True)
        (self.root / "docs" / "contracts" / "ASC-0101-test-contract.md").write_text(
            """---
contract_id: ASC-0101
slug: test-contract
status: closed
goal: Test address contract resolution.
---

# ASC-0101 Test
""",
            encoding="utf-8",
        )
        write_jsonl(
            self.root / ".aios" / "state" / "dispatches.jsonl",
            [
                {
                    "dispatch_id": "asc-0101.myworld",
                    "event": "created",
                    "status": "pending",
                    "goal": "Resolve typed addresses",
                    "contract_path": "docs/contracts/ASC-0101-test-contract.md",
                },
                {
                    "dispatch_id": "asc-0101.myworld",
                    "event": "collected",
                    "status": "closed",
                    "result": ".aios/outbox/myworld/asc-0101.myworld.result.json",
                },
            ],
        )
        write_jsonl(
            self.root / "memoryOS" / "memory" / "objects.jsonl",
            [
                {
                    "id": "mem_test",
                    "status": "draft",
                    "content": "Accepted memory text that should be summarized, not exposed remotely.",
                    "raw_refs": [
                        "/home/user/private/raw_exports/source.md",
                        "docs/contracts/ASC-0101-test-contract.md",
                    ],
                }
            ],
        )
        write_jsonl(
            self.root / "memoryOS" / "memory" / "sources.jsonl",
            [{"id": "src_test", "path": "docs/contracts/ASC-0101-test-contract.md", "type": "contract"}],
        )
        write_jsonl(
            self.root / "memoryOS" / "memory" / "retrieval_traces.jsonl",
            [{"id": "trace_test", "evidence_state": "complete", "evidence_refs": ["aios://memory/mem_test"]}],
        )
        write_jsonl(
            self.root / "memoryOS" / "ontology" / "hyperedges.jsonl",
            [{"id": "hedge_test", "type": "supports", "evidence_refs": ["aios://memory/mem_test"]}],
        )
        run_dir = self.root / "hivemind" / ".runs" / "run_test"
        run_dir.mkdir(parents=True)
        (run_dir / "run_state.json").write_text(
            json.dumps({"status": "completed", "user_request": "Run a typed address smoke test."}),
            encoding="utf-8",
        )
        (run_dir / "result.md").write_text("done\n", encoding="utf-8")
        fixture = self.root / "CapabilityOS" / "tests" / "fixtures" / "capabilities.json"
        fixture.parent.mkdir(parents=True)
        fixture.write_text(
            json.dumps(
                {
                    "capabilities": [
                        {
                            "id": "cap_test",
                            "name": "Test capability",
                            "description": "A recommendation-only test capability.",
                            "status": "active",
                            "privacy": "local",
                            "evidence_refs": ["docs/AIOS_ADDRESS_SPACE.md"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_parse_requires_aios_scheme(self) -> None:
        parsed = parse_address("aios://contract/ASC-0101")
        self.assertEqual(parsed.kind, "contract")
        self.assertEqual(parsed.identifier, "ASC-0101")
        with self.assertRaises(ValueError):
            parse_address("contract/ASC-0101")

    def test_resolve_contract_dispatch_and_run(self) -> None:
        contract = resolve(self.root, "aios://contract/ASC-0101")
        self.assertTrue(contract["found"])
        self.assertEqual(contract["status"], "closed")
        self.assertEqual(contract["owner_os"], "myworld")

        dispatch = resolve(self.root, "aios://dispatch/asc-0101.myworld")
        self.assertTrue(dispatch["found"])
        self.assertEqual(dispatch["status"], "closed")
        self.assertIn(".aios/state/dispatches.jsonl", dispatch["storage_refs"])

        run = resolve(self.root, "aios://run/hive/run_test")
        self.assertTrue(run["found"])
        self.assertEqual(run["owner_repo"], "hivemind")
        self.assertEqual(run["record"]["artifact_count"], 2)

    def test_resolve_memory_source_trace_and_hyperedge(self) -> None:
        memory = resolve(self.root, "aios://memory/mem_test")
        self.assertTrue(memory["found"])
        self.assertEqual(memory["owner_os"], "MemoryOS")
        self.assertIn("docs/contracts/ASC-0101-test-contract.md", memory["provenance_refs"])

        source = resolve(self.root, "aios://source/src_test")
        trace = resolve(self.root, "aios://trace/trace_test")
        hyperedge = resolve(self.root, "aios://hyperedge/hedge_test")
        self.assertTrue(source["found"])
        self.assertTrue(trace["found"])
        self.assertTrue(hyperedge["found"])
        self.assertEqual(trace["provenance_refs"], ["aios://memory/mem_test"])

    def test_remote_redaction_removes_private_memory_payloads(self) -> None:
        memory = resolve(self.root, "aios://memory/mem_test", audience="remote")
        self.assertTrue(memory["found"])
        self.assertNotIn("raw_refs", memory["record"])
        self.assertNotIn("content", memory["record"])
        self.assertNotIn("/home/user/private/raw_exports/source.md", memory["provenance_refs"])
        self.assertIn("Accepted memory text", memory["summary"])

    def test_resolve_capability_cards_and_provider_route(self) -> None:
        card = resolve(self.root, "aios://capability/cap_test")
        self.assertTrue(card["found"])
        self.assertEqual(card["owner_os"], "CapabilityOS")
        self.assertTrue(card["record"]["recommendation_only"])

        provider = resolve(self.root, "aios://capability/provider-route/codex")
        self.assertTrue(provider["found"])
        self.assertFalse(provider["record"]["executes_tools"])
        self.assertTrue(provider["record"]["recommendation_only"])

    def test_build_index_counts_address_spaces(self) -> None:
        index = build_index(self.root)
        self.assertEqual(index["schema_version"], "aios.address.index.v1")
        self.assertEqual(index["counts"]["contract"], 1)
        self.assertEqual(index["counts"]["memory"], 1)
        self.assertEqual(index["counts"]["capability"], 1)
        self.assertEqual(index["counts"]["hive_run"], 1)
        self.assertEqual(index["samples"]["contract"], ["aios://contract/ASC-0101"])

    def test_cli_resolve_outputs_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "scripts" / "aios_address.py"),
                "--root",
                str(self.root),
                "resolve",
                "aios://contract/ASC-0101",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["found"])
        self.assertEqual(payload["schema_version"], "aios.address.resolution.v1")


if __name__ == "__main__":
    unittest.main()
