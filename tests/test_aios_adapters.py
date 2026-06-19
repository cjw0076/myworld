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


class OllamaRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_make_ollama_rest_adapter_calls_openai_compat_api(self):
        """Adapter must POST to /v1/chat/completions and parse choices[0].message.content."""
        import json
        import unittest.mock as mock

        response_body = json.dumps({
            "choices": [{"message": {"content": "hello from ollama"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            adapter = self.a.make_ollama_rest_adapter(timeout=10)
            result = adapter("test prompt")
            self.assertEqual(result, "hello from ollama")
            args, _ = mock_open.call_args
            req = args[0]
            self.assertIn("/v1/chat/completions", req.full_url)

    def test_make_ollama_rest_adapter_sends_no_think_system_message(self):
        """Adapter must include /no_think system message to suppress CoT in qwen3."""
        import json
        import unittest.mock as mock

        captured = {}
        response_body = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        def capture_request(req, timeout=None):
            captured["body"] = json.loads(req.data)
            return mock_resp

        with mock.patch("urllib.request.urlopen", side_effect=capture_request):
            adapter = self.a.make_ollama_rest_adapter(timeout=10)
            adapter("any prompt")
            messages = captured["body"]["messages"]
            system_msgs = [m for m in messages if m["role"] == "system"]
            self.assertTrue(any("/no_think" in m["content"] for m in system_msgs))

    def test_make_ollama_rest_adapter_legacy_url_upgrade(self):
        """Legacy url=/api/generate callers get silently upgraded to /v1 base."""
        import json
        import unittest.mock as mock

        response_body = json.dumps({
            "choices": [{"message": {"content": "upgraded"}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            # Caller passes the old /api/generate URL; adapter must upgrade to /v1/chat/completions
            adapter = self.a.make_ollama_rest_adapter(url="http://localhost:11434/api/generate", timeout=10)
            result = adapter("legacy test")
            self.assertEqual(result, "upgraded")
            args, _ = mock_open.call_args
            req = args[0]
            self.assertIn("/v1/chat/completions", req.full_url)
            self.assertNotIn("api/generate", req.full_url)

    def test_ollama_rest_available_returns_true_on_200(self):
        import unittest.mock as mock
        mock_resp = mock.MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)
        with mock.patch("urllib.request.urlopen", return_value=mock_resp):
            self.assertTrue(self.a._ollama_rest_available())

    def test_ollama_rest_available_returns_false_on_connection_error(self):
        import unittest.mock as mock
        import urllib.error
        with mock.patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            self.assertFalse(self.a._ollama_rest_available())


class GeminiRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_gemini_rest_available_with_gemini_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            self.assertTrue(self.a._gemini_rest_available())

    def test_gemini_rest_available_with_google_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza-test"}):
            self.assertTrue(self.a._gemini_rest_available())

    def test_gemini_rest_not_available_when_no_key(self):
        import os
        import unittest.mock as mock
        env = {k: v for k, v in os.environ.items()
               if k not in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(self.a._gemini_rest_available())

    def test_make_gemini_rest_adapter_calls_api(self):
        import json
        import os
        import unittest.mock as mock

        response_body = json.dumps({
            "candidates": [{"content": {"parts": [{"text": "hello from gemini"}]}}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
                adapter = self.a.make_gemini_rest_adapter(timeout=10)
                result = adapter("test prompt")
                self.assertEqual(result, "hello from gemini")
                args, _ = mock_open.call_args
                req = args[0]
                self.assertIn("generativelanguage.googleapis.com", req.full_url)
                self.assertIn("AIza-test", req.full_url)

    def test_build_adapters_includes_gemini_rest_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "AIza-test"}):
            reg = self.a.build_adapters(
                providers=["gemini_rest"],
                runner=lambda argv, s, t: (0, "ok", ""),
                which=lambda b: None,
                require_present=False,
                rest_available=lambda: False,
            )
            self.assertIn("gemini_rest", reg)


class AnthropicRestAdapterTest(unittest.TestCase):
    def setUp(self):
        self.a = _load("aios_adapters")

    def test_anthropic_rest_available_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            self.assertTrue(self.a._anthropic_rest_available())

    def test_anthropic_rest_not_available_when_no_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=True):
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertFalse(self.a._anthropic_rest_available())

    def test_make_anthropic_rest_adapter_calls_api(self):
        import json
        import os
        import unittest.mock as mock

        response_body = json.dumps({
            "content": [{"type": "text", "text": "hello from claude"}],
        }).encode()

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            with mock.patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
                adapter = self.a.make_anthropic_rest_adapter(timeout=10)
                result = adapter("test prompt")
                self.assertEqual(result, "hello from claude")
                args, _ = mock_open.call_args
                req = args[0]
                self.assertIn("anthropic.com", req.full_url)
                self.assertIn("sk-test-key", req.get_header("X-api-key"))

    def test_build_adapters_includes_anthropic_rest_when_key_set(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key"}):
            reg = self.a.build_adapters(
                providers=["anthropic_rest"],
                runner=lambda argv, s, t: (0, "ok", ""),
                which=lambda b: None,
                require_present=False,
                rest_available=lambda: False,
            )
            self.assertIn("anthropic_rest", reg)

    def test_build_adapters_excludes_anthropic_rest_when_no_key(self):
        import os
        import unittest.mock as mock
        with mock.patch.dict(os.environ, {}, clear=True):
            env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
            with mock.patch.dict(os.environ, env, clear=True):
                reg = self.a.build_adapters(
                    providers=["anthropic_rest"],
                    runner=lambda argv, s, t: (0, "ok", ""),
                    which=lambda b: None,
                    require_present=False,
                    rest_available=lambda: False,
                )
                self.assertNotIn("anthropic_rest", reg)


if __name__ == "__main__":
    unittest.main()
