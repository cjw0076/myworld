"""Hermetic unit tests for the headline A/B harness LOGIC only.

NO model calls and NO network: the model (`generate`) and the pytest oracle (`run_oracle`)
are stubbed via monkeypatch, and the ledger lives in an isolated tempdir AIOS_HOME. These
tests cover battery loading, the code extractor, the no-train/test-leakage guard, and the
metric math — not the empirical experiment (that lives in docs/AIOS_HEADLINE_AB_RESULTS.md).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

# Isolate AIOS_HOME BEFORE the harness lazily imports aios_agent_behavior, and force the
# global akashic server unreachable so nothing can egress during import/seed.
_TMP_HOME = tempfile.mkdtemp(prefix="aios_ab_test_home_")
os.environ["AIOS_HOME"] = _TMP_HOME
os.environ["AIOS_AKASHIC_URL"] = "http://127.0.0.1:9"

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))
import aios_headline_ab as h  # noqa: E402


def test_load_battery_disjoint_counts():
    b = h.load_battery()
    assert len(b["train"]) == 3
    assert len(b["test"]) == 5
    train_names = {t.name for t in b["train"]}
    test_names = {t.name for t in b["test"]}
    assert train_names.isdisjoint(test_names)  # TRAIN and TEST are distinct problems
    for t in b["train"] + b["test"]:
        assert t.function and t.prompt
        assert t.module == "solution"
        assert t.oracle_path.exists()


def test_extract_code():
    assert h.extract_code("pre\n```python\nx=1\n```\npost") == "x=1"
    assert h.extract_code("```\ny=2\n```") == "y=2"
    assert h.extract_code("no fence here").strip() == "no fence here"


def test_arm_metrics_math():
    runs = [
        {"solved": True,  "solved_first": True,  "attempts": 1, "out_tokens": 10, "in_tokens": 5, "ok": True},
        {"solved": True,  "solved_first": False, "attempts": 2, "out_tokens": 20, "in_tokens": 5, "ok": True},
        {"solved": False, "solved_first": False, "attempts": 2, "out_tokens": 30, "in_tokens": 5, "ok": True},
        {"solved": False, "solved_first": False, "attempts": 2, "out_tokens": 40, "in_tokens": 5, "ok": False},
    ]
    m = h._arm_metrics(runs)
    assert m["trials"] == 4
    assert m["solved"] == 2
    assert m["solve_rate"] == 0.5
    assert m["first_attempt_solved"] == 1
    assert m["first_attempt_solve_rate"] == 0.25
    assert m["mean_attempts_to_solve"] == 1.5   # (1+2)/2 among solved
    assert m["mean_attempts_all"] == 1.75       # (1+2+2+2)/4 over all
    assert m["total_out_tokens"] == 100
    assert m["errored_runs"] == 1


def test_arm_metrics_empty_solved():
    runs = [{"solved": False, "solved_first": False, "attempts": 2,
             "out_tokens": 7, "in_tokens": 1, "ok": True}]
    m = h._arm_metrics(runs)
    assert m["solve_rate"] == 0.0
    assert m["mean_attempts_to_solve"] is None  # no solved runs
    assert m["mean_attempts_all"] == 2.0


def test_no_leakage_guard(monkeypatch):
    """Seed the ledger fully offline (stubbed model + oracle) and assert that NO TEST-task
    identifier leaks into any recorded behavioral object. The ledger must only ever carry
    TRAIN-derived behavioral signatures — never anything derived from a TEST task."""
    monkeypatch.setattr(
        h, "generate",
        lambda prompt, model, seed, temperature=h.TEMPERATURE: {
            "text": "```python\ndef f():\n    return 1\n```",
            "out_tokens": 5, "in_tokens": 5, "ok": True, "error": "",
        },
    )
    # alternate pass/fail so both the quick and the fix (retry) sequences are exercised
    calls = {"n": 0}

    def fake_oracle(oracle_path, code, module):
        calls["n"] += 1
        return (calls["n"] % 2 == 0, "AssertionError: expected 1 got 2")

    monkeypatch.setattr(h, "run_oracle", fake_oracle)

    battery = h.load_battery()
    summary = h.seed_ledger(battery["train"], model="stub-model")
    assert summary["records_written"] >= 1

    bh = h._behavior_module()
    mems = bh.load_behavior_memories()
    assert len(mems) >= 1

    forbidden = set()
    for t in battery["test"]:
        forbidden.add(t.name.lower())
        forbidden.add(t.function.lower())
    blob = json.dumps(mems, ensure_ascii=False).lower()
    for bad in forbidden:
        assert bad not in blob, f"TEST identifier leaked into ledger: {bad!r}"

    # sanity: the ledger DID record the (allowed) disjoint TRAIN provenance
    train_names = {t.name for t in battery["train"]}
    assert any(
        any(tn in ref for ref in m.get("evidence_refs", []))
        for m in mems for tn in train_names
    )
    # every record is behavioral + draft (never auto-accepted; DNA invariant)
    for m in mems:
        assert m.get("domain") == "agent_behavior"
        assert m.get("status") == "draft"
