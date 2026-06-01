#!/usr/bin/env python3
"""AIOS ContractObject runtime — the execution kernel.

This is the missing head piece from docs/AIOS_MINIMUM_KERNEL_AUDIT.md: a
runtime that *executes* a ContractObject's steps as governed syscalls instead
of leaving the contract as an inert document.

Every step is:
  1. authority-checked against the contract's filesystem/provider/network scope
     (deny precedence; nothing runs that the contract did not pre-authorize);
  2. dispatched to a typed syscall handler (fs.read/list/write/delete/move,
     web, provider.<name>);
  3. recorded as a Receipt with artifacts + summary (append-only audit);
  4. for filesystem mutations: backed up first, so every write/delete/move is
     reversible via `rollback`.

The contract state machine is advanced automatically:
  accepted -> running -> verified -> closed
A step with requires_checkpoint=True stops the run at `waiting_user` so a peer
can review before the kernel proceeds (operator override invariant).

Design constraints (match aios_contract_object.py):
  - stdlib only
  - no secrets in git artifacts: backups + receipts live under .aios/ (gitignored)
  - provider/web syscalls are adapter-routed; offline they record an explicit
    "no live substrate" receipt rather than failing silently (named exit).
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent


def _load_contract_object_module():
    """Load aios_contract_object regardless of cwd / sys.path state."""
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))
    name = "aios_contract_object"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(
        name, _SCRIPT_DIR / "aios_contract_object.py"
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


co = _load_contract_object_module()


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# --- runtime artifact locations (all under gitignored .aios/) -----------------

def _runtime_root(contract: Any) -> Path:
    root = Path(contract.workspace_root).resolve() if contract.workspace_root else Path.cwd().resolve()
    return root / ".aios" / "runtime"


def _backup_dir(contract: Any) -> Path:
    return _runtime_root(contract) / "backups" / contract.contract_id


def _receipts_file(contract: Any) -> Path:
    return _runtime_root(contract) / "receipts" / f"{contract.contract_id}.jsonl"


# --- typed syscall handlers ---------------------------------------------------
#
# Each handler returns (success, artifacts, summary, error).
# Handlers assume authorize_step() already passed — they enforce nothing extra
# except real filesystem reality (missing files, etc).

def _syscall_fs_read(contract: Any, step: Any) -> tuple[bool, list[str], str, str | None]:
    path = Path(step.inputs.get("path", "")).expanduser()
    if not path.exists():
        return False, [], "", f"path not found: {path}"
    if path.is_dir():
        return False, [], "", f"path is a directory (use fs.list): {path}"
    max_bytes = int(step.inputs.get("max_bytes", 4096))
    data = path.read_text(encoding="utf-8", errors="replace")[:max_bytes]
    return True, [str(path)], f"read {len(data)} chars from {path.name}", None


def _syscall_fs_list(contract: Any, step: Any) -> tuple[bool, list[str], str, str | None]:
    path = Path(step.inputs.get("path", "")).expanduser()
    if not path.exists():
        return False, [], "", f"path not found: {path}"
    if not path.is_dir():
        return False, [], "", f"not a directory: {path}"
    entries = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
    return True, entries, f"listed {len(entries)} entries in {path.name}", None


def _backup_path(contract: Any, target: Path, seq: int) -> Path:
    bdir = _backup_dir(contract)
    bdir.mkdir(parents=True, exist_ok=True)
    return bdir / f"{seq:04d}__{target.name}"


def _record_backup_manifest(contract: Any, entry: dict[str, Any]) -> None:
    manifest = _backup_dir(contract) / "manifest.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with manifest.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _syscall_fs_write(contract: Any, step: Any, seq: int) -> tuple[bool, list[str], str, str | None]:
    path = Path(step.inputs.get("path", "")).expanduser()
    content = step.inputs.get("content", "")
    old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else None
    backup_ref = None
    if old is not None:
        bpath = _backup_path(contract, path, seq)
        bpath.write_text(old, encoding="utf-8")
        backup_ref = str(bpath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            (old or "").splitlines(keepends=True),
            content.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
    )
    _record_backup_manifest(contract, {
        "op": "write", "target": str(path), "backup": backup_ref,
        "existed": old is not None, "at": _now(), "step_id": step.id,
    })
    n = len(diff.splitlines())
    verb = "created" if old is None else "modified"
    return True, [str(path)] + ([backup_ref] if backup_ref else []), \
        f"{verb} {path.name} ({n} diff lines; reversible)", None


def _syscall_fs_delete(contract: Any, step: Any, seq: int) -> tuple[bool, list[str], str, str | None]:
    path = Path(step.inputs.get("path", "")).expanduser()
    if not path.exists():
        return False, [], "", f"path not found: {path}"
    if path.is_dir():
        return False, [], "", f"refusing to delete directory in v0: {path}"
    bpath = _backup_path(contract, path, seq)
    shutil.copy2(path, bpath)
    _record_backup_manifest(contract, {
        "op": "delete", "target": str(path), "backup": str(bpath),
        "at": _now(), "step_id": step.id,
    })
    path.unlink()
    return True, [str(bpath)], f"deleted {path.name} (backed up; reversible)", None


def _syscall_fs_move(contract: Any, step: Any, seq: int) -> tuple[bool, list[str], str, str | None]:
    src = Path(step.inputs.get("src", "")).expanduser()
    dst = Path(step.inputs.get("dst", "")).expanduser()
    if not src.exists():
        return False, [], "", f"src not found: {src}"
    _record_backup_manifest(contract, {
        "op": "move", "src": str(src), "dst": str(dst),
        "at": _now(), "step_id": step.id,
    })
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))
    return True, [str(dst)], f"moved {src.name} -> {dst} (reversible)", None


def _syscall_provider(contract: Any, step: Any, adapters: dict[str, Any]) -> tuple[bool, list[str], str, str | None]:
    provider = step.tool.split(".", 1)[1]
    adapter = adapters.get(provider)
    if adapter is None:
        # Named exit, not silent failure: the contract authorized this provider
        # but no live substrate is wired. Record it honestly.
        return False, [], "", f"provider '{provider}' authorized but no live adapter (offline)"
    try:
        out = adapter(step.inputs.get("prompt", ""))
    except Exception as exc:  # adapter is external substrate
        return False, [], "", f"provider '{provider}' adapter error: {exc}"
    return True, [], f"provider '{provider}' returned {len(str(out))} chars", None


def _syscall_web(contract: Any, step: Any) -> tuple[bool, list[str], str, str | None]:
    # web is network-gated by authorize_step; offline kernel records a named exit.
    target = step.inputs.get("url") or step.inputs.get("query") or ""
    return False, [], "", f"web '{target}' authorized but no live network substrate (offline)"


def _web_cache_path(contract: Any, step: Any) -> Path:
    d = _runtime_root(contract) / "web" / contract.contract_id
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{step.id}.txt"


def _syscall_web_fetch(contract: Any, step: Any, fetcher) -> tuple[bool, list[str], str, str | None]:
    """web -> action, kernel-low: fetch to a deterministic runtime cache file.

    The fetched content lands at .aios/runtime/web/<cid>/<sid>.txt (a predictable
    path the planner can wire a downstream fs.read against). This is file-as-IPC
    — no inter-step dataflow engine (decision A: kernel, not workflow).
    The fetcher is dependency-injected so the kernel never hardcodes a network
    client; absent fetcher takes the offline named-exit.
    """
    if fetcher is None:
        return _syscall_web(contract, step)
    target = step.inputs.get("url") or step.inputs.get("query") or ""
    if not target:
        return False, [], "", "web step has neither url nor query"
    try:
        content = fetcher(step.inputs)
    except Exception as exc:  # network substrate is external
        return False, [], "", f"web fetch failed for '{target}': {exc}"
    cache = _web_cache_path(contract, step)
    cache.write_text(content, encoding="utf-8")
    return True, [str(cache)], f"fetched {len(content)} chars from '{target}' -> {cache.name}", None


# --- the run loop -------------------------------------------------------------

def run_contract(
    contract: Any,
    *,
    adapters: dict[str, Any] | None = None,
    fetcher: Any = None,
    memory_sink: Any = None,
    approve_checkpoints: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute a ContractObject's steps under its declared authority.

    Returns a run summary dict. Mutates `contract` in place (state, receipts).
    `fetcher(inputs)->str` is the optional network substrate for web syscalls.
    `memory_sink(contract)->dict` is the optional closeout hook that turns the
    run's receipts into draft-first memory (injected, not baked — decision A
    keeps the kernel small; memoryOS owns the actual draft).
    """
    adapters = adapters or {}
    Receipt = co.Receipt

    pre_errors = contract.validate()
    if pre_errors:
        return {"status": "invalid", "errors": pre_errors}

    # advance to running (incl. resume from a checkpoint halt)
    if contract.state == "proposed":
        contract.transition("accepted", reason="runner auto-accept")
    if contract.state == "accepted":
        contract.transition("running", reason="runner start")
    if contract.state == "waiting_user":
        contract.transition("running", reason="runner resume after checkpoint")
    if contract.state != "running":
        return {"status": "bad_state", "state": contract.state,
                "detail": "contract must be proposed/accepted/running/waiting_user to run"}

    done_ok = {r.step_id for r in contract.receipts if r.success}
    executed: list[dict[str, Any]] = []
    seq = len(contract.receipts)  # keep backup sequence monotonic across resumes
    halted_at: str | None = None

    for step in contract.steps:
        # idempotent resume: never re-run a step that already succeeded
        if step.id in done_ok:
            executed.append({"step": step.id, "status": "skipped", "summary": "already succeeded"})
            continue

        # checkpoint gate (operator override invariant)
        if step.requires_checkpoint and not approve_checkpoints:
            contract.user_checkpoints.append(step.id)
            contract.transition("waiting_user", reason=f"checkpoint at step {step.id}")
            halted_at = step.id
            executed.append({"step": step.id, "status": "checkpoint", "summary": "awaiting peer approval"})
            break

        auth_errors = contract.authorize_step(step)
        if auth_errors:
            r = Receipt(step_id=step.id, timestamp=_now(), success=False,
                        summary="authority denied", error="; ".join(auth_errors))
            contract.record_receipt(r)
            executed.append({"step": step.id, "status": "denied", "summary": r.error})
            # authority denial blocks the contract — named exit
            contract.transition("blocked", reason=f"authority denied at {step.id}")
            halted_at = step.id
            break

        if dry_run:
            executed.append({"step": step.id, "status": "would_run",
                             "summary": f"{step.tool} (authorized)"})
            continue

        seq += 1
        success, artifacts, summary, error = _dispatch(contract, step, seq, adapters, fetcher)
        r = Receipt(step_id=step.id, timestamp=_now(), success=success,
                    artifacts=artifacts, summary=summary, error=error)
        contract.record_receipt(r)
        executed.append({"step": step.id, "status": "ok" if success else "failed",
                         "summary": summary or error})
        if not success and step.inputs.get("hard", True):
            contract.transition("blocked", reason=f"step {step.id} failed: {error}")
            halted_at = step.id
            break

    _flush_receipts(contract)

    if halted_at is not None or dry_run:
        return {"status": contract.state, "halted_at": halted_at,
                "executed": executed, "dry_run": dry_run}

    # all steps executed — verify + close
    _run_evals(contract)
    failed_required = [e for e in contract.evals if e.required and e.result == "fail"]
    if failed_required:
        contract.transition("blocked", reason="required eval failed")
        return {"status": contract.state, "executed": executed,
                "evals": [(e.name, e.result) for e in contract.evals]}
    contract.transition("verified", reason="runner evals passed")
    contract.transition("closed", reason="runner closeout")
    result = {"status": contract.state, "executed": executed,
              "evals": [(e.name, e.result) for e in contract.evals]}
    if memory_sink is not None:
        try:
            result["memory"] = memory_sink(contract)
        except Exception as exc:  # memory write-back must never fail a closed run
            result["memory"] = {"status": "error", "detail": str(exc)[:200]}
    return result


