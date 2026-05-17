import json
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())

import aios_ingest_server as ingest  # noqa: E402


def _free_port() -> int:
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


SAMPLE_PACKET = {
    "schema": "aios.product_recap.v1",
    "product_repo": "uri",
    "sprint_id": "URI-999",
    "sprint_subject": "ingest protocol test packet",
    "capabilities_used": ["nextjs"],
    "operator_signed_by": "test",
    "consent": "I authorize AIOS to ingest this packet as a MemoryOS draft and CapabilityOS observation.",
    "evidence_refs": ["test://evidence"],
}


class AiosIngestProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / ".aios" / "inbox" / "myworld").mkdir(parents=True)
        # ASC-0181: a repo must be registered in the workbench registry to
        # be emit-eligible. Register the test repo so packets route.
        import aios_workbench_registry as registry

        registry.register_repo(self.root, "uri", note="ingest protocol test")
        self.port = _free_port()
        ingest.IngestHandler.root = self.root
        from http.server import ThreadingHTTPServer

        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), ingest.IngestHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.05)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def _post(self, body: dict) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/aios/ingest", json.dumps(body), {"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode("utf-8"))
        code = resp.status
        conn.close()
        return code, data

    def test_bind_is_loopback_only(self) -> None:
        self.assertEqual(self.httpd.server_address[0], "127.0.0.1")

    def test_health_endpoint(self) -> None:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/aios/health", timeout=5) as r:
            payload = json.loads(r.read().decode("utf-8"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["bind"], "127.0.0.1")

    def test_packet_lands_in_inbox(self) -> None:
        code, data = self._post(SAMPLE_PACKET)
        self.assertEqual(code, 200)
        self.assertTrue(data["accepted"])
        dest = self.root / ".aios" / "inbox" / "myworld" / "product_recap__uri__URI-999.json"
        self.assertTrue(dest.exists())
        stored = json.loads(dest.read_text(encoding="utf-8"))
        self.assertEqual(stored["sprint_id"], "URI-999")

    def test_idempotent_redelivery(self) -> None:
        code1, data1 = self._post(SAMPLE_PACKET)
        code2, data2 = self._post(SAMPLE_PACKET)
        self.assertEqual(code1, 200)
        self.assertEqual(code2, 200)
        self.assertEqual(data1["receipt_id"], data2["receipt_id"])
        self.assertIn("idempotent", data2["reason"])

    def test_forbidden_marker_rejected(self) -> None:
        bad = dict(SAMPLE_PACKET, sprint_id="URI-998", operator_signed_by="leak sk-ABCDEFGH12345678")
        code, data = self._post(bad)
        self.assertEqual(code, 422)
        self.assertFalse(data["accepted"])
        self.assertIn("forbidden_marker", data["reason"])

    def test_unroutable_packet_rejected(self) -> None:
        code, data = self._post({"schema": "aios.unknown.v1", "foo": "bar"})
        self.assertEqual(code, 422)
        self.assertFalse(data["accepted"])

    def test_unregistered_repo_rejected(self) -> None:
        # ASC-0181: a repo not in the workbench registry is unroutable.
        unregistered = dict(SAMPLE_PACKET, product_repo="notregistered", sprint_id="NR-001")
        code, data = self._post(unregistered)
        self.assertEqual(code, 422)
        self.assertFalse(data["accepted"])

    def test_invalid_json_rejected(self) -> None:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/aios/ingest", "{not json", {"Content-Type": "application/json"})
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        conn.close()

    def test_non_loopback_host_refused(self) -> None:
        rc = ingest.main(["--host", "0.0.0.0", "--port", str(_free_port())])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
