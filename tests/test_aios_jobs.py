"""Tests for the leased jobs queue (ASC-0185) — proves the named-exit behaviors."""

import importlib.util
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "aios_jobs", Path(__file__).resolve().parent.parent / "scripts" / "aios_jobs.py")
jobs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jobs)


def test_enqueue_and_status(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-1", contract_id="ASC-9001")
    st = jobs.status(tmp_path)
    assert st["counts"]["queued"] == 1


def test_duplicate_job_key_is_noop(tmp_path):
    a = jobs.enqueue(tmp_path, "dispatch", "key-dup")
    b = jobs.enqueue(tmp_path, "dispatch", "key-dup")
    assert a["status"] == "enqueued"
    assert b["status"] == "duplicate"
    assert b["job_id"] == a["job_id"]
    assert jobs.status(tmp_path)["counts"]["queued"] == 1


def test_claim_then_double_claim_rejected(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-2")
    first = jobs.claim(tmp_path, worker="worker-A")
    assert first["status"] == "claimed"
    # nothing left to claim — the second worker gets empty, not the same job
    second = jobs.claim(tmp_path, worker="worker-B")
    assert second["status"] == "empty"


def test_only_lease_holder_may_complete(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-3")
    claimed = jobs.claim(tmp_path, worker="worker-A")
    job_id = claimed["job"]["job_id"]
    # a non-holder cannot complete
    bad = jobs.complete(tmp_path, job_id, worker="worker-B")
    assert bad["status"] == "error"
    # the holder can
    ok = jobs.complete(tmp_path, job_id, worker="worker-A")
    assert ok["status"] == "done"
    assert jobs.status(tmp_path)["counts"]["done"] == 1


def test_expired_lease_is_requeued(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-4", retries=2)
    claimed = jobs.claim(tmp_path, worker="worker-A")
    job_id = claimed["job"]["job_id"]
    # force the lease into the past
    leased = tmp_path / ".aios" / "jobs" / "leased" / f"{job_id}.json"
    import json
    rec = json.loads(leased.read_text())
    rec["lease_until"] = time.time() - 1
    leased.write_text(json.dumps(rec))
    swept = jobs.sweep(tmp_path)
    assert job_id in swept["requeued"]
    assert jobs.status(tmp_path)["counts"]["queued"] == 1


def test_retries_exhausted_fails_with_named_reason(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-5", retries=0)
    claimed = jobs.claim(tmp_path, worker="worker-A")
    job_id = claimed["job"]["job_id"]
    leased = tmp_path / ".aios" / "jobs" / "leased" / f"{job_id}.json"
    import json
    rec = json.loads(leased.read_text())
    rec["lease_until"] = time.time() - 1
    leased.write_text(json.dumps(rec))
    swept = jobs.sweep(tmp_path)
    assert job_id in swept["failed"]
    failed = tmp_path / ".aios" / "jobs" / "failed" / f"{job_id}.json"
    assert "lease expired" in json.loads(failed.read_text())["fail_reason"]


def test_claim_key_claims_the_specific_job(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "asc-7.hivemind")
    jobs.enqueue(tmp_path, "dispatch", "asc-8.memoryOS")
    r = jobs.claim_key(tmp_path, worker="watcher-A", job_key="asc-8.memoryOS")
    assert r["status"] == "claimed"
    assert r["job"]["job_key"] == "asc-8.memoryOS"
    # the other job is untouched
    assert jobs.status(tmp_path)["counts"]["queued"] == 1


def test_claim_key_second_claim_is_unavailable(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "asc-9.hivemind")
    first = jobs.claim_key(tmp_path, worker="watcher-A", job_key="asc-9.hivemind")
    assert first["status"] == "claimed"
    second = jobs.claim_key(tmp_path, worker="watcher-B", job_key="asc-9.hivemind")
    assert second["status"] == "unavailable"


def test_claim_key_absent_when_no_job(tmp_path):
    r = jobs.claim_key(tmp_path, worker="watcher-A", job_key="never-enqueued")
    assert r["status"] == "absent"


def test_complete_by_job_key(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "asc-10.uri")
    jobs.claim_key(tmp_path, worker="watcher-A", job_key="asc-10.uri")
    # complete accepts the job_key via the _find_leased fallback
    done = jobs.complete(tmp_path, "asc-10.uri", worker="watcher-A")
    assert done["status"] == "done"
    assert jobs.status(tmp_path)["counts"]["done"] == 1


def test_log_is_append_only(tmp_path):
    jobs.enqueue(tmp_path, "dispatch", "key-6")
    claimed = jobs.claim(tmp_path, worker="worker-A")
    jobs.complete(tmp_path, claimed["job"]["job_id"], worker="worker-A")
    log = (tmp_path / ".aios" / "jobs" / "log.jsonl").read_text().strip().splitlines()
    events = [__import__("json").loads(l)["event"] for l in log]
    assert events == ["enqueue", "claim", "complete"]
