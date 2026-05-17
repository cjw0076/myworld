import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "aios_child_watcher.sh"


def write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class AiosChildWatcherTest(unittest.TestCase):
    def make_root(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "scripts").mkdir()
        script = root / "scripts" / "aios_child_watcher.sh"
        shutil.copy2(SOURCE_SCRIPT, script)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        (root / "memoryOS").mkdir()
        (root / "GenesisOS").mkdir()
        (root / "CapabilityOS" / "capabilityos").mkdir(parents=True)
        (root / ".aios" / "inbox" / "memoryOS").mkdir(parents=True)
        (root / ".aios" / "outbox" / "memoryOS").mkdir(parents=True)
        (root / ".aios" / "inbox" / "GenesisOS").mkdir(parents=True)
        (root / ".aios" / "outbox" / "GenesisOS").mkdir(parents=True)
        return root

    def write_packet(self, root: Path, dispatch_id: str, agent: str = "codex") -> Path:
        packet = {
            "schema_version": "aios.dispatch.v1",
            "dispatch_id": dispatch_id,
            "contract_id": "ASC-0996",
            "contract_path": "docs/contracts/ASC-0996-test.md",
            "target_repo": "memoryOS",
            "agent": agent,
            "goal": "prove child watcher fallback behavior",
            "return_to": f".aios/outbox/memoryOS/{dispatch_id}.memoryOS.result.json",
            "scope": {"allowed_files": ["memoryOS/docs/AGENT_WORKLOG.md"], "forbidden_files": [".env"]},
        }
        path = root / ".aios" / "inbox" / "memoryOS" / f"{dispatch_id}.memoryOS.json"
        path.write_text(json.dumps(packet), encoding="utf-8")
        return path

    def init_child_git(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root / "memoryOS", text=True, capture_output=True, check=True)

    def run_watcher(self, root: Path, bin_dir: Path, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["CODEX_TIMEOUT"] = "10"
        env["CLAUDE_TIMEOUT"] = "10"
        env["GEMINI_TIMEOUT"] = "10"
        env["LOCAL_TIMEOUT"] = "10"
        env["AIOS_CHILD_AGENT_FALLBACKS"] = "1"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(root / "scripts" / "aios_child_watcher.sh"), "once", "--repo", "memoryOS"],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_watcher_for_repo(
        self,
        root: Path,
        bin_dir: Path,
        repo: str,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
        env["CODEX_TIMEOUT"] = "10"
        env["CLAUDE_TIMEOUT"] = "10"
        env["GEMINI_TIMEOUT"] = "10"
        env["LOCAL_TIMEOUT"] = "10"
        env["AIOS_CHILD_AGENT_FALLBACKS"] = "1"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(root / "scripts" / "aios_child_watcher.sh"), "once", "--repo", repo],
            cwd=root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_capabilityos_route_cli(self, root: Path, fallback_agent: str) -> Path:
        return self.write_capabilityos_route_cli_list(root, [fallback_agent])

    def write_capabilityos_route_cli_list(self, root: Path, fallback_agents: list[str]) -> Path:
        package = root / "CapabilityOS" / "capabilityos"
        (package / "__init__.py").write_text("", encoding="utf-8")
        marker = root / "capability-route-called"
        (package / "cli.py").write_text(
            "\n".join(
                [
                    "from __future__ import annotations",
                    "import json",
                    "from pathlib import Path",
                    f"Path({marker.as_posix()!r}).write_text('called', encoding='utf-8')",
                    "print(json.dumps({",
                    "  'contract': 'capabilityos.provider_route.v1',",
                    "  'recommendation_only': True,",
                    f"  'fallback_agents': {fallback_agents!r},",
                    "  'routes': [],",
                    "}))",
                ]
            ),
            encoding="utf-8",
        )
        return marker

    def test_provider_access_denied_falls_back_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            marker = self.write_capabilityos_route_cli(root, "claude")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'provider access denied: account lacks this model' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'fallback agent completed bounded turn'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0996")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0996.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["final_agent"], "claude")
            self.assertEqual(data["failure_category"], "provider_access_denied")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude"])
            self.assertEqual(data["agent_attempts"][0]["failure_category"], "provider_access_denied")
            self.assertEqual(data["agent_attempts"][1]["failure_category"], "none")
            self.assertFalse(data["stop_conditions_triggered"])
            self.assertTrue(marker.exists())
            self.assertTrue((root / ".aios" / "logs" / "asc-0996.memoryOS.fallback-1.provider_route.json").exists())

    def test_provider_access_denied_can_fallback_to_gemini(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli(root, "gemini")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'provider access denied: account lacks this model' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "gemini",
                "#!/usr/bin/env bash\n"
                "echo 'gemini fallback completed bounded turn'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0991")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0991.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["final_agent"], "gemini")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "gemini"])

    def test_provider_access_denied_can_fallback_to_local_but_holds_for_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli(root, "local")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'provider access denied: account lacks this model' >&2\n"
                "exit 1\n",
            )
            self.write_packet(root, "asc-0990")

            result = self.run_watcher(
                root,
                bin_dir,
                {
                    "AIOS_LOCAL_AGENT_COMMAND": "echo local fallback drafted bounded route",
                    "AIOS_CHILD_PREFER_PROVIDER_BEFORE_LOCAL": "0",
                },
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0990.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "held")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["final_agent"], "local")
            self.assertTrue(data["local_final_without_verifier"])
            self.assertEqual(data["failure_category"], "local_llm_used_as_final_acceptor_without_verifier")

    def test_local_route_is_demoted_when_provider_fallback_command_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli(root, "local")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'provider backpressure: quota exhausted' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'claude completed before local fallback'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0986")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0986.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["final_agent"], "claude")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude"])

    def test_unknown_child_failure_does_not_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "fallback-called"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'ordinary implementation failure' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0995")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse(marker.exists())
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0995.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertFalse(data["fallback_used"])
            self.assertEqual(data["final_agent"], "codex")
            self.assertEqual(data["failure_category"], "child_agent_failed")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex"])
            self.assertEqual(data["stop_conditions_triggered"], ["child_agent_failed"])

    def test_korean_access_denied_falls_back_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli(root, "claude")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo 'fallback agent completed bounded turn'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0994")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0994.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["failure_category"], "provider_access_denied")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude"])

    def test_pin_auth_failure_continues_to_next_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli_list(root, ["claude", "gemini", "local"])
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo '틀렸습니다. (1/3)' >&2\n"
                "echo '틀렸습니다. (2/3)' >&2\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "gemini",
                "#!/usr/bin/env bash\n"
                "echo 'gemini completed after pin-gated providers failed'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0989")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0989.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertTrue(data["fallback_used"])
            self.assertEqual(data["final_agent"], "gemini")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude", "gemini"])
            self.assertEqual(data["agent_attempts"][1]["failure_category"], "pin_required_noninteractive")

    def test_provider_backpressure_continues_to_next_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli_list(root, ["claude", "gemini", "local"])
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo \"You've hit your limit · resets 3pm\" >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "gemini",
                "#!/usr/bin/env bash\n"
                "echo 'gemini completed after rate-limited provider failed'\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0988")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0988.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["final_agent"], "gemini")
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude", "gemini"])
            self.assertEqual(data["agent_attempts"][1]["failure_category"], "provider_backpressure")

    def test_gemini_missing_auth_continues_to_local_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.write_capabilityos_route_cli_list(root, ["claude", "gemini", "local"])
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo '접근 거부.' >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "claude",
                "#!/usr/bin/env bash\n"
                "echo \"You've hit your limit · resets 3pm\" >&2\n"
                "exit 1\n",
            )
            write_executable(
                bin_dir / "gemini",
                "#!/usr/bin/env bash\n"
                "echo 'Please set an Auth method in your /home/user/.gemini/settings.json or specify GEMINI_API_KEY' >&2\n"
                "exit 41\n",
            )
            self.write_packet(root, "asc-0987")

            result = self.run_watcher(
                root,
                bin_dir,
                {"AIOS_LOCAL_AGENT_COMMAND": "echo local route drafted after provider auth chain failed"},
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0987.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "held")
            self.assertEqual(data["final_agent"], "local")
            self.assertTrue(data["local_final_without_verifier"])
            self.assertEqual([item["agent"] for item in data["agent_attempts"]], ["codex", "claude", "gemini", "local"])
            self.assertEqual(data["agent_attempts"][2]["failure_category"], "provider_access_denied")

    def test_existing_related_dirty_work_holds_without_spawning_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.init_child_git(root)
            worklog = root / "memoryOS" / "docs" / "AGENT_WORKLOG.md"
            worklog.parent.mkdir(parents=True)
            worklog.write_text("parallel work\n", encoding="utf-8")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "codex-called"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "exit 0\n",
            )
            self.write_packet(root, "asc-0993")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse(marker.exists())
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0993.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "held")
            self.assertTrue(data["pending_concurrent_work"])
            self.assertIn("pending_concurrent_work", data["stop_conditions_triggered"])

    def test_memory_draft_review_request_writes_result_without_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            package = root / "memoryOS" / "memoryos"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "cli.py").write_text(
                "\n".join(
                    [
                        "from __future__ import annotations",
                        "import json",
                        "import sys",
                        "from pathlib import Path",
                        f"Path({(root / 'memoryos-import-called').as_posix()!r}).write_text('called', encoding='utf-8')",
                        "print(json.dumps({",
                        "  'schema_version': 'aios.memory_draft_review_import.v1',",
                        "  'request_id': 'mdrev-test',",
                        "  'draft_id': 'demo:0',",
                        "  'memory_object_id': 'mem_test',",
                        "  'source_artifact_id': 'src_test',",
                        "  'review_id': 'review_test',",
                        "  'memory_status': 'draft',",
                        "  'review_action': 'needs_more_evidence',",
                        "  'auto_accept': False,",
                        "  'imported_counts': {'source_artifacts': 1, 'memory_objects': 1, 'hyperedges': 1, 'reviews': 1},",
                        "  'skipped_counts': {'source_artifacts': 0, 'memory_objects': 0, 'hyperedges': 0, 'reviews': 0},",
                        "}))",
                    ]
                ),
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            marker = root / "codex-called"
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                f"touch {marker.as_posix()}\n"
                "exit 0\n",
            )
            packet = {
                "schema_version": "aios.memory_draft_review_request.v1",
                "result_schema_version": "aios.dispatch.result.v1",
                "request_id": "mdrev-test",
                "dispatch_id": "mdrev-test",
                "contract_id": "MEMORY-DRAFT-REVIEW",
                "contract_path": "docs/AIOS_CHAT.md",
                "target_repo": "memoryOS",
                "agent": "memoryOS-reviewer",
                "goal": "Review one AIOS chat memory draft candidate.",
                "source_artifact": ".aios/chat/demo/memory_drafts.json",
                "draft_id": "demo:0",
                "return_to": ".aios/outbox/memoryOS/mdrev-test.memoryOS.result.json",
                "review_policy": {"auto_accept": False, "draft_first": True},
                "draft": {
                    "type": "genesis_friction_signal",
                    "origin": "aios_chat_genesis",
                    "status": "draft",
                    "confidence": 0.67,
                    "content": "reviewable draft",
                    "raw_refs": ["messages.jsonl"],
                    "provenance": {"source": "aios_chat"},
                },
                "scope": {"allowed_files": [], "forbidden_files": [".env"]},
            }
            packet_path = root / ".aios" / "inbox" / "memoryOS" / "mdrev-test.memoryOS.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertFalse(marker.exists())
            result_path = root / ".aios" / "outbox" / "memoryOS" / "mdrev-test.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema_version"], "aios.dispatch.result.v1")
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["agent_executed"], "aios_child_watcher.memory_draft_review_adapter")
            self.assertEqual(data["review_request"]["review_decision"], "needs_more_evidence")
            self.assertTrue(data["review_request"]["memory_mutated"])
            self.assertEqual(data["review_request"]["memory_object_id"], "mem_test")
            self.assertEqual(data["review_request"]["source_artifact_id"], "src_test")
            self.assertEqual(data["review_request"]["review_id"], "review_test")
            self.assertTrue((root / "memoryos-import-called").exists())
            self.assertTrue(Path(data["review_request"]["import_result_ref"]).exists())
            self.assertFalse(data["stop_conditions_triggered"])

    def test_memory_draft_review_request_without_dispatch_id_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            package = root / "memoryOS" / "memoryos"
            package.mkdir()
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "cli.py").write_text(
                "raise SystemExit('should not import legacy packet without dispatch_id')\n",
                encoding="utf-8",
            )
            bin_dir = root / "bin"
            bin_dir.mkdir()
            packet = {
                "schema_version": "aios.memory_draft_review_request.v1",
                "request_id": "mdrev-legacy",
                "target_repo": "memoryOS",
                "agent": "memoryOS-reviewer",
                "source_artifact": ".aios/chat/demo/memory_drafts.json",
                "draft_id": "demo:0",
                "return_to": ".aios/outbox/memoryOS/mdrev-legacy.memoryOS.result.json",
                "review_policy": {"auto_accept": False, "draft_first": True},
                "draft": {
                    "type": "genesis_friction_signal",
                    "origin": "aios_chat_genesis",
                    "status": "draft",
                    "confidence": 0.67,
                    "content": "reviewable draft",
                    "raw_refs": ["messages.jsonl"],
                    "provenance": {"source": "aios_chat"},
                },
                "scope": {"allowed_files": [], "forbidden_files": [".env"]},
            }
            packet_path = root / ".aios" / "inbox" / "memoryOS" / "mdrev-legacy.memoryOS.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            data = json.loads((root / ".aios" / "outbox" / "memoryOS" / "mdrev-legacy.memoryOS.result.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "held")
            self.assertEqual(data["failure_category"], "memory_draft_review_request_incomplete")
            self.assertIn("dispatch_id_missing", data["stop_conditions_triggered"])
            self.assertFalse(data["review_request"]["memory_mutated"])

    def test_failed_agent_that_leaves_dirty_work_flags_orphan_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            self.init_child_git(root)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "mkdir -p docs\n"
                "echo orphan > docs/AGENT_WORKLOG.md\n"
                "echo failed after writing >&2\n"
                "exit 1\n",
            )
            self.write_packet(root, "asc-0992")

            result = self.run_watcher(root, bin_dir)

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "memoryOS" / "asc-0992.memoryOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertTrue(data["orphan_work_detected"])
            self.assertIn("orphan_work_detected", data["stop_conditions_triggered"])
            self.assertTrue(any("docs/AGENT_WORKLOG.md" in item for item in data["orphan_work_files"]))

    def test_genesisos_packet_runs_through_child_watcher(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            write_executable(
                bin_dir / "codex",
                "#!/usr/bin/env bash\n"
                "echo 'genesis bounded turn complete'\n"
                "exit 0\n",
            )
            packet = {
                "schema_version": "aios.dispatch.v1",
                "dispatch_id": "asc-0986",
                "contract_id": "ASC-0986",
                "contract_path": "docs/contracts/ASC-0986-test.md",
                "target_repo": "GenesisOS",
                "agent": "codex",
                "goal": "prove GenesisOS child watcher support",
                "return_to": ".aios/outbox/GenesisOS/asc-0986.GenesisOS.result.json",
                "scope": {
                    "allowed_files": ["GenesisOS/genesisos/critic.py"],
                    "forbidden_files": [".env"],
                },
            }
            packet_path = root / ".aios" / "inbox" / "GenesisOS" / "asc-0986.GenesisOS.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")

            result = self.run_watcher_for_repo(root, bin_dir, "GenesisOS")

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            result_path = root / ".aios" / "outbox" / "GenesisOS" / "asc-0986.GenesisOS.result.json"
            data = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["target_repo"], "GenesisOS")
            self.assertEqual(data["final_agent"], "codex")

    def test_status_lists_genesisos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make_root(tmp)
            bin_dir = root / "bin"
            bin_dir.mkdir()

            result = self.run_watcher_for_repo(root, bin_dir, "GenesisOS")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

            status = subprocess.run(
                [str(root / "scripts" / "aios_child_watcher.sh"), "status"],
                cwd=root,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("GenesisOS running=false", status.stdout)


if __name__ == "__main__":
    unittest.main()
