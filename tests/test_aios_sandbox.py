"""Adversarial tests for the AIOS execution sandbox.

These are NOT mock tests. Where the kernel permits real isolation
(sandbox_self_test().isolated), the escape tests ACTUALLY attempt to write
outside the workspace / reach the network and assert the kernel blocked it.
Where it does not (restricted CI/nested containers that block unprivileged user
namespaces), those tests skip with the concrete reason — never a silent pass —
and the fail-closed + policy-encoding tests still run everywhere.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_sandbox as sb

_SELFTEST = sb.sandbox_self_test()
_ISOLATED = _SELFTEST.get("isolated", False)
_SKIP_REASON = f"kernel isolation unavailable here: {_SELFTEST.get('reason')}"


class PolicyEncodingTests(unittest.TestCase):
    """The security policy must be correctly encoded in the bwrap command even
    on hosts where it cannot be executed — this is what makes it real on hosts
    where it CAN."""

    def setUp(self) -> None:
        self.ws = Path(tempfile.mkdtemp(prefix="aios_pol_"))

    def test_network_unshared_by_default(self) -> None:
        argv = sb.build_bwrap_argv(["sh"], workspace=self.ws, allow_network=False)
        self.assertIn("--unshare-net", argv)

    def test_network_kept_when_explicitly_allowed(self) -> None:
        argv = sb.build_bwrap_argv(["sh"], workspace=self.ws, allow_network=True)
        self.assertNotIn("--unshare-net", argv)

    def test_root_is_readonly_and_workspace_bound_after(self) -> None:
        argv = sb.build_bwrap_argv(["sh"], workspace=self.ws, allow_network=False)
        # whole FS read-only...
        self.assertIn("--ro-bind", argv)
        # ...and the workspace rw bind must come AFTER the ro-bind / (later wins)
        ro_idx = argv.index("--ro-bind")
        bind_idx = max(i for i, t in enumerate(argv) if t == "--bind")
        self.assertGreater(bind_idx, ro_idx)
        self.assertIn(str(self.ws.resolve()), argv)

    def test_private_tmp_and_namespaces(self) -> None:
        argv = sb.build_bwrap_argv(["sh"], workspace=self.ws, allow_network=False)
        for flag in ("--tmpfs", "--unshare-pid", "--unshare-ipc", "--die-with-parent"):
            self.assertIn(flag, argv)


class FailClosedTests(unittest.TestCase):
    """The single most important property: NEVER run unsandboxed silently."""

    def test_missing_bwrap_refuses(self) -> None:
        ws = tempfile.mkdtemp(prefix="aios_fc_")
        with self.assertRaises(sb.SandboxUnavailable):
            sb.run_sandboxed(["sh", "-c", "echo should-not-run"], workspace=ws,
                             which=lambda _b: None)  # bwrap "absent"

    def test_bogus_bwrap_path_refuses(self) -> None:
        ws = tempfile.mkdtemp(prefix="aios_fc_")
        with self.assertRaises(sb.SandboxUnavailable):
            sb.run_sandboxed(["sh", "-c", "echo x"], workspace=ws,
                             bwrap_bin="/nonexistent/bwrap")

    def test_nonexistent_workspace_refuses(self) -> None:
        with self.assertRaises(sb.SandboxUnavailable):
            sb.run_sandboxed(["sh", "-c", "echo x"], workspace="/no/such/ws/here")


@unittest.skipUnless(_ISOLATED, _SKIP_REASON)
class AdversarialEscapeTests(unittest.TestCase):
    """Run ONLY where real isolation works — and then actually try to escape."""

    def setUp(self) -> None:
        self.ws = tempfile.mkdtemp(prefix="aios_adv_")
        fd, self.outside = tempfile.mkstemp(prefix="aios_outside_", suffix=".txt")
        os.write(fd, b"SAFE")
        os.close(fd)

    def tearDown(self) -> None:
        if os.path.exists(self.outside):
            os.unlink(self.outside)

    def test_cannot_overwrite_host_file_outside_workspace(self) -> None:
        sb.run_sandboxed(["sh", "-c", f"echo HACKED > {self.outside} 2>/dev/null || true"],
                         workspace=self.ws)
        self.assertEqual(Path(self.outside).read_text(), "SAFE")  # host file untouched

    def test_cannot_write_to_etc(self) -> None:
        code, _o, _e = sb.run_sandboxed(
            ["sh", "-c", "echo x > /etc/aios_escape && echo WROTE || echo blocked"],
            workspace=self.ws)
        self.assertFalse(Path("/etc/aios_escape").exists())

    def test_network_egress_denied_by_default(self) -> None:
        code, _o, _e = sb.run_sandboxed(
            ["python3", "-c",
             "import socket; socket.setdefaulttimeout(4);"
             "socket.create_connection(('1.1.1.1',53)); print('REACHED')"],
            workspace=self.ws, allow_network=False)
        self.assertNotEqual(code, 0)  # connection must fail in the empty net ns

    def test_legit_write_inside_workspace_succeeds(self) -> None:
        code, out, _e = sb.run_sandboxed(["sh", "-c", "echo ok > f.txt && cat f.txt"],
                                         workspace=self.ws)
        self.assertEqual(code, 0)
        self.assertEqual((Path(self.ws) / "f.txt").read_text().strip(), "ok")


if __name__ == "__main__":
    print(f"sandbox self-test: {_SELFTEST}", file=sys.stderr)
    unittest.main()
