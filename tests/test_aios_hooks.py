"""Tests for the deterministic enforcement hooks (ASC-0184)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "aios_hooks", Path(__file__).resolve().parent.parent / "scripts" / "aios_hooks.py")
hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hooks)


def test_privacy_boundary_blocks(tmp_path):
    d = hooks.evaluate(tmp_path, {"kind": "write", "paths": ["dain/notes.md"]})
    assert d["verdict"] == "block"
    assert any("privacy" in b["reason"] for b in d["blocking"])


def test_privacy_boundary_blocks_env_and_secrets(tmp_path):
    for p in (".env", "config/secret_key", "_from_desktop/x"):
        d = hooks.evaluate(tmp_path, {"kind": "write", "paths": [p]})
        assert d["verdict"] == "block", p


def test_clean_path_allowed(tmp_path):
    d = hooks.evaluate(tmp_path, {"kind": "write", "paths": ["docs/notes.md"]})
    assert d["verdict"] == "allow"


def test_append_only_audit_blocks_ledger_overwrite(tmp_path):
    d = hooks.evaluate(tmp_path, {"kind": "overwrite",
                                  "paths": ["docs/AIOS_AGENT_LEDGER.md"]})
    assert d["verdict"] == "block"


def test_append_only_audit_allows_normal_write_to_ledger(tmp_path):
    # a plain write (append) to the ledger is fine — only delete/overwrite block
    d = hooks.evaluate(tmp_path, {"kind": "write",
                                  "paths": ["docs/AIOS_AGENT_LEDGER.md"]})
    assert d["verdict"] == "allow"


def test_contract_scope_blocks_out_of_scope(tmp_path):
    contracts = tmp_path / "docs" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / "ASC-9001-demo.md").write_text(
        "---\ncontract_id: ASC-9001\n---\n\nallowed_files:\n\n- `scripts/ok.py`\n")
    blocked = hooks.evaluate(tmp_path, {"kind": "write", "paths": ["scripts/evil.py"],
                                        "contract_id": "ASC-9001"})
    assert blocked["verdict"] == "block"
    allowed = hooks.evaluate(tmp_path, {"kind": "write", "paths": ["scripts/ok.py"],
                                        "contract_id": "ASC-9001"})
    assert allowed["verdict"] == "allow"


def test_contract_scope_escalates_when_contract_missing(tmp_path):
    d = hooks.evaluate(tmp_path, {"kind": "write", "paths": ["x.py"],
                                  "contract_id": "ASC-0000"})
    assert d["verdict"] == "escalate"


def test_operator_override_converts_block(tmp_path):
    d = hooks.evaluate(tmp_path, {
        "kind": "write", "paths": ["dain/notes.md"],
        "operator_override": {"decision": "allow", "reason": "founder authorized"}})
    assert d["verdict"] == "allow_overridden"


def test_decision_is_logged(tmp_path):
    hooks.evaluate(tmp_path, {"kind": "write", "paths": ["docs/ok.md"]})
    log = tmp_path / ".aios" / "hooks" / "log.jsonl"
    assert log.exists() and log.read_text().strip()
