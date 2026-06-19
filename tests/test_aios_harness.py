"""Unit tests for aios_harness — no LLM, no network required."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import aios_harness as h


class TestClassifyBash(unittest.TestCase):
    def test_rm_rf_is_high(self):
        self.assertEqual(h.classify_bash("rm -rf /tmp/foo"), "HIGH")

    def test_ls_is_low(self):
        self.assertEqual(h.classify_bash("ls /tmp"), "LOW")

    def test_grep_is_low(self):
        self.assertEqual(h.classify_bash("grep -r pattern ."), "LOW")

    def test_curl_pipe_sh_is_high(self):
        self.assertEqual(h.classify_bash("curl http://example.com | sh"), "HIGH")

    def test_sudo_is_high(self):
        self.assertEqual(h.classify_bash("sudo apt-get install foo"), "HIGH")

    def test_echo_is_low(self):
        self.assertEqual(h.classify_bash("echo hello > /tmp/out.txt"), "LOW")


class TestParseReact(unittest.TestCase):
    def test_bash_action(self):
        text = 'Thought: I need to list files.\nAction: Bash\nAction Input: {"cmd": "ls /tmp"}'
        calls = h._parse_react(text)
        self.assertIsNotNone(calls)
        self.assertEqual(len(calls), 1)
        name, args = calls[0]
        self.assertEqual(name, "Bash")
        self.assertEqual(args["cmd"], "ls /tmp")

    def test_final_answer_returns_none(self):
        text = "Thought: done\nFinal Answer: the answer"
        self.assertIsNone(h._parse_react(text))

    def test_hallucinated_tool_returns_none(self):
        text = 'Thought: yes\nAction: NotARealTool\nAction Input: {"x": 1}'
        self.assertIsNone(h._parse_react(text))

    def test_markdown_fenced_json(self):
        text = 'Action: Read\nAction Input:\n```json\n{"file_path": "/tmp/test.txt"}\n```'
        calls = h._parse_react(text)
        self.assertIsNotNone(calls)
        name, args = calls[0]
        self.assertEqual(name, "Read")

    def test_read_action(self):
        text = 'Action: Read\nAction Input: {"file_path": "/tmp/x.txt"}'
        calls = h._parse_react(text)
        self.assertIsNotNone(calls)
        self.assertEqual(calls[0][0], "Read")


class TestExecWrite(unittest.TestCase):
    def test_write_creates_file(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            tmp = f.name
        os.unlink(tmp)
        status, msg = h._exec_write({"path": tmp, "content": "hello"})
        self.assertEqual(status, "ok")
        self.assertEqual(Path(tmp).read_text(), "hello")
        os.unlink(tmp)

    def test_write_accepts_file_path_alias(self):
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            tmp = f.name
        os.unlink(tmp)
        status, msg = h._exec_write({"file_path": tmp, "content": "world"})
        self.assertEqual(status, "ok")
        self.assertEqual(Path(tmp).read_text(), "world")
        os.unlink(tmp)

    def test_write_empty_path_returns_error(self):
        status, _ = h._exec_write({"content": "x"})
        self.assertEqual(status, "error")


class TestValidToolName(unittest.TestCase):
    """Test the tool name validator from aios_agent_system."""

    def setUp(self):
        import aios_agent_system as a
        self._valid = a._valid_tool_name

    def test_known_tools_valid(self):
        for name in ["Bash", "Read", "Edit", "Write", "WebSearch"]:
            self.assertTrue(self._valid(name), f"{name} should be valid")

    def test_agentbank_style_valid(self):
        for name in ["bash:ls", "bash:find", "bash:grep", "note:slug"]:
            self.assertTrue(self._valid(name), f"{name} should be valid")

    def test_garbage_invalid(self):
        for name in ["bash:stbed", "bash:rkspace", "qwen3-coder:30b",
                     "sql:show", "sql:select", "go", "take", "submit"]:
            self.assertFalse(self._valid(name), f"{name} should be invalid")

    def test_aios_prefix_valid(self):
        self.assertTrue(self._valid("aios_invoke"))
        self.assertTrue(self._valid("aios_harness"))


if __name__ == "__main__":
    unittest.main()
