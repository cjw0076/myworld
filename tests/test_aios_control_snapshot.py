import json
import os
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_control_snapshot.py"


def load_snapshot_module():
    spec = importlib.util.spec_from_file_location("aios_control_snapshot_test_module", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        archive_inbox = root / ".aios" / "archive" / "inbox" / "myworld"
        archive_inbox.mkdir(parents=True)
        (archive_inbox / "asc-0001.myworld.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.dispatch.v1",
                    "dispatch_id": "asc-0001",
                    "contract_id": "ASC-0001",
                    "target_repo": "myworld",
                    "session_envelope": {
                        "ref": ".aios/invocations/inv-demo/session_envelope.json",
                        "memory_context": {
                            "context_pack": ".aios/invocations/inv-demo/memory/context_pack.md",
                            "retrieval_trace": "rtrace_dispatch_demo",
                            "signal_coverage": "1.0",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        (state / "monitor_assessment.latest.json").write_text(
            json.dumps(
                {
                    "health": "watch",
                    "findings": [
                        {
                            "code": "genesis_prompt_prison_advisory",
                            "severity": "info",
                            "owner": "GenesisOS",
                            "action": "review_prompt_prison_escape_vectors",
                            "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
                            "alert": {
                                "sample": [
                                    {
                                        "contract_id": "ASC-0999",
                                        "path": "docs/contracts/ASC-0999-review-promotion.md",
                                        "status": "accepted",
                                        "confidence": 0.75,
                                        "escape_vectors": ["restate as schema", "negate assumptions"],
                                        "signatures": [
                                            {
                                                "signature": "mono-language",
                                                "evidence": "long prose",
                                                "escape_vector": "restate as schema",
                                            }
                                        ],
                                    }
                                ]
                            },
                        }
                    ],
                    "next_actions": [{"action": "review_prompt_prison_escape_vectors", "owner": "GenesisOS", "severity": "info"}],
                }
            ),
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
                    json.dumps(
                        {
                            "id": "mem_a",
                            "status": "accepted",
                            "confidence": 0.91,
                            "evidence_state": "reviewed",
                            "content": "Founder wants MemoryOS retrieval to show selected memory content and provenance, not just abstract counts.",
                            "raw_refs": ["docs/AGENT_WORKLOG.md"],
                            "attrs": {"source_artifact_id": "src_a"},
                        }
                    ),
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
            json.dumps(
                {
                    "id": "rtrace_a",
                    "created_at": "2026-05-14T00:01:00+09:00",
                    "query": "show MemoryOS retrieval evidence",
                    "role": "hive",
                    "privacy_filter": "local",
                    "signal_coverage": 1.0,
                    "selected": [{"id": "mem_a", "confidence": 0.91, "evidence_state": "reviewed", "status": "accepted"}],
                    "attrs": {"explain": {"candidate_counts": {"considered": 2, "selected": 1}}},
                }
            )
            + "\n"
            + json.dumps({"id": "rtrace_b", "selected": []})
            + "\n",
            encoding="utf-8",
        )
        (memory_dir / "sources.jsonl").write_text(json.dumps({"id": "src_a", "kind": "local_file", "path": "docs/AGENT_WORKLOG.md"}) + "\n", encoding="utf-8")
        invocation = root / ".aios" / "invocations" / "inv-demo"
        (invocation / "genesis").mkdir(parents=True)
        (invocation / "memory").mkdir()
        (invocation / "capability").mkdir()
        (invocation / "hive").mkdir()
        (invocation / "genesis" / "branches.json").write_text(
            json.dumps(
                {
                    "authority": "speculative_only",
                    "branches": [
                        {
                            "branch_id": "demo",
                            "type": "constraint_removal",
                            "premise": "Make hidden AIOS queues visible.",
                            "what_it_breaks": "The interface hides discomfort after critique.",
                            "why_it_might_matter": "Users need to compare worldlines before execution.",
                            "contract_seed": "Add a GenesisOS worldline evidence map.",
                            "risk": "Speculative UI affordance.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
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
        (promotion / "materialization.json").write_text(
            json.dumps(
                {
                    "schema_version": "aios.promotion_contract_materialization.v1",
                    "promotion_id": "promotion-demo",
                    "promotion_receipt": ".aios/promotions/promotion-demo/promotion.json",
                    "contract_id": "ASC-0999",
                    "contract_path": "docs/contracts/ASC-0999-review-promotion.md",
                    "status": "proposed_contract_materialized",
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
        (state / "memory_review_evidence.jsonl").write_text(
            json.dumps(
                {
                    "schema_version": "aios.memory_review_evidence.v1",
                    "evidence_id": "mrevd-demo",
                    "created_at": "2026-05-14T00:06:00+09:00",
                    "status": "evidence_recorded",
                    "source_artifact": ".aios/chat/control-center/memory_drafts.json",
                    "draft_id": "control-center:1",
                    "draft_type": "genesis_friction_signal",
                    "note": "Founder repeated that hidden review queues make memory feel absent.",
                    "evidence_artifact": ".aios/chat/control-center/messages.jsonl",
                    "artifact_paths": {
                        "evidence": ".aios/memory_review_evidence/mrevd-demo/evidence.json",
                        "evidence_artifact": ".aios/chat/control-center/messages.jsonl",
                    },
                    "execution_started": False,
                }
            )
            + "\n",
            encoding="utf-8",
        )
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
                        "review_decision": "needs_more_evidence",
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
            ask_dir = root / ".aios" / "asks" / "ask-demo"
            ask_dir.mkdir(parents=True)
            (ask_dir / "goal.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.ask.v1",
                        "ask_id": "ask-demo",
                        "created_at": "2026-05-18T00:00:00+09:00",
                        "goal": "Make the OS board useful",
                    }
                ),
                encoding="utf-8",
            )
            (ask_dir / "receipt.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.ask.receipt.v1",
                        "ask_id": "ask-demo",
                        "created_at": "2026-05-18T00:00:00+09:00",
                        "goal": "Make the OS board useful",
                        "status": "passed",
                        "invocation_status": "passed",
                        "next_action": "review_instruction_and_dispatch",
                        "invocation_role_statuses": {
                            "memory": "passed",
                            "capability": "passed",
                            "genesis": "passed",
                            "hive": "passed",
                        },
                        "artifact_paths": {
                            "goal": ".aios/asks/ask-demo/goal.json",
                            "instruction": ".aios/asks/ask-demo/instruction.md",
                            "praxis": ".aios/asks/ask-demo/praxis.json",
                            "contract_seed": ".aios/asks/ask-demo/contract_seed.md",
                            "invocation_receipt": ".aios/invocations/ask-demo/receipt.json",
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(root, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["schema_version"], "aios.control_snapshot.v1")
            self.assertEqual(data["goals"]["active"]["id"], "AIOS-GOAL-0001")
            self.assertEqual(data["goals"]["evolution"]["recommendation"], "goal:visual_control_application")
            self.assertEqual(data["contracts"]["counts"]["closed"], 1)
            self.assertEqual(data["dispatches"]["counts"]["released"], 1)
            self.assertTrue(data["dispatches"]["latest"][0]["memory_context"]["memory_backed"])
            self.assertEqual(data["dispatches"]["latest"][0]["memory_context"]["retrieval_trace"], "rtrace_dispatch_demo")
            self.assertEqual(data["dispatches"]["latest"][0]["memory_context"]["signal_coverage"], "1.0")
            self.assertEqual(data["dispatches"]["latest"][0]["memory_context"]["packet"], ".aios/archive/inbox/myworld/asc-0001.myworld.json")
            self.assertEqual(data["monitor"]["health"], "watch")
            self.assertEqual(data["installation"]["status"], "installed_stopped")
            self.assertTrue(data["installation"]["command"]["launcher_installed"])
            self.assertTrue(data["installation"]["service"]["installed"])
            self.assertEqual(data["installation"]["control_center"]["url"], "http://127.0.0.1:8765/")
            self.assertTrue(data["installation"]["gate_chair"]["enabled"])
            self.assertEqual(data["installation"]["gate_chair"]["state"], "internal")
            self.assertEqual(data["installation"]["gate_chair"]["mode"], "internal_evidence_synthesizer")
            self.assertFalse(data["installation"]["gate_chair"]["demoted"])
            self.assertTrue(data["installation"]["gate_chair"]["runtime_preview"]["nodes"])
            self.assertIn("produces", [edge["kind"] for edge in data["installation"]["gate_chair"]["runtime_preview"]["edges"]])
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
            self.assertTrue(data["genesis_lens"]["worldline_preview"]["nodes"])
            self.assertIn("provokes", [edge["kind"] for edge in data["genesis_lens"]["worldline_preview"]["edges"]])
            self.assertIn("invents", [edge["kind"] for edge in data["genesis_lens"]["worldline_preview"]["edges"]])
            self.assertEqual(data["promotions"]["total"], 1)
            self.assertEqual(data["promotions"]["next_contract_id"], "ASC-0002")
            self.assertEqual(data["promotions"]["items"][0]["promotion_id"], "promotion-demo")
            self.assertEqual(data["promotions"]["items"][0]["next_contract_id"], "ASC-0002")
            self.assertEqual(data["promotions"]["items"][0]["session_envelope_ref"], ".aios/invocations/inv-demo/session_envelope.json")
            self.assertEqual(data["promotions"]["items"][0]["contract_seed"], ".aios/promotions/promotion-demo/contract_seed.md")
            self.assertEqual(data["promotions"]["items"][0]["materialized_contract_id"], "ASC-0999")
            self.assertEqual(data["promotions"]["items"][0]["materialized_contract"], "docs/contracts/ASC-0999-review-promotion.md")
            self.assertEqual(data["promotions"]["items"][0]["materialization_receipt"], ".aios/promotions/promotion-demo/materialization.json")
            self.assertEqual(data["asks"]["total"], 1)
            self.assertEqual(data["asks"]["latest"][0]["ask_id"], "ask-demo")
            self.assertEqual(data["asks"]["latest"][0]["contract_seed"], ".aios/asks/ask-demo/contract_seed.md")
            self.assertEqual(data["asks"]["latest"][0]["role_statuses"]["genesis"], "passed")
            self.assertEqual(data["memory_draft_queue"]["total"], 2)
            self.assertEqual(data["memory_draft_queue"]["counts"]["genesis_friction_signal"], 1)
            self.assertEqual(data["memory_draft_queue"]["items"][0]["type"], "genesis_friction_signal")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_state"], "review_result_ready")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_request_id"], "mdrev-demo")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_result"], "needs_more_evidence")
            self.assertIn("kept this candidate as draft", data["memory_draft_queue"]["items"][0]["review_reason"])
            self.assertIn("corroborating artifact", data["memory_draft_queue"]["items"][0]["next_evidence"])
            self.assertEqual(data["memory_draft_queue"]["items"][0]["review_result_ref"], ".aios/outbox/memoryOS/mdrev-demo.memoryOS.result.json")
            self.assertEqual(data["memory_draft_queue"]["items"][0]["evidence_count"], 1)
            self.assertEqual(data["memory_draft_queue"]["items"][0]["latest_evidence_ref"], ".aios/memory_review_evidence/mrevd-demo/evidence.json")
            self.assertIn("hidden review queues", data["memory_draft_queue"]["items"][0]["latest_evidence_note"])
            self.assertEqual(data["memory_draft_queue"]["items"][0]["source_artifact"], ".aios/chat/control-center/memory_drafts.json")
            self.assertIn("hidden review queues", data["memory_draft_queue"]["items"][0]["content_preview"])
            self.assertEqual(data["friction_radar"]["items"][0]["need"], "review_prompt_prison_escape_vectors")
            self.assertEqual(data["friction_radar"]["items"][0]["contracts"][0]["contract_id"], "ASC-0999")
            self.assertIn("restate as schema", data["friction_radar"]["items"][0]["contracts"][0]["escape_vectors"])
            self.assertEqual(data["friction_radar"]["items"][0]["contracts"][0]["signatures"][0]["signature"], "mono-language")
            self.assertEqual(data["os_observatory"]["memory"]["nodes"], 2)
            self.assertEqual(data["os_observatory"]["memory"]["edges"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["accepted"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["draft"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["rejected"], 1)
            self.assertEqual(data["os_observatory"]["memory"]["retrieval_traces"], 2)
            self.assertEqual(data["os_observatory"]["memory"]["hyperedges"], 1)
            self.assertTrue(data["os_observatory"]["memory"]["graph_preview"]["nodes"])
            self.assertIn(
                {"from": "rtrace_a", "to": "mem_a", "kind": "retrieved"},
                data["os_observatory"]["memory"]["graph_preview"]["edges"],
            )
            memory_trace = data["os_observatory"]["memory"]["recent_traces"][1]
            self.assertEqual(memory_trace["id"], "rtrace_a")
            self.assertEqual(memory_trace["selected_count"], 1)
            self.assertEqual(memory_trace["candidate_counts"]["considered"], 2)
            self.assertEqual(memory_trace["selected_memories"][0]["id"], "mem_a")
            self.assertIn("selected memory content", memory_trace["selected_memories"][0]["content_preview"])
            self.assertEqual(memory_trace["selected_memories"][0]["source_path"], "docs/AGENT_WORKLOG.md")
            self.assertIn("MemoryOS", [row["label"] for row in data["os_observatory"]["lanes"]])

    def test_contract_snapshot_marks_weak_session_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract_dir = root / "docs" / "contracts"
            contract_dir.mkdir(parents=True)
            (contract_dir / "ASC-0199-aios-session.md").write_text(
                """---
contract_id: ASC-0199
slug: aios-session
status: proposed
goal: 현재 상태 알려줘
origin: AIOS reviewed session promotion
---

# ASC-0199 Aios Session

## AIOS Role Evidence

- signal_coverage: `0.0`
- recommended_tools: `pending_or_not_required`

## Stop Conditions

- scope_not_narrowed_before_dispatch
""",
                encoding="utf-8",
            )
            module = load_snapshot_module()

            contracts = module.load_contracts(root)

            self.assertEqual(contracts["quality_counts"]["weak_proposed"], 1)
            row = contracts["latest"][0]
            self.assertEqual(row["quality_state"], "weak_proposed")
            self.assertEqual(row["review_action"], "revise_or_supersede_before_acceptance")
            self.assertIn("goal_too_short_for_contract_acceptance", row["quality_warnings"])
            self.assertIn("memory_signal_coverage_zero", row["quality_warnings"])

    def test_visual_fix_promotion_marks_visual_focus_mitigation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs" / "contracts").mkdir(parents=True)
            (root / "docs" / "contracts" / "ASC-0001-demo.md").write_text(
                "---\ncontract_id: ASC-0001\nstatus: closed\n---\n# Demo\n",
                encoding="utf-8",
            )
            source = root / ".aios" / "visual_verification" / "vis-source" / "receipt.json"
            source.parent.mkdir(parents=True)
            source.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.visual_verification.v1",
                        "created_at": "2026-05-18T00:00:00+09:00",
                        "url": "http://127.0.0.1:8765/?mode=operator#contract-flow",
                        "status": "degraded",
                        "screenshot_path": ".aios/screenshots/vis-source.png",
                        "stop_conditions": ["browser_visual_evidence_suspicious"],
                    }
                ),
                encoding="utf-8",
            )
            passed = root / ".aios" / "visual_verification" / "vis-focus" / "receipt.json"
            passed.parent.mkdir(parents=True)
            passed.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.visual_verification.v1",
                        "created_at": "2026-05-18T00:01:00+09:00",
                        "url": "http://127.0.0.1:8765/?mode=operator&visual_focus=contract-flow",
                        "status": "passed",
                        "screenshot_path": ".aios/screenshots/vis-focus.png",
                        "stop_conditions": [],
                    }
                ),
                encoding="utf-8",
            )
            promotion = root / ".aios" / "promotions" / "visual-fix-demo"
            promotion.mkdir(parents=True)
            (promotion / "contract_seed.md").write_text("# Seed\n", encoding="utf-8")
            (promotion / "promotion.json").write_text(
                json.dumps(
                    {
                        "schema_version": "aios.session_promotion.v1",
                        "promotion_id": "visual-fix-demo",
                        "status": "proposed_contract_seed",
                        "goal": "Fix visual receipt",
                        "created_at": "2026-05-18T00:02:00+09:00",
                        "source": {
                            "kind": "visual_verification_receipt",
                            "ref": ".aios/visual_verification/vis-source/receipt.json",
                            "status": "degraded",
                        },
                        "artifact_paths": {
                            "receipt": ".aios/promotions/visual-fix-demo/promotion.json",
                            "contract_seed": ".aios/promotions/visual-fix-demo/contract_seed.md",
                            "visual_receipt": ".aios/visual_verification/vis-source/receipt.json",
                        },
                        "execution_started": False,
                    }
                ),
                encoding="utf-8",
            )
            module = load_snapshot_module()

            promotions = module.load_promotions(root)

            self.assertEqual(promotions["next_contract_id"], "ASC-0002")
            self.assertEqual(promotions["items"][0]["quality_state"], "mitigated_by_visual_focus")
            self.assertEqual(promotions["items"][0]["quality_evidence"], ".aios/visual_verification/vis-focus/receipt.json")

    def test_snapshot_marks_active_gate_chair_runtime_demoted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            runtime = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            runtime.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "claude",
                        "model": "chair-test-model",
                        "updated_at": "2026-05-17T00:00:00+09:00",
                    }
                ),
                encoding="utf-8",
            )
            report = root / ".aios" / "evals" / "gate_chair" / "eval-demoted" / "report.json"
            report.parent.mkdir(parents=True)
            report.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-demoted",
                        "modes": [
                            {
                                "mode": "current",
                                "runs": [
                                    {
                                        "gate_chair_status": {
                                            "status": "gate_chair_timeout",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                    {
                                        "gate_chair_status": {
                                            "status": "provider_access_denied",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(root, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            chair = data["installation"]["gate_chair"]
            self.assertTrue(chair["demoted"])
            self.assertEqual(chair["configured_mode"], "claude")
            self.assertEqual(chair["effective_mode"], "internal_evidence_synthesizer")
            self.assertEqual(chair["demotion"]["failure_count"], 2)
            self.assertIn("eval-demoted/report.json", chair["demotion"]["failure_refs"][0])

    def test_snapshot_recovery_eval_clears_gate_chair_demotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_fixture(root)
            runtime = root / ".aios" / "gate" / "founder" / "chair_runtime.json"
            runtime.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate.chair_runtime.v1",
                        "status": "active",
                        "mode": "claude",
                        "model": "chair-test-model",
                        "updated_at": "2026-05-17T00:00:00+09:00",
                    }
                ),
                encoding="utf-8",
            )
            failure = root / ".aios" / "evals" / "gate_chair" / "eval-old-fail" / "report.json"
            failure.parent.mkdir(parents=True)
            failure.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-old-fail",
                        "promotion_ready": False,
                        "modes": [
                            {
                                "mode": "current",
                                "runs": [
                                    {
                                        "gate_chair_status": {
                                            "status": "gate_chair_timeout",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                    {
                                        "gate_chair_status": {
                                            "status": "provider_access_denied",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        }
                                    },
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            recovery = root / ".aios" / "evals" / "gate_chair" / "eval-new-recovery" / "report.json"
            recovery.parent.mkdir(parents=True)
            recovery.write_text(
                json.dumps(
                    {
                        "schema_version": "aios.gate_chair_eval.v1",
                        "eval_id": "eval-new-recovery",
                        "promotion_ready": True,
                        "scores": {"internal": 0.75, "current": 1.0},
                        "modes": [
                            {
                                "mode": "current",
                                "average_score": 1.0,
                                "runtime_modes": ["claude"],
                                "runtime_models": ["chair-test-model"],
                                "runs": [
                                    {
                                        "ok": True,
                                        "gate_chair_status": {
                                            "status": "success",
                                            "mode": "claude",
                                            "model": "chair-test-model",
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_cli(root, "--json")

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            chair = data["installation"]["gate_chair"]
            self.assertFalse(chair["demoted"])
            self.assertIsNone(chair["demotion"])
            self.assertEqual(chair["configured_mode"], "claude")
            self.assertEqual(chair["recovery_proof"]["recovery_ref"], ".aios/evals/gate_chair/eval-new-recovery/report.json")
            self.assertEqual(chair["recovery_proof"]["superseded_failure_count"], 2)

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

    def test_capability_route_preview_links_routes_fallbacks_and_evidence(self) -> None:
        module = load_snapshot_module()

        preview = module.build_capability_route_preview(
            [
                {
                    "id": "cap_primary",
                    "name": "Primary Route",
                    "score": 91,
                    "risk": "medium",
                    "privacy": "local",
                    "fallback_ids": ["cap_fallback"],
                    "evidence_refs": ["../docs/AIOS_CONTROL_APP.md"],
                }
            ],
            [
                {
                    "reason": "skipped_result",
                    "detail": "result status maps to skipped",
                    "evidence_ref": "../docs/AIOS_CONTROL_APP.md",
                }
            ],
            [{"agent": "codex", "passed": 3, "failed": 1}],
        )

        self.assertTrue(preview["nodes"])
        self.assertIn({"from": "cap_primary", "to": "cap_fallback", "kind": "fallback"}, preview["edges"])
        self.assertTrue(any(edge["kind"] == "evidence" for edge in preview["edges"]))
        self.assertTrue(any(node["type"] == "gap" for node in preview["nodes"]))
        self.assertTrue(any(node["type"] == "provider" and node["state"] == "attention" for node in preview["nodes"]))

    def test_genesis_worldline_preview_links_discomfort_branch_seed_and_source(self) -> None:
        module = load_snapshot_module()

        preview = module.build_genesis_worldline_preview(
            [
                {
                    "branch_id": "b1",
                    "type": "failure_as_feature",
                    "premise": "Treat hidden failure as interface signal.",
                    "what_it_breaks": "The UI hides provider failure.",
                    "contract_seed": "Expose failed provider fallback as a visual lane.",
                }
            ],
            ".aios/invocations/demo/genesis/branches.json",
        )

        node_types = {node["type"] for node in preview["nodes"]}
        edge_kinds = {edge["kind"] for edge in preview["edges"]}
        self.assertIn("discomfort", node_types)
        self.assertIn("branch", node_types)
        self.assertIn("seed", node_types)
        self.assertIn("source", node_types)
        self.assertIn("provokes", edge_kinds)
        self.assertIn("invents", edge_kinds)
        self.assertIn("evidence", edge_kinds)

    def test_check_app_js_reports_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = self.run_cli(root, "--check-app-js", "apps/control/app.js", "--json")

            self.assertNotEqual(result.returncode, 0)
            data = json.loads(result.stdout)
            self.assertFalse(data["ok"])
            self.assertIn("app js not found", data["errors"])


class RosterAndContractBoardTest(unittest.TestCase):
    """ASC-0204 — roster + contract-lifecycle board projections."""

    def test_contract_board_buckets_five_lifecycle_columns(self) -> None:
        module = load_snapshot_module()
        contract_rows = [
            {"id": "ASC-0001", "slug": "a", "status": "proposed", "goal": "g1", "path": "p1"},
            {"id": "ASC-0002", "slug": "b", "status": "accepted", "goal": "g2", "path": "p2"},
            {"id": "ASC-0003", "slug": "c", "status": "accepted", "goal": "g3", "path": "p3"},
            {"id": "ASC-0004", "slug": "d", "status": "accepted", "goal": "g4", "path": "p4"},
            {"id": "ASC-0005", "slug": "e", "status": "closed", "goal": "g5", "path": "p5"},
        ]
        dispatches = {"by_contract": {
            # ASC-0003: sent, not all collected -> dispatched
            "ASC-0003": {"sent": ["hivemind"], "collected": [], "statuses": ["sent"]},
            # ASC-0004: sent and fully collected -> collected
            "ASC-0004": {"sent": ["memoryOS"], "collected": ["memoryOS"], "statuses": ["collected"]},
        }}
        board = module.build_contract_board(contract_rows, dispatches)
        self.assertEqual(board["column_order"],
                         ["proposed", "accepted", "dispatched", "collected", "closed"])
        self.assertEqual(board["counts"],
                         {"proposed": 1, "accepted": 1, "dispatched": 1, "collected": 1, "closed": 1})
        # ASC-0002 has no dispatch record -> stays in accepted
        self.assertEqual(board["columns"]["accepted"][0]["contract_id"], "ASC-0002")
        self.assertEqual(board["columns"]["dispatched"][0]["contract_id"], "ASC-0003")
        self.assertEqual(board["columns"]["collected"][0]["contract_id"], "ASC-0004")

    def test_contract_board_renders_unknown_status_for_review(self) -> None:
        module = load_snapshot_module()
        rows = [{"id": "ASC-0009", "slug": "x", "status": "weird", "goal": "g", "path": "p"}]
        board = module.build_contract_board(rows, {"by_contract": {}})
        # untraceable status is surfaced for review, never dropped
        self.assertEqual(board["counts"]["proposed"], 1)
        self.assertEqual(board["columns"]["proposed"][0]["status"], "unknown")

    def test_roster_surfaces_six_agents_and_floats_blocked(self) -> None:
        module = load_snapshot_module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repos_state = {"items": [
                {"repo": "hivemind", "inbox_count": 1, "outbox_count": 4, "dirty": False},
                {"repo": "memoryOS", "inbox_count": 0, "outbox_count": 2, "dirty": False},
                {"repo": "CapabilityOS", "inbox_count": 0, "outbox_count": 0, "dirty": False},
            ]}
            # a failed dispatch to memoryOS marks codex@memoryOS blocked
            dispatches = {"latest": [
                {"sent": ["memoryOS"], "status": "failed"},
            ]}
            roster = module.build_roster(root, dispatches, repos_state)
        agents = roster["agents"]
        self.assertEqual(len(agents), 6)
        self.assertEqual({a["agent"] for a in agents}, {
            "claude@myworld", "codex@myworld", "codex@hivemind",
            "codex@memoryOS", "codex@CapabilityOS", "codex@GenesisOS",
        })
        # blocked agent floats to the top (out-of-band channel)
        self.assertEqual(agents[0]["agent"], "codex@memoryOS")
        self.assertEqual(agents[0]["event"], "blocked")
        self.assertEqual(roster["blocked_count"], 1)
        # an agent with inbox work reads as working
        hivemind = next(a for a in agents if a["agent"] == "codex@hivemind")
        self.assertEqual(hivemind["event"], "working")

    def test_roster_event_helper_is_deterministic(self) -> None:
        module = load_snapshot_module()
        self.assertEqual(module._roster_event(inbox_count=0, dirty=False, blocked=False, needs_input=False), "idle")
        self.assertEqual(module._roster_event(inbox_count=3, dirty=False, blocked=False, needs_input=False), "working")
        self.assertEqual(module._roster_event(inbox_count=0, dirty=True, blocked=False, needs_input=False), "working")
        self.assertEqual(module._roster_event(inbox_count=9, dirty=True, blocked=True, needs_input=False), "blocked")
        self.assertEqual(module._roster_event(inbox_count=0, dirty=False, blocked=False, needs_input=True), "needs_input")


if __name__ == "__main__":
    unittest.main()