def _dispatch(contract: Any, step: Any, seq: int, adapters: dict[str, Any], fetcher: Any = None):
    tool = step.tool
    if tool == "fs.read":
        return _syscall_fs_read(contract, step)
    if tool == "fs.list":
        return _syscall_fs_list(contract, step)
    if tool == "fs.write":
        return _syscall_fs_write(contract, step, seq)
    if tool == "fs.delete":
        return _syscall_fs_delete(contract, step, seq)
    if tool == "fs.move":
        return _syscall_fs_move(contract, step, seq)
    if tool.startswith("provider."):
        return _syscall_provider(contract, step, adapters)
    if tool == "web":
        return _syscall_web_fetch(contract, step, fetcher)
    return False, [], "", f"unknown syscall '{tool}'"


def _run_evals(contract: Any) -> None:
    """Best-effort eval resolution. v0 supports a tiny check DSL:
        'receipts_all_success'  -> every receipt succeeded
        'receipts >= N'         -> at least N successful receipts
    Unknown checks are left unrun (result=None) and do not block.
    """
    ok_count = sum(1 for r in contract.receipts if r.success)
    for e in contract.evals:
        check = (e.check or "").strip()
        if check == "receipts_all_success":
            e.result = "pass" if contract.receipts and all(r.success for r in contract.receipts) else "fail"
        elif check.startswith("receipts >="):
            try:
                n = int(check.split(">=", 1)[1])
                e.result = "pass" if ok_count >= n else "fail"
            except ValueError:
                e.result = None


