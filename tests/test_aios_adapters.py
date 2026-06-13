"""Provider adapter layer tests — no real CLI is ever invoked."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"


def _load(name: str):
    full = f"{name}_under_test"
    spec = importlib.util.spec_from_file_location(full, SCRIPTS / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[full] = m
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec.loader.exec_module(m)
    return m


class AdaptersTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_build_argv_substitutes_prompt_and_binary(self):
        # ollama uses positional-arg mode — prompt appears in argv
        spec = self.a.SPECS["ollama_local"]
        argv = spec.build_argv("hello world")
        self.assertIn("hello world", argv)

    def test_claude_spec_uses_stdin_mode(self):
        # claude uses stdin mode — prompt must NOT appear in argv (sent via stdin)
        spec = self.a.SPECS["claude"]
        self.assertTrue(spec.use_stdin)
        argv = spec.build_argv("hello world")
        self.assertNotIn("hello world", argv)
        self.assertEqual(argv, ["claude", "-p"])
        self.assertEqual(spec.get_stdin("hello world"), "hello world")

    def test_adapter_returns_stdout_on_success(self):
        calls = []

        def fake_runner(argv, stdin_text, timeout):
            calls.append((argv, stdin_text))
            return 0, "RESPONSE TEXT", ""

        adapter = self.a.make_adapter(self.a.SPECS["ollama_local"], runner=fake_runner)
        out = adapter("summarize this")
        self.assertEqual(out, "RESPONSE TEXT")
        self.assertEqual(calls[0][0][:3], ["ollama", "run", "qwen3:8b"])

    def test_claude_adapter_sends_prompt_via_stdin(self):
        calls = []

        def fake_runner(argv, stdin_text, timeout):
            calls.append((argv, stdin_text))
            return 0, '{"done":true}', ""

        adapter = self.a.make_adapter(self.a.SPECS["claude"], runner=fake_runner)
        out = adapter("my prompt")
        self.assertEqual(out, '{"done":true}')
        self.assertEqual(calls[0][0], ["claude", "-p"])   # no prompt in argv
        self.assertEqual(calls[0][1], "my prompt")        # prompt in stdin_text

    def test_adapter_raises_on_nonzero(self):
        def fake_runner(argv, stdin_text, timeout):
            return 1, "", "auth required"

        adapter = self.a.make_adapter(self.a.SPECS["gemini"], runner=fake_runner)
        with self.assertRaises(RuntimeError) as ctx:
            adapter("x")
        self.assertIn("auth required", str(ctx.exception))

    def test_build_adapters_filters_by_presence(self):
        # pretend only codex is installed; disable ollama_rest auto-registration
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: "/usr/bin/" + b if b == "codex" else None,
            rest_available=lambda: False,
        )
        self.assertEqual(set(reg), {"codex"})

    def test_build_adapters_require_present_false_builds_all(self):
        # require_present=False + rest disabled → exactly the SPECS keys
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: None,
            require_present=False,
            rest_available=lambda: False,
        )
        self.assertEqual(set(reg), set(self.a.SPECS))

    def test_build_adapters_includes_ollama_rest_when_available(self):
        reg = self.a.build_adapters(
            runner=lambda argv, s, t: (0, "ok", ""),
            which=lambda b: None,
            require_present=False,
            rest_available=lambda: True,
        )
        self.assertIn("ollama_rest", reg)

    def test_available_providers_uses_which(self):
        names = self.a.available_providers(which=lambda b: "/x/" + b if b in ("claude", "ollama") else None)
        self.assertIn("claude", names)
        self.assertIn("ollama_local", names)
        self.assertNotIn("gemini", names)

    def test_integration_runner_executes_provider_via_fake_adapter(self):
        """The runner should accept a built adapter registry and run a provider step."""
        runner_mod = _load("aios_contract_runner")
        co = runner_mod.co
        reg = self.a.build_adapters(
            providers=["ollama_local"],
            runner=lambda argv, s, t: (0, "LOCAL THOUGHT", ""),
            require_present=False,
        )
        c = co.ContractObject(contract_id="co-adapt", goal="think")
        c.provider_routes.append(co.ProviderRoute(provider="ollama_local", auth_mode="local", role="background"))
        c.steps.append(co.Step(id="t1", description="local cognition", tool="provider.ollama_local",
                               inputs={"prompt": "what is 2+2"}))
        summary = runner_mod.run_contract(c, adapters=reg)
        self.assertEqual(summary["status"], "closed", summary)
        self.assertTrue(c.receipts[0].success)


if __name__ == "__main__":
    unittest.main()
