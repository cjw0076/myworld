import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_control_snapshot.py"


class AiosControlSnapshotTest(unittest.TestCase):
    def write_fixture(self, root: Path) -> None:
        (root / "docs" / "contracts").mkdir(parents=True)
        (root / "docs" / "goals").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "aios_install.py").write_text("# installer fixture\n", encoding="utf-8")
        install_home = root / "home"
        launcher = install_home / ".local" / "bin" / "aios"
        service = install_home / ".config" / "systemd" / "user" / "aios.service"
        desktop = install_home / ".config" / "autostart" / "aios-control.desktop"
        for path in (launcher, service, desktop):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# AIOS_INSTALLER_MANAGED v=asc-0080\n", encoding="utf-8")
        (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
            """---
contract_id: ASC-0001
slug: demo
status: closed
goal: Demo contract.
created: now
closed: now
---

# ASC-0001 Demo

## AIOS Inputs Used

- MemoryOS: `trace_id=rtrace_demo123`
- CapabilityOS: `cap_demo_route`
- Hive: `run_20260512_000000_demo`

## Stop Conditions

- verification_gate_failed
- scope_violation
""",
            encoding="utf-8",
        )
        (root / "docs" / "goals" / "AIOS-GOAL-0001-demo.md").write_text(
            """---
goal_id: AIOS-GOAL-0001
slug: demo
status: active
---

# Demo Goal

## North Star

Build the loop.

## Preferred Next Improvements

- visual_control_application: show the loop.

## Completed Improvements

- self_resonant_repo_loop: route repo goals.
""",
            encoding="utf-8",
        )
        (root / "docs" / "goals" / "AIOS-GOAL-0001-evolution.md").write_text(
            """# AIOS Goal Evolution Plan

- monitor_health: `clear`
- readiness: `L6 repeatable`

## Recommendation

- path: `goal:visual_control_application`
""",
            encoding="utf-8",
        )
        state = root / ".aios" / "state"
        state.mkdir(parents=True)
        (state / "dispatches.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"dispatch_id": "asc-0001", "contract_id": "ASC-0001", "event": "created", "status": "created", "timestamp": "1"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "sent", "repo": "myworld", "status": "sent", "timestamp": "2"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "collected", "repo": "myworld", "status": "collected", "timestamp": "3"}),
                    json.dumps({"dispatch_id": "asc-0001", "event": "released", "status": "released", "reason": "verified", "timestamp": "4"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (state / "monitor_assessment.latest.json").write_text(
            json.dumps({"health": "clear", "findings": [], "next_actions": [{"action": "continue_observing"}]}),
            encoding="utf-8",
        )
        memory_dir = root / "memoryOS" / "memory"
        ontology_dir = root / "memoryOS" / "ontology"
        (memory_dir / "processed").mkdir(parents=True)
        ontology_dir.mkdir(parents=True)
        (memory_dir / "processed" / "nodes.jsonl").write_text('{"id":"n1"}\n{"id":"n2"}\n', encoding="utf-8")
        (ontology_dir / "edges.jsonl").write_text('{"id":"e1"}\n', encoding="utf-8")
        (ontology_dir / "hyperedges.jsonl").write_text('{"id":"h1"}\n', encoding="utf-8")
        (memory_dir / "objects.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"id": "mem_a", "status": "accepted"}),
                    json.dumps({"id": "mem_b", "status": "draft"}),
                    json.dumps({"id": "mem_c", "status": "rejected"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (memory_dir / "reviews.jsonl").write_text(
            json.dumps({"id": "review_a", "memory_object_id": "mem_a", "new_status": "accepted", "captured_at": "2026-05-14T00:00:00+09:00"}) + "\n",
            encoding="utf-8",
        )
        (memory_dir / "retrieval_traces.jsonl").write_text(
            json.dumps({"id": "rtrace_a", "selected": ["mem_a"]}) + "\n" + json.dumps({"id": "rtrace_b", "selected": []}) + "\n",
            encoding="utf-8",
        )
        (memory_dir / "sources.jsonl").write_text(json.dumps({"id": "src_a"}) + "\n", encoding="utf-8")
        invocation = root / ".aios" / "invocations" / "inv-demo"
        (invocation / "genesis").mkdir(parents=True)
        (invocation / "memory").mkdir()
        (invocation / "capability").mkdir()
        (invocation / "hive").mkdir()
        (invocation / "genesis" / "branches.json").write_text(json.dumps({"branches": [{"branch_id": "demo"}]}), encoding="utf-8")
        (invocation / "memory" / "context_pack.md").write_text("# Context pack\n\nselected_memory_ids: [mem_demo]\n", encoding="utf-8")
        (invocation / "capability" / "route.json").write_text(json.dumps({"recommendations": [{"id": "cap_demo"}]}), encoding="utf-8")
        (invocation / "hive" / "execution_plan.json").write_text(json.dumps({"candidate_worker": "hive.provider_loop"}), encoding="utf-8")
        envelope = {
            "schema_version": "aios.session_envelope.v1",
            "invocation_id": "inv-demo",
            "goal": "Show agent work",
            "created_at": "2026-05-14T00:00:00+09:00",
            "role_statuses": {"genesis": "passed", "memory": "passed", "capability": "passed", "hive": "passed"},
            "role_artifacts": {
                "genesis": ".aios/invocations/inv-demo/genesis/branches.json",
                "memory_context_pack": ".aios/invocations/inv-demo/memory/context_pack.md",
                "capability_route": ".aios/invocations/inv-demo/capability/route.json",
                "hive_execution_plan": ".aios/invocations/inv-demo/hive/execution_plan.json",
            },
            "executor_assignment": {"default_executor": "codex", "execution_owner": "hivemind"},
        }
        (invocation / "session_envelope.json").write_text(json.dumps(envelope), encoding="utf-8")
        (invocation / "receipt.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.invocation_receipt.v1",
                    "invocation_id": "inv-demo",
                    "created_at": "2026-05-14T00:00:00+09:00",
                    "overall_status": "passed",
                    "next_action": "dispatch_ready",
                    "session_envelope": ".aios/invocations/inv-demo/session_envelope.json",
                    "role_statuses": envelope["role_statuses"],
                }
            ),
            encoding="utf-8",
        )
        promotion = root / ".aios" / "promotions" / "promotion-demo"
        promotion.mkdir(parents=True)
        (promotion / "contract_seed.md").write_text("# Contract Seed\n", encoding="utf-8")
        (promotion / "promotion.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.session_promotion.v1",
                    "promotion_id": "promotion-demo",
                    "status": "proposed_contract_seed",
                    "goal": "Review promotion",
                    "created_at": "2026-05-14T00:01:00+09:00",
                    "session_envelope": {"ref": ".aios/invocations/inv-demo/session_envelope.json"},
                    "artifact_paths": {
                        "receipt": ".aios/promotions/promotion-demo/promotion.json",
                        "contract_seed": ".aios/promotions/promotion-demo/contract_seed.md",
                        "dispatch_preview": ".aios/invocations/inv-demo/dispatch/packets.json",
                    },
                    "next_action": "operator_assign_asc_accept_and_dispatch",
                    "execution_started": False,
                }
            ),
            encoding="utf-8",
        )
        chat = root / ".aios" / "chat" / "control-center"
        chat.mkdir(parents=True)
        gate_pack = root / ".aios" / "gate" / "founder" / "gate_pack.json"
        gate_pack.parent.mkdir(parents=True)
        gate_pack.write_text(
            json.dumps(
                {
                    "schema_version": "aios.gate.pack.v1",
                    "id": "gatepack_fixture",
                    "status": "active",
                    "generated_at": "2026-05-14T00:00:00+09:00",
                    "source_pair_count": 4,
                    "accepted_memory_hint_count": 1,
                    "rules": {"memoryos_context_before_execution": True},
                    "examples": [{"id": "gpair_fixture"}],
                }
            ),
            encoding="utf-8",
        )
        (gate_pack.parent / "chair_runtime.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.gate.chair_runtime.v1",
                    "status": "active",
                    "mode": "internal_evidence_synthesizer",
                    "updated_at": "2026-05-14T00:01:00+09:00",
                }
            ),
            encoding="utf-8",
        )
        (chat / "gate_chair_turns.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "aios.chat.gate_chair_turn.v1",
                    "turn_id": "gatechair_fixture",
                    "executed": True,
                    "chair_meta": {
                        "status": "success",
                        "return_code": 0,
                        "meta": {"mode": "internal_evidence_synthesizer", "model": "deterministic"},
                    },
                    "created_at": "2026-05-14T00:02:30+09:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (chat / "memory_drafts.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.chat.memory_drafts.v1",
                    "memory_drafts": [
                        {
                            "type": "chat_turn_summary",
                            "origin": "aios_chat",
                            "status": "draft",
                            "confidence": 0.72,
                            "conversation_id": "control-center",
                            "content": "User asked about memory review visibility and AIOS answered with a draft-first plan.",
                            "raw_refs": ["messages.jsonl", "cost.json"],
                            "provenance": {"created_at": "2026-05-14T00:02:00+09:00", "source": "aios_chat"},
                        },
                        {
                            "type": "genesis_friction_signal",
                            "origin": "aios_chat_genesis",
                            "status": "draft",
                            "confidence": 0.67,
                            "conversation_id": "control-center",
                            "content": "GenesisOS projected discomfort/need signal: hidden review queues make memory feel absent.",
                            "raw_refs": ["messages.jsonl", ".aios/invocations/inv-demo/genesis/branches.json"],
                            "provenance": {
                                "created_at": "2026-05-14T00:03:00+09:00",
                                "source": "aios_chat",
                                "genesis_ref": ".aios/invocations/inv-demo/genesis/branches.json",
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        review_receipt = {
            "schema_version": "aios.memory_draft_review_request.v1",
            "request_id": "mdrev-demo",
            "created_at": "2026-05-14T00:04:00+09:00",
            "status": "sent_to_memoryOS_inbox",
            "source_artifact": ".aios/chat/control-center/memory_drafts.json",
            "draft_id": "control-center:1",
            "draft_type": "genesis_friction_signal",
            "artifact_paths": {
                "packet": ".aios/inbox/memoryOS/mdrev-demo.memoryOS.json",
                "return_to": ".aios/outbox/memoryOS/mdrev-demo.memoryOS.result.json",
            },
        }
        (state / "memory_draft_reviews.jsonl").write_text(json.dumps(review_receipt) + "\n", encoding="utf-8")
        outbox = root / ".aios" / "outbox" / "memoryOS"
        outbox.mkdir(parents=True)
        (outbox / "mdrev-demo.memoryOS.result.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.dispatch.result.v1",
                    "status": "passed",
                    "dispatch_id": "mdrev-demo",
                    "target_repo": "memoryOS",
                    "executed_at": "2026-05-14T00:05:00+09:00",
                    "review_request": {
                        "request_id": "mdrev-demo",
                        "source_artifact": ".aios/chat/control-center/memory_drafts.json",
                        "draft_id": "control-center:1",
                        "draft_type": "genesis_friction_signal",
                        "review_decision": "queued_for_memoryos_review",
                    },
                }
            ),
            encoding="utf-8",
        )

    def run_cli(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["HOME"] = (root / "home").as_posix()
        env["XDG_CONFIG_HOME"] = (root / "home" / ".config").as_posix()
        env["AIOS_INSTALL_SKIP_SYSTEMCTL"] = "1"
        return subprocess.run(
            [sys.executable, SCRIPT.as_posix(), "--root", root.as_posix(), *args],
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

    def test_snapshot_contains_control_plane_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(root, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.control_snapshot.v1")
            self.assertEqual(data["goals"]["active"]["id"], "AIOS-GOAL-0001")
            self.assertEqual(data["goals"]["evolution"]["recommendation"], "goal:visual_control_application")
            self.assertEqual(data["contracts"]["counts"]["closed"], 1)
            self.assertEqual(data["dispatches"]["counts"]["released"], 1)
            self.assertEqual(data["monitor"]["health"], "clear")
            self.assertEqual(data["installation"]["status"], "installed_stopped")
            self.assertTrue(data["installation"]["command"]["launcher_installed"])
            self.assertTrue(data["installation"]["service"]["installed"])
            self.assertEqual(data["installation"]["control_center"]["url"], "http://127.0.0.1:8765/")
            self.assertTrue(data["installation"]["gate_chair"]["enabled"])
            self.assertEqual(data["installation"]["gate_chair"]["state"], "internal")
            self.assertEqual(data["installation"]["gate_chair"]["mode"], "internal_evidence_synthesizer")
            self.assertTrue(data["installation"]["gate_chair"]["runtime_config_active"])
            self.assertEqual(data["installation"]["gate_chair"]["runtime_config"]["mode"], "internal_evidence_synthesizer")
            self.assertEqual(data["installation"]["gate_chair"]["latest_turn"]["status"], "success")
            self.assertEqual(data["aios_inputs"]["memory_traces"], ["rtrace_demo123"])
            self.assertEqual(data["aios_inputs"]["capability_routes"], ["cap_demo_route"])
            self.assertEqual(data["aios_inputs"]["hive_runs"], ["run_20260512_000000_demo"])
            self.assertIn("stop_lanes", data)
            latest = data["invocations"]["latest"][0]
            self.assertEqual(latest["invocation_id"], "inv-demo")
            self.assertEqual(latest["goal"], "Show agent work")
            self.assertEqual(latest["executor_assignment"]["default_executor"], "codex")
            self.assertIn("memory_context_pack", latest["artifact_previews"])
            self.assertIn("selected_memory_ids", latest["artifact_previews"]["memory_context_pack"]["preview"])
            self.assertEqual(data["genesis_lens"]["source_invocation"], "inv-demo")
            self.assertEqual(data["genesis_lens"]["branches"][0]["branch_id"], "demo")
            self.assertEqual(data["promotions"]["total"], 1)
            self.assertEqual(data["promotions"]["items"][0]["promotion_id"], "promotion-demo")
            self.assertEqual(data["promotions"]["items"][0]["session_envelope_ref"], ".aios/invocations/inv-demo/session_envelope.json")
            self.assertEqual(data["promotions"]["items"][0]["contract_seed"], ".aios/promotions/promotion-demo/contract_seed.md")
            self.assertEqual(data["memory_draft_queue"]["total"], 2)
            self.assertEqual(data["memory_draft_queue"]["counts"]["genesis_friction_signal"], 1)
            self.assertEqual(data["memory_draft_queue"]["items"][0]["type"], "genesis_friction_signal")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_state"], "review_result_ready")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_request_id"], "mdrev-demo")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_result"], "queued_for_memoryos_review")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_result_ref"], ".aios/outbox/memoryOS/mdrev-demo.memoryOS.result.json")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["source_artifact"], ".aios/chat/control-center/memory_drafts.json")
            self.assertIn("hidden review queues", data["memory_draft_queue"]["items"][0]["content_preview"])
            self.assertEqual(data["friction_radar"]["items"][0]["need"], "continue_observing")
            self.assertEqual(data["os_observatory"]["memory"]["nodes"], 2)
            self.assertEqual(data["os_observatory"]["memory"]["edges"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["accepted"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["draft"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["rejected"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["retrieval_traces"], 2)
            self.assertEqual(data["os_observatory"]["memory"]["hyperedges"], 1)
            self.assertIn("MemoryOS", [row["label"] for row in data["os_observatory"]["lanes"]])

    def test_writes_json_and_browser_data_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)

            result = self.run_cli(
                root,
                "--write-json",
                "apps/control/aios-control-snapshot.json",
                "--write-js",
                "apps/control/aios-control-data.js",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            json_path = root / "apps" / "control" / "aios-control-snapshot.json"
            js_path = root / "apps" / "control" / "aios-control-data.js"
            self.assertTrue(json_path.exists())
            self.assertTrue(js_path.exists())
            self.assertIn("window.AIOS_CONTROL_SNAPSHOT", js_path.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema_version"], "aios.control_snapshot.v1")

    def test_check_app_js_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(root, "--check-app-js", "apps/control/app.js", "--json")

            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertFalse(data["ok"])
            self.assertIn("app js not found", data["errors"])


if __name__ == "__main__":
    unittest.main()