def _flush_receipts(contract: Any) -> None:
    path = _receipts_file(contract)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in contract.receipts:
            fh.write(json.dumps(co.dc.asdict(r), ensure_ascii=False) + "\n")


# --- rollback -----------------------------------------------------------------

def rollback(contract: Any) -> dict[str, Any]:
    """Restore every backed-up filesystem mutation in reverse order."""
    manifest = _backup_dir(contract) / "manifest.jsonl"
    if not manifest.exists():
        return {"status": "nothing_to_rollback"}
    entries = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
    restored: list[str] = []
    for entry in reversed(entries):
        op = entry.get("op")
        if op == "write":
            target = Path(entry["target"])
            if entry.get("existed") and entry.get("backup"):
                shutil.copy2(entry["backup"], target)
                restored.append(f"restored {target}")
            elif not entry.get("existed") and target.exists():
                target.unlink()
                restored.append(f"removed {target}")
        elif op == "delete" and entry.get("backup"):
            shutil.copy2(entry["backup"], Path(entry["target"]))
            restored.append(f"undeleted {entry['target']}")
        elif op == "move":
            src, dst = Path(entry["src"]), Path(entry["dst"])
            if dst.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
                restored.append(f"moved back {dst} -> {src}")
    return {"status": "rolled_back", "restored": restored}


