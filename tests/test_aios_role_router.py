"""Tests for aios_role_router — OMX role-router pattern absorbed into AIOS."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import aios_role_router as rr


class RouteTests(unittest.TestCase):

    def _route(self, task: str) -> rr.RouteResult:
        return rr.route(task)

    # -- build/debug lane --
    def test_build_error_routes_to_debugger(self):
        r = self._route("Fix the TypeScript build error in the CI pipeline")
        self.assertEqual(r.role, "debugger")
        self.assertEqual(r.confidence, "high")

    def test_debug_routes_to_debugger(self):
        r = self._route("Investigate the root cause of the memory leak")
        self.assertEqual(r.role, "debugger")
        self.assertEqual(r.provider, "codex")

    # -- test lane --
    def test_write_tests_routes_to_test_engineer(self):
        r = self._route("Write tests for the auth module")
        self.assertEqual(r.role, "test-engineer")
        self.assertEqual(r.confidence, "high")

    def test_increase_coverage_routes_to_test_engineer(self):
        r = self._route("Increase test coverage for the API layer")
        self.assertEqual(r.role, "test-engineer")

    # -- docs lane --
    def test_write_readme_routes_to_writer(self):
        r = self._route("Write README documentation for the new CLI")
        self.assertEqual(r.role, "writer")
        self.assertEqual(r.provider, "claude")

    # -- review lane --
    def test_security_review_routes_to_code_reviewer(self):
        r = self._route("Review the authentication module for security vulnerabilities")
        self.assertEqual(r.role, "code-reviewer")

    def test_quality_review_routes_to_quality_reviewer(self):
        r = self._route("Audit the codebase for anti-patterns")
        self.assertEqual(r.role, "quality-reviewer")

    # -- explore lane --
    def test_find_files_routes_to_explore(self):
        r = self._route("Find all files that reference the auth module")
        self.assertEqual(r.role, "explore")
        self.assertEqual(r.agent_type, "Explore")

    # -- cleanup lane --
    def test_refactor_routes_to_code_simplifier(self):
        r = self._route("Refactor the legacy dispatch module to simplify it")
        self.assertEqual(r.role, "code-simplifier")

    # -- design lane --
    def test_ui_design_routes_to_designer(self):
        r = self._route("Design the layout for the new dashboard component")
        self.assertEqual(r.role, "designer")

    # -- Korean text --
    def test_korean_debug(self):
        r = self._route("메모리 누수 원인 조사")
        self.assertEqual(r.role, "debugger")

    def test_korean_test(self):
        r = self._route("테스트 커버리지 추가")
        self.assertEqual(r.role, "test-engineer")

    # -- default implementation fallback --
    def test_implement_returns_executor(self):
        r = self._route("Implement the new feature X")
        self.assertEqual(r.role, "executor")
        self.assertEqual(r.confidence, "low")

    # -- schema --
    def test_result_has_schema_version(self):
        r = self._route("anything")
        d = r.as_dict()
        self.assertEqual(d["schema_version"], "aios.role_router.v1")
        for key in ("role", "provider", "agent_type", "confidence", "reason"):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