# --- CLI ----------------------------------------------------------------------

def _load_contract(path: str) -> Any:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return co.ContractObject.from_dict(data)


def _save_contract(contract: Any, path: str) -> None:
    Path(path).write_text(contract.to_json(), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AIOS ContractObject runtime kernel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="execute a contract's steps under its authority")
    run.add_argument("contract", help="path to a ContractObject json file")
    run.add_argument("--approve-checkpoints", action="store_true",
                     help="proceed through requires_checkpoint steps without stopping")
    run.add_argument("--dry-run", action="store_true",
                     help="authorize every step but execute nothing")
    run.add_argument("--write", action="store_true",
                     help="write the mutated contract back to the json file")
    run.add_argument("--no-live-providers", action="store_true",
                     help="do not wire real provider CLIs; provider steps take the offline named-exit")

    rb = sub.add_parser("rollback", help="restore all filesystem mutations of a contract")
    rb.add_argument("contract")

    args = parser.parse_args(argv)
    contract = _load_contract(args.contract)

    if args.cmd == "run":
        adapters: dict[str, Any] = {}
        if not args.no_live_providers and not args.dry_run:
            # only build adapters for providers this contract actually authorized
            authorized = [r.provider for r in contract.provider_routes]
            if authorized:
                try:
                    import aios_adapters
                    adapters = aios_adapters.build_adapters(providers=authorized)
                except Exception:  # adapter layer optional; runner still works
                    adapters = {}
        summary = run_contract(
            contract,
            adapters=adapters,
            approve_checkpoints=args.approve_checkpoints,
            dry_run=args.dry_run,
        )
        if args.write and not args.dry_run:
            _save_contract(contract, args.contract)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("status") in ("closed", "waiting_user", "running", "would_run", None) or args.dry_run else 1

    if args.cmd == "rollback":
        print(json.dumps(rollback(contract), ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
