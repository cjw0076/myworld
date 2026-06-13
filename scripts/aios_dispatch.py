#!/usr/bin/env python3
"""File-based AIOS dispatch control-plane CLI.

This script only writes myworld control-plane packets under `.aios/`. It does
not execute child repo work and does not edit child repo files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aios_close_condition import CLOSE_TYPES, evaluate_contract
from aios_action_policy import evaluate_action
from aios_work_praxis import validate_praxis
from aios_authority import audit_authority, current_agent_id, verify_authority


REPOS = ("myworld", "hivemind", "memoryOS", "CapabilityOS", "GenesisOS")
STATE_DIR = Path(".aios/state")
STATE_LOG = STATE_DIR / "dispatches.jsonl"
INBOX_DIR = Path(".aios/inbox")
OUTBOX_DIR = Path(".aios/outbox")
LOG_DIR = Path(".aios/logs")
LEASE_DIR = Path(".aios/leases")       # runtime-only, not committed
LEASE_TTL_DEFAULT = 300                # seconds
RUNTIME_PROFILE_FILE = Path(".aios/runtime_profile.json")  # runtime-only, not committed (ASC-0249)
RUNTIME_PROFILES = ("build_control", "live_agent_runtime", "end_user_serving")
DEFAULT_RUNTIME_PROFILE = "build_control"
TERMINAL_STATES = ("released", "held", "retried", "escalated")
STATE_COMMANDS = {
    "release": "released",
    "hold": "held",
    "retry": "retried",
    "escalate": "escalated",
}
SHELL_META = (";", "&&", "||", "|", "`", "$(", ">", "<")


@dataclass(frozen=True)
class Contract:
    path: Path
    frontmatter: dict[str, str]
    body: str
    repos: list[str]
    allowed_files: list[str]
    allowed_existing_dirty: list[str]
    forbidden_files: list[str]

    @property
    def contract_id(self) -> str:
        return self.frontmatter.get("contract_id") or self.path.stem.split("-", 1)[0]

    @property
    def status(self) -> str:
        return self.frontmatter.get("status") or "unknown"

    @property
    def goal(self) -> str:
        return self.frontmatter.get("goal") or ""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path.cwd().resolve()


def ensure_layout(root: Path) -> None:
    (root / STATE_DIR).mkdir(parents=True, exist_ok=True)
    (root / LOG_DIR).mkdir(parents=True, exist_ok=True)
    (root / LEASE_DIR).mkdir(parents=True, exist_ok=True)
    for repo in REPOS:
        (root / INBOX_DIR / repo).mkdir(parents=True, exist_ok=True)
        (root / OUTBOX_DIR / repo).mkdir(parents=True, exist_ok=True)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    data: dict[str, str] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip()
    return data, body


def extract_bullet_list(body: str, label: str) -> list[str]:
    lines = body.splitlines()
    values: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"{label}:":
            collecting = True
            continue
        if not collecting:
            continue
        if not stripped:
            if values:
                break
            continue
        if stripped.startswith("- "):
            values.append(stripped[2:].strip().strip("`"))
            continue
        if values:
            break
    return values


def read_contract(path: Path) -> Contract:
    if not path.exists():
        raise SystemExit(f"contract not found: {path}")
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    repos = extract_bullet_list(body, "repos")
    allowed_files = extract_bullet_list(body, "allowed_files")
    allowed_existing_dirty = extract_bullet_list(body, "allowed_existing_dirty")
    forbidden_files = extract_bullet_list(body, "forbidden_files")
    return Contract(
        path=path,
        frontmatter=frontmatter,
        body=body,
        repos=repos,
        allowed_files=allowed_files,
        allowed_existing_dirty=allowed_existing_dirty,
        forbidden_files=forbidden_files,
    )


def normalize_repo_path(repo: str, raw: str) -> str:
    value = str(raw).strip().strip("`")
    if value.startswith(("?? ", "M ", "A ", "D ", "R ", "C ", "!! ")):
        value = value[3:].strip()
    if value.startswith(f"{repo}/"):
        value = value[len(repo) + 1 :]
    return value.rstrip("/")


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_porcelain_z(stdout: bytes) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for raw_record in stdout.split(b"\0"):
        if not raw_record:
            continue
        record = raw_record.decode("utf-8", errors="surrogateescape")
        if len(record) < 4:
            continue
        rows.append((record[:2], record[3:]))
    return rows


def capture_allowed_existing_dirty_baseline(root: Path, repo: str, allowed: list[str]) -> list[dict[str, str | None]]:
    repo_dir = root / repo
    if not allowed or not (repo_dir / ".git").exists():
        return []
    baselines: list[dict[str, str | None]] = []
    for raw in allowed:
        repo_path = normalize_repo_path(repo, raw)
        if not repo_path:
            continue
        result = subprocess.run(
            [
                "git",
                "-C",
                repo_dir.as_posix(),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--",
                repo_path,
            ],
            check=False,
            capture_output=True,
        )
        status_code = ""
        status_path = repo_path
        if result.returncode == 0:
            rows = parse_porcelain_z(result.stdout)
            if rows:
                status_code, status_path = rows[0]
        baselines.append(
            {
                "path": f"{repo}/{status_path}",
                "repo_path": status_path,
                "status_code": status_code,
                "sha256": sha256_file(repo_dir / status_path),
            }
        )
    return baselines


def _load_sibling(root: Path, module_name: str):
    """Import a sibling scripts/ module by path; None on any failure — the
    dispatch path must not break if an optional organ is absent."""
    import importlib.util

    path = root / "scripts" / f"{module_name}.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:  # noqa: BLE001
        return None


def hook_preflight(root: Path, contract: "Contract") -> dict[str, Any] | None:
    """ASC-0184 — run the deterministic enforcement hooks on a contract's
    declared allowed_files before its packet is dispatched. Returns the hook
    decision iff it BLOCKED, else None. The integration glue fails open (a
    missing engine never blocks); the engine itself fails closed on privacy."""
    hooks = _load_sibling(root, "aios_hooks")
    if hooks is None:
        return None
    action = {
        "kind": "dispatch",
        "paths": list(contract.allowed_files),
        "contract_id": contract.contract_id,
    }
    try:
        decision = hooks.evaluate(root, action)
    except Exception:  # noqa: BLE001
        return None
    return decision if decision.get("verdict") == "block" else None


# --- Dispatch Lease / Collision Control (ASC-0248) ---------------------------

def _lease_path(root: Path, dispatch_id: str, repo: str) -> Path:
    return root / LEASE_DIR / f"{dispatch_id}.{repo}.lease.json"


def is_lease_stale(lease: dict[str, Any]) -> bool:
    """Return True when the lease has passed its expires_at timestamp."""
    expires_at = lease.get("expires_at")
    if not expires_at:
        return True
    try:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= exp
    except (ValueError, TypeError):
        return True


def get_dispatch_lease(root: Path, dispatch_id: str, repo: str) -> dict[str, Any] | None:
    """Return the current lease dict or None if no lease file exists."""
    p = _lease_path(root, dispatch_id, repo)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def claim_dispatch_lease(
    root: Path,
    dispatch_id: str,
    repo: str,
    agent: str,
    *,
    ttl_seconds: int = LEASE_TTL_DEFAULT,
) -> dict[str, Any]:
    """Atomically claim a dispatch lease.

    Returns:
      {"status": "claimed", "lease": {...}}
      {"status": "collision", "stale": False, "owner": {...}}
      {"status": "collision", "stale": True,  "owner": {...}}   # caller may reclaim
    """
    ensure_layout(root)
    lease_path = _lease_path(root, dispatch_id, repo)
    now = datetime.now(timezone.utc)
    expires_dt = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
    lease = {
        "schema_version": "aios.lease.v0",
        "dispatch_id": dispatch_id,
        "repo": repo,
        "agent": agent,
        "pid": os.getpid(),
        "started_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": expires_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "ttl_seconds": ttl_seconds,
    }
    # Atomic exclusive create: O_CREAT | O_EXCL raises FileExistsError if present.
    try:
        fd = os.open(str(lease_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(lease, indent=2, ensure_ascii=False))
        return {"status": "claimed", "lease": lease}
    except FileExistsError:
        existing = get_dispatch_lease(root, dispatch_id, repo) or {}
        stale = is_lease_stale(existing)
        return {"status": "collision", "stale": stale, "owner": existing}


def release_dispatch_lease(root: Path, dispatch_id: str, repo: str) -> None:
    """Remove the lease file. Idempotent; silent if absent."""
    p = _lease_path(root, dispatch_id, repo)
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass


def reclaim_dispatch_lease(
    root: Path,
    dispatch_id: str,
    repo: str,
    agent: str,
    *,
    reason: str,
    ttl_seconds: int = LEASE_TTL_DEFAULT,
) -> dict[str, Any]:
    """Force-take a stale lease, recording why.

    Returns:
      {"status": "reclaimed", "lease": {...}, "evicted": {...}}
      {"status": "refused",   "reason": "lease is still active", "owner": {...}}
    """
    ensure_layout(root)
    existing = get_dispatch_lease(root, dispatch_id, repo)
    if existing and not is_lease_stale(existing):
        return {"status": "refused", "reason": "lease is still active", "owner": existing}
    now = datetime.now(timezone.utc)
    expires_dt = datetime.fromtimestamp(now.timestamp() + ttl_seconds, tz=timezone.utc)
    lease = {
        "schema_version": "aios.lease.v0",
        "dispatch_id": dispatch_id,
        "repo": repo,
        "agent": agent,
        "pid": os.getpid(),
        "started_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "expires_at": expires_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "ttl_seconds": ttl_seconds,
        "reclaimed_from": existing,
        "reclaim_reason": reason,
    }
    tmp = _lease_path(root, dispatch_id, repo).with_suffix(".tmp")
    tmp.write_text(json.dumps(lease, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(_lease_path(root, dispatch_id, repo)))
    return {"status": "reclaimed", "lease": lease, "evicted": existing}


# --- end Dispatch Lease -------------------------------------------------------


# --- Build/Runtime Isolation Profile (ASC-0249) ------------------------------

def runtime_profile_state(root: Path, override: str | None = None) -> dict[str, Any]:
    """Resolve the active build-vs-runtime isolation profile.

    Two labeled rooms on one machine:
      - ``build_control``      — contracts, code changes, verification, delegation;
      - ``live_agent_runtime`` — actual AIOS agent workloops/pulses.
      - ``end_user_serving``   — user-delegated serving sessions.

    Resolution order (later overrides earlier): default -> file under .aios/
    -> environment -> explicit caller override. The default is
    ``build_control`` with live child execution disallowed: the conservative
    "we are building AIOS" assumption, so a build context never *silently*
    spawns a live child provider session. ``live_agent_runtime`` implies live
    child execution is allowed by definition. ``end_user_serving`` opens live
    child execution only when an explicit serving-session artifact is bound or
    an explicit allow flag is present.

    State lives under ``.aios/`` which is gitignored, so the profile never
    enters commits (ASC-0249 negated check ``runtime_profile_committed``).
    """
    profile = DEFAULT_RUNTIME_PROFILE
    allow_live = False
    source = "default"
    serving_session_artifact = ""
    path = root / RUNTIME_PROFILE_FILE
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if str(data.get("profile")) in RUNTIME_PROFILES:
                profile = str(data["profile"])
                source = "file"
            allow_live = bool(data.get("allow_live_child_execution", allow_live))
            serving_session_artifact = str(data.get("serving_session_artifact") or "")
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    env_profile = os.environ.get("AIOS_RUNTIME_PROFILE", "").strip()
    if env_profile in RUNTIME_PROFILES:
        profile = env_profile
        source = "env"
    env_allow = os.environ.get("AIOS_ALLOW_LIVE_CHILD_EXECUTION", "").strip().lower()
    if env_allow in {"1", "true", "yes"}:
        allow_live = True
    elif env_allow in {"0", "false", "no"}:
        allow_live = False
    env_serving_artifact = os.environ.get("AIOS_SERVING_SESSION_ARTIFACT", "").strip()
    if env_serving_artifact:
        serving_session_artifact = env_serving_artifact
    if override in RUNTIME_PROFILES:
        profile = override
        source = "override"
    serving_boundary = serving_session_boundary_state(root, serving_session_artifact)
    effective_allow = (
        allow_live
        or profile == "live_agent_runtime"
        or (profile == "end_user_serving" and serving_boundary["present"])
    )
    return {
        "schema_version": "aios.runtime_profile.v1",
        "profile": profile,
        "allow_live_child_execution": effective_allow,
        "live_child_execution_blocked": not effective_allow,
        "serving_session_boundary": serving_boundary,
        "source": source,
    }


def _within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def serving_session_boundary_state(root: Path, artifact: str) -> dict[str, Any]:
    if not artifact:
        return {"present": False, "reason": "missing_serving_session_artifact"}
    artifact_path = Path(artifact)
    if not artifact_path.is_absolute():
        artifact_path = root / artifact_path
    serving_root = root / ".aios" / "serving"
    if not _within(artifact_path, serving_root):
        return {"present": False, "reason": "artifact_outside_serving_root"}
    try:
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"present": False, "reason": "artifact_not_found"}
    except (OSError, json.JSONDecodeError, ValueError):
        return {"present": False, "reason": "artifact_unreadable"}
    workspace = str(data.get("workspace_path") or "")
    workspace_path = Path(workspace)
    if not workspace_path.is_absolute():
        workspace_path = root / workspace_path
    if data.get("schema_version") != "aios.serving_session.v1":
        return {"present": False, "reason": "schema_mismatch"}
    if not data.get("user_id") or not data.get("session_id"):
        return {"present": False, "reason": "missing_user_or_session"}
    if not _within(workspace_path, root / ".aios" / "serving" / "workspaces"):
        return {"present": False, "reason": "workspace_outside_serving_root"}
    return {
        "present": True,
        "artifact_path": artifact_path.relative_to(root).as_posix(),
        "workspace_path": workspace_path.relative_to(root).as_posix(),
        "user_id": data.get("user_id"),
        "session_id": data.get("session_id"),
    }


def write_runtime_profile(root: Path, profile: str, allow_live_child_execution: bool) -> dict[str, Any]:
    ensure_layout(root)
    payload = {
        "schema_version": "aios.runtime_profile.v1",
        "profile": profile,
        "allow_live_child_execution": bool(allow_live_child_execution),
        "updated_at": now_iso(),
    }
    (root / RUNTIME_PROFILE_FILE).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


# --- end Build/Runtime Isolation Profile -------------------------------------


def enqueue_dispatch_job(root: Path, dispatch_id: str, repo: str, contract: "Contract") -> None:
    """ASC-0185 — record the dispatch as a leased job alongside the file drop.
    Idempotent (job_key dedup); never raises into the dispatch path."""
    jobs = _load_sibling(root, "aios_jobs")
    if jobs is None:
        return
    try:
        jobs.enqueue(root, kind="dispatch", job_key=f"{dispatch_id}.{repo}",
                     contract_id=contract.contract_id, target_repo=repo)
    except Exception:  # noqa: BLE001
        return


def append_event(root: Path, event: dict[str, Any]) -> None:
    ensure_layout(root)
    event = {"timestamp": now_iso(), **event}
    with (root / STATE_LOG).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def load_events(root: Path) -> list[dict[str, Any]]:
    path = root / STATE_LOG
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


def latest_dispatch_id(root: Path) -> str | None:
    for event in reversed(load_events(root)):
        dispatch_id = event.get("dispatch_id")
        if dispatch_id:
            return str(dispatch_id)
    return None


def dispatch_created(root: Path, dispatch_id: str) -> dict[str, Any] | None:
    for event in reversed(load_events(root)):
        if event.get("dispatch_id") == dispatch_id and event.get("event") == "created":
            return event
    return None


def latest_dispatch_event(root: Path, dispatch_id: str) -> dict[str, Any] | None:
    for event in reversed(load_events(root)):
        if event.get("dispatch_id") == dispatch_id:
            return event
    return None


def latest_packet(root: Path, repo: str) -> Path | None:
    packets = sorted((root / INBOX_DIR / repo).glob("*.json"), key=lambda path: path.stat().st_mtime)
    return packets[-1] if packets else None


def default_dispatch_id(contract: Contract) -> str:
    safe = re.sub(r"[^a-z0-9]+", "-", contract.contract_id.lower()).strip("-")
    return safe or contract.path.stem


def contains_term(text: str, term: str) -> bool:
    escaped = re.escape(term.lower()).replace(r"\ ", r"\s+")
    return bool(re.search(rf"(?<![a-z0-9_-]){escaped}(?![a-z0-9_-])", text))


def contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(contains_term(text, term) for term in terms)


def is_deliberation_only_external_topic(text: str) -> bool:
    deliberation_signal = contains_any_term(
        text,
        (
            "contract deliberates; it does not deploy",
            "this contract deliberates; it does not deploy",
            "produces only deliberation artifacts",
            "deliberation artifacts",
        ),
    )
    no_execution_signal = contains_any_term(
        text,
        (
            "forbidden_files",
            "no deployment code",
            "any deployment manifest",
            "does not deploy",
            "forbidden files",
        ),
    )
    return deliberation_signal and no_execution_signal


def action_policy_input(contract: Contract, dispatch_id: str, repo: str, agent: str) -> dict[str, Any]:
    text = f"{contract.goal}\n{contract.body}".lower()
    public_communication = contains_any_term(text, ("public communication", "public statement", "on behalf"))
    legal_or_safety_impact = contains_any_term(text, ("legal", "medical", "financial", "employment", "safety"))
    uses_credentials = contains_any_term(text, ("credential", "token", "secret", "login"))
    paid_or_costly = contains_any_term(text, ("paid api", "paid", "spend", "billing", "purchase"))
    irreversible = contains_any_term(text, ("irreversible", "delete production", "destructive"))
    real_world_authority = contains_any_term(text, ("real-world authority", "legal authority", "public authority"))
    sends_private_data = contains_any_term(
        text,
        (
            "send private data",
            "sends private data",
            "upload private data",
            "publish private data",
            "send personal data",
            "upload personal data",
            "raw private export publish",
        ),
    )
    external_effect = contains_any_term(
        text,
        (
            "external system",
            "internet search",
            "browse internet",
            "network call",
            "remote api",
            "deploy",
            "paid",
            "credential",
        ),
    )
    deliberation_only_external_topic = is_deliberation_only_external_topic(text)
    effective_external_effect = external_effect and not deliberation_only_external_topic
    return {
        "action_type": "dispatch_packet",
        "target_repo": repo,
        "authority": "accepted_contract" if contract.status in {"accepted", "closed"} else "unaccepted_contract",
        "risk": "high" if any((public_communication, legal_or_safety_impact, paid_or_costly, irreversible, real_world_authority)) else "low",
        "privacy": "remote" if effective_external_effect or sends_private_data else "local",
        "cost": "paid" if paid_or_costly else "free",
        "has_contract": contract.status in {"accepted", "closed"},
        "evidence_refs": [contract.path.as_posix()],
        "human_approved": contract.frontmatter.get("human_approved", "").lower() == "true",
        "irreversible": irreversible,
        "external_effect": effective_external_effect,
        "external_topic": external_effect,
        "deliberation_only_external_topic": deliberation_only_external_topic,
        "uses_credentials": uses_credentials,
        "public_communication": public_communication,
        "legal_or_safety_impact": legal_or_safety_impact,
        "real_world_authority": real_world_authority,
        "sends_private_data": sends_private_data,
        "repos": contract.repos,
        "allowed_files": contract.allowed_files,
        "forbidden_files": contract.forbidden_files,
        "dispatch_id": dispatch_id,
        "agent": agent,
    }


def evaluate_dispatch_policy(contract: Contract, dispatch_id: str, repo: str, agent: str) -> dict[str, Any]:
    action = action_policy_input(contract, dispatch_id, repo, agent)
    result = evaluate_action(action).to_json(action)
    return {
        "schema_version": result["schema_version"],
        "decision": result["decision"],
        "allowed_to_execute": result["allowed_to_execute"],
        "required_checkpoint": result["required_checkpoint"],
        "reason_codes": result["reason_codes"],
        "action": action,
    }


def contract_requires_praxis(contract: Contract) -> bool:
    value = contract.frontmatter.get("praxis_required", "").strip().lower()
    if value in {"true", "yes", "1"}:
        return True
    if value in {"false", "no", "0"}:
        return False
    return False


def contract_requires_session_envelope(contract: Contract) -> bool:
    value = contract.frontmatter.get("session_envelope_required", "").strip().lower()
    if value in {"true", "yes", "1"}:
        return True
    if value in {"false", "no", "0"}:
        return False
    return False


def contract_requires_memory_retrieval(contract: Contract) -> bool:
    value = contract.frontmatter.get("memory_retrieval_required", "").strip().lower()
    if value in {"true", "yes", "1"}:
        return True
    if value in {"false", "no", "0"}:
        return False
    return False


def load_praxis_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("praxis file must contain a JSON object")
    return payload


def positive_signal_coverage(value: str) -> bool:
    raw = value.strip().lower()
    if raw in {"positive", "true", "passed"}:
        return True
    try:
        return float(raw) > 0.0
    except ValueError:
        return False


def validate_session_envelope_for_dispatch(root: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    roles = payload.get("role_statuses") if isinstance(payload.get("role_statuses"), dict) else {}
    degraded = [role for role, status in roles.items() if status != "passed"]
    if degraded:
        errors.append(f"session_envelope_role_degraded:{','.join(sorted(degraded))}")
    return errors


def extract_memory_retrieval_evidence(root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    artifacts = payload.get("role_artifacts") if isinstance(payload.get("role_artifacts"), dict) else {}
    ref = str(artifacts.get("memory_context_pack") or "").strip()
    evidence = {
        "context_pack": ref,
        "retrieval_trace": "",
        "signal_coverage": "",
    }
    errors: list[str] = []
    if not ref:
        return evidence, ["memory_context_pack_missing"]
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    try:
        path.resolve().relative_to((root / ".aios" / "invocations").resolve())
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return evidence, ["memory_context_pack_outside_invocations"]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return evidence, [f"memory_context_pack_unreadable:{exc.__class__.__name__}"]
    trace = re.search(r"\btrace_id:\s*(rtrace_[A-Za-z0-9]+)", text)
    coverage = re.search(r"\bsignal_coverage:\s*([A-Za-z0-9_.+-]+)", text)
    if trace:
        evidence["retrieval_trace"] = trace.group(1)
    else:
        errors.append("retrieval_trace_missing")
    if coverage:
        evidence["signal_coverage"] = coverage.group(1)
        if not positive_signal_coverage(coverage.group(1)):
            errors.append("signal_coverage_not_positive")
    else:
        errors.append("signal_coverage_missing")
    return evidence, errors


def load_session_envelope(root: Path, path_text: str) -> tuple[str, dict[str, Any]]:
    path = Path(path_text)
    if not path.is_absolute():
        path = root / path
    try:
        rel = path.resolve().relative_to((root / ".aios" / "invocations").resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("session envelope must stay under .aios/invocations") from exc
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("session envelope must contain a JSON object")
    if payload.get("schema_version") != "aios.session_envelope.v1":
        raise ValueError("session envelope schema_version must be aios.session_envelope.v1")
    if payload.get("required_before_execution") is not True:
        raise ValueError("session envelope must set required_before_execution=true")
    for field in ("role_statuses", "role_artifacts", "executor_assignment", "degraded_receipt"):
        if not isinstance(payload.get(field), dict):
            raise ValueError(f"session envelope missing object field: {field}")
    return f".aios/invocations/{rel}", payload


def append_praxis_block(root: Path, contract: Contract, dispatch_id: str, repo: str, agent: str, reason: str, errors: list[str] | None = None) -> dict[str, Any]:
    append_event(
        root,
        {
            "event": "held",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "reason": reason,
            "praxis_errors": errors or [],
            "status": "held",
        },
    )
    return {
        "ok": False,
        "dispatch_id": dispatch_id,
        "repo": repo,
        "status": "held",
        "reason": reason,
        "praxis_errors": errors or [],
    }


def append_policy_block(root: Path, contract: Contract, dispatch_id: str, repo: str, agent: str, policy: dict[str, Any]) -> dict[str, Any]:
    decision = str(policy.get("decision"))
    event = "escalated" if decision == "escalate" else "held" if decision == "hold" else "stopped"
    status = event
    append_event(
        root,
        {
            "event": event,
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "reason": f"action_policy_{decision}",
            "policy": policy,
            "status": status,
        },
    )
    return {
        "ok": False,
        "dispatch_id": dispatch_id,
        "repo": repo,
        "status": status,
        "policy": policy,
    }


def repo_aliases(repo: str) -> set[str]:
    aliases = {
        "hivemind": {"hivemind", "hive mind", "hive_mind", "hive"},
        "memoryOS": {"memoryos", "memory os", "memory_os"},
        "CapabilityOS": {"capabilityos", "capability os", "capability_os"},
        "GenesisOS": {"genesisos", "genesis os", "genesis_os", "genesis"},
        "myworld": {"myworld", "my world", "control plane"},
    }
    return aliases.get(repo, {repo.lower()})


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def repo_matches_label(repo: str, label: str) -> bool:
    normalized = normalize_label(label)
    return normalized in repo_aliases(repo)


def bullet_lines(text: str) -> list[str]:
    values: list[str] = []
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            if current:
                values.append(current)
            current = stripped[2:].strip().strip("`")
        elif current and raw.startswith((" ", "\t")):
            current = f"{current} {stripped}".strip()
        elif current:
            values.append(current)
            current = None
    if current:
        values.append(current)
    return values


def section_after_any_heading(body: str, headings: list[str]) -> str:
    for heading in headings:
        section = section_after_heading(body, heading)
        if section:
            return section
    return ""


def extract_must_produce(contract: Contract, repo: str) -> list[str]:
    section = section_after_any_heading(contract.body, ["Per-OS Responsibility", "Responsibilities"])
    if not section:
        return []

    # Legacy shape: "### Hive Mind" followed by "must_produce:" bullets.
    for match in re.finditer(r"^###\s+(.+?)\s*$", section, flags=re.MULTILINE):
        label = match.group(1).strip()
        start = match.end()
        next_match = re.search(r"^###\s+", section[start:], flags=re.MULTILINE)
        block = section[start : start + next_match.start()] if next_match else section[start:]
        if not repo_matches_label(repo, label):
            continue
        marker = re.search(r"^must_produce:\s*$", block, flags=re.MULTILINE)
        return bullet_lines(block[marker.end() :] if marker else block)

    # Compact shape: "- **capabilityos.must_produce**: item, item, ..."
    for raw in section.splitlines():
        stripped = raw.strip()
        match = re.match(r"-\s+\*\*(.+?)\.must_produce\*\*:\s*(.+)", stripped, flags=re.IGNORECASE)
        if match and repo_matches_label(repo, match.group(1)):
            return [match.group(2).strip()]
    return []


def cmd_create(args: argparse.Namespace) -> int:
    root = repo_root()
    contract = read_contract(Path(args.contract))
    dispatch_id = args.dispatch_id or default_dispatch_id(contract)
    if dispatch_created(root, dispatch_id) and not args.force:
        raise SystemExit(f"dispatch already exists: {dispatch_id} (use --force to append another create event)")
    ensure_layout(root)
    append_event(
        root,
        {
            "event": "created",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "contract_path": contract.path.as_posix(),
            "contract_status": contract.status,
            "goal": contract.goal,
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "forbidden_files": contract.forbidden_files,
            "status": "created",
        },
    )
    print(json.dumps({"ok": True, "dispatch_id": dispatch_id, "status": "created"}, ensure_ascii=False))
    return 0


def build_packet(
    contract: Contract,
    dispatch_id: str,
    repo: str,
    agent: str,
    policy: dict[str, Any] | None = None,
    praxis: dict[str, Any] | None = None,
    praxis_ref: str | None = None,
    session_envelope: dict[str, Any] | None = None,
    session_envelope_ref: str | None = None,
) -> dict[str, Any]:
    verification_commands = [
        {"cwd": command["cwd"], "command": command["line"]}
        for command in extract_verification_commands(contract, repo, repo_root())
    ]
    existing_dirty_baseline = capture_allowed_existing_dirty_baseline(
        repo_root(),
        repo,
        contract.allowed_existing_dirty,
    )
    packet = {
        "schema_version": "aios.dispatch.v1",
        "result_schema_version": "aios.dispatch.result.v1",
        "dispatch_id": dispatch_id,
        "contract_id": contract.contract_id,
        "contract_path": contract.path.as_posix(),
        "contract_status": contract.status,
        "target_repo": repo,
        "agent": agent,
        "goal": contract.goal,
        "created_at": now_iso(),
        "status": "sent",
        "action_policy": policy or evaluate_dispatch_policy(contract, dispatch_id, repo, agent),
        "control_plane": {
            "root": "myworld",
            "rule": "myworld issues packets; child repo agent executes in the owning repo",
        },
        "scope": {
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "allowed_existing_dirty": contract.allowed_existing_dirty,
            "allowed_existing_dirty_baseline": existing_dirty_baseline,
            "forbidden_files": contract.forbidden_files,
        },
        "required_reading": [
            "AGENTS.md",
            "docs/AIOS_NORTHSTAR.md",
            "docs/AIOS_AGENT_PROTOCOL.md",
            "docs/AIOS_SMART_CONTRACT.md",
            "docs/AIOS_WORK_DISPATCH.md",
            "docs/AIOS_BUILD_METHOD.md",
            contract.path.as_posix(),
        ],
        "must_produce": extract_must_produce(contract, repo),
        "verification_commands": verification_commands,
        "result_contract": {
            "schema_version": "aios.dispatch.result.v1",
            "required_fields": [
                "target_repo",
                "dispatch_id",
                "contract_id",
                "status",
                "evidence",
                "stop_conditions_triggered",
            ],
        },
        "return_to": f".aios/outbox/{repo}/{dispatch_id}.{repo}.result.json",
        "stop_conditions": [
            "scope_violation",
            "privacy_violation",
            "missing_required_artifact",
            "test_gate_failed",
            "ownership_conflict",
            "contract_ambiguous",
        ],
    }
    if praxis is not None:
        packet["production_praxis"] = {
            "ref": praxis_ref,
            "schema_version": praxis.get("schema_version"),
            "memory_context": praxis.get("memory_context"),
            "capability_routes": praxis.get("capability_routes"),
            "external_resource_check": praxis.get("external_resource_check"),
            "genesis_reframe": praxis.get("genesis_reframe"),
            "hive_execution_plan": praxis.get("hive_execution_plan"),
            "specialist_assignment": praxis.get("specialist_assignment"),
        }
        packet["stop_conditions"] = [
            *packet["stop_conditions"],
            "memory_context_missing",
            "capability_route_missing",
            "genesis_reframe_missing",
            "external_resource_skipped",
            "specialist_flattening",
            "hive_gate_missing",
        ]
    if session_envelope is not None:
        memory_evidence, _ = extract_memory_retrieval_evidence(repo_root(), session_envelope)
        packet["session_envelope"] = {
            "ref": session_envelope_ref,
            "schema_version": session_envelope.get("schema_version"),
            "envelope_id": session_envelope.get("envelope_id"),
            "invocation_id": session_envelope.get("invocation_id"),
            "goal_hash": session_envelope.get("goal_hash"),
            "role_statuses": session_envelope.get("role_statuses"),
            "degraded_roles": session_envelope.get("degraded_roles"),
            "failed_roles": session_envelope.get("failed_roles"),
            "executor_assignment": session_envelope.get("executor_assignment"),
            "degraded_receipt": session_envelope.get("degraded_receipt"),
            "memory_context": memory_evidence,
        }
        packet["stop_conditions"] = [
            *packet["stop_conditions"],
            "session_envelope_missing",
            "session_envelope_schema_invalid",
            "session_envelope_role_degraded",
        ]
    return packet


def existing_packet_agent(packet_path: Path) -> str | None:
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    agent = payload.get("agent")
    return str(agent) if agent else None


def dispatch_result_evidence(root: Path, dispatch_id: str, repo: str) -> list[str]:
    evidence: list[str] = []
    result_path = root / OUTBOX_DIR / repo / f"{dispatch_id}.{repo}.result.json"
    if result_path.exists():
        evidence.append(result_path.relative_to(root).as_posix())
    for event in load_events(root):
        if (
            event.get("event") == "collected"
            and event.get("dispatch_id") == dispatch_id
            and event.get("repo") == repo
        ):
            result = event.get("result")
            evidence.append(str(result) if result else "dispatch.collected")
    return sorted(set(evidence))


def archive_packet_if_safe(root: Path, dispatch_id: str, repo: str, reason: str, new_dispatch_id: str) -> str | None:
    packet_path = root / INBOX_DIR / repo / f"{dispatch_id}.{repo}.json"
    if not packet_path.exists():
        return None
    archive_dir = root / ".aios" / "archive" / "inbox" / repo
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / packet_path.name
    if archive_path.exists():
        archive_path = archive_dir / f"{dispatch_id}.{repo}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    packet_path.rename(archive_path)
    rel_archive = archive_path.relative_to(root).as_posix()
    append_event(
        root,
        {
            "event": "dispatch_packet_archived",
            "dispatch_id": dispatch_id,
            "repo": repo,
            "packet": rel_archive,
            "reason": reason,
            "new_dispatch_id": new_dispatch_id,
            "status": "archived",
        },
    )
    return rel_archive


def cmd_send(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; run create first or pass --dispatch-id")
    created = dispatch_created(root, dispatch_id)
    if not created:
        raise SystemExit(f"dispatch not found: {dispatch_id}")
    contract = read_contract(Path(str(created["contract_path"])))
    repo = args.repo
    if repo not in REPOS:
        raise SystemExit(f"unsupported repo: {repo}")
    if contract.repos and repo not in contract.repos:
        raise SystemExit(f"{repo} is not in contract scope: {', '.join(contract.repos)}")
    if contract.status not in {"accepted", "closed"} and not args.allow_proposed:
        raise SystemExit(
            f"contract {contract.contract_id} is {contract.status}; operator acceptance required before send"
        )
    ensure_layout(root)
    policy = (
        {
            "schema_version": "aios.action_policy.v1",
            "decision": "allow",
            "allowed_to_execute": True,
            "required_checkpoint": False,
            "reason_codes": ["allow_proposed_test_bypass"],
        }
        if args.allow_proposed
        else evaluate_dispatch_policy(contract, dispatch_id, repo, args.agent)
    )
    if policy["decision"] != "allow":
        blocked = append_policy_block(root, contract, dispatch_id, repo, args.agent, policy)
        print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    praxis_payload = None
    praxis_ref = None
    session_envelope_payload = None
    session_envelope_ref = None
    if args.praxis:
        praxis_path = Path(args.praxis)
        try:
            praxis_payload = load_praxis_payload(praxis_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "praxis_unreadable", [str(exc)])
            print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        errors = validate_praxis(praxis_payload)
        if errors:
            blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "praxis_invalid", errors)
            print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        praxis_ref = praxis_path.as_posix()
    elif contract_requires_praxis(contract):
        blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "praxis_required_missing", ["praxis_required_missing"])
        print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    if contract_requires_session_envelope(contract) and not getattr(args, "session_envelope", None):
        blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "session_envelope_required_missing", ["session_envelope_required_missing"])
        print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    if getattr(args, "session_envelope", None):
        try:
            session_envelope_ref, session_envelope_payload = load_session_envelope(root, args.session_envelope)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "session_envelope_invalid", [str(exc)])
            print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        envelope_errors = validate_session_envelope_for_dispatch(root, session_envelope_payload)
        if envelope_errors:
            blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "session_envelope_role_degraded", envelope_errors)
            print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
            return 1
        if contract_requires_memory_retrieval(contract):
            _memory_evidence, memory_errors = extract_memory_retrieval_evidence(root, session_envelope_payload)
            if memory_errors:
                blocked = append_praxis_block(root, contract, dispatch_id, repo, args.agent, "memory_retrieval_required_missing", memory_errors)
                print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
                return 1
    # ASC-0184 — deterministic enforcement preflight: refuse to dispatch a
    # contract whose declared scope would cross a privacy/audit boundary.
    blocking = hook_preflight(root, contract)
    if blocking is not None:
        print(json.dumps({"ok": False, "dispatch_id": dispatch_id, "repo": repo,
                           "blocked_by": "aios_hooks", "decision": blocking},
                          ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    packet = build_packet(
        contract,
        dispatch_id,
        repo,
        args.agent,
        policy=policy,
        praxis=praxis_payload,
        praxis_ref=praxis_ref,
        session_envelope=session_envelope_payload,
        session_envelope_ref=session_envelope_ref,
    )
    packet_path = root / INBOX_DIR / repo / f"{dispatch_id}.{repo}.json"
    if packet_path.exists():
        previous_agent = existing_packet_agent(packet_path)
        rel_packet = packet_path.relative_to(root).as_posix()
        if previous_agent and previous_agent != args.agent:
            result_evidence = dispatch_result_evidence(root, dispatch_id, repo)
            append_event(
                root,
                {
                    "event": "agent_reassign_blocked" if args.force else "agent_binding_mismatch",
                    "dispatch_id": dispatch_id,
                    "contract_id": contract.contract_id,
                    "repo": repo,
                    "previous_agent": previous_agent,
                    "requested_agent": args.agent,
                    "packet": rel_packet,
                    "reason": "existing_packet_agent_is_immutable",
                    "result_evidence": result_evidence,
                    "status": "blocked",
                },
            )
            detail = (
                f"; result evidence exists ({', '.join(result_evidence)})"
                if result_evidence
                else ""
            )
            raise SystemExit(
                "agent binding mismatch: "
                f"{rel_packet} is assigned to {previous_agent}, requested {args.agent}; "
                "existing packet agent is immutable, create a new dispatch or stop/archive the old one"
                f"{detail}"
            )
        elif not args.force:
            raise SystemExit(f"packet already exists: {packet_path} (use --force to overwrite)")
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(
        root,
        {
            "event": "sent",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": args.agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "sent",
        },
    )
    # ASC-0185 — record the dispatch as a leased job alongside the file drop.
    enqueue_dispatch_job(root, dispatch_id, repo, contract)
    print(
        json.dumps(
            {
                "ok": True,
                "dispatch_id": dispatch_id,
                "repo": repo,
                "packet": packet_path.relative_to(root).as_posix(),
                "return_to": packet["return_to"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_reissue(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id
    new_dispatch_id = args.new_dispatch_id
    repo = args.repo
    if new_dispatch_id == dispatch_id:
        raise SystemExit("--new-dispatch-id must differ from --dispatch-id")
    if repo not in REPOS:
        raise SystemExit(f"unsupported repo: {repo}")
    created = dispatch_created(root, dispatch_id)
    if not created:
        raise SystemExit(f"dispatch not found: {dispatch_id}")
    if dispatch_created(root, new_dispatch_id):
        raise SystemExit(f"new dispatch already exists: {new_dispatch_id}")
    contract = read_contract(Path(str(created["contract_path"])))
    if contract.repos and repo not in contract.repos:
        raise SystemExit(f"{repo} is not in contract scope: {', '.join(contract.repos)}")
    if contract.status not in {"accepted", "closed"}:
        raise SystemExit(f"contract {contract.contract_id} is {contract.status}; operator acceptance required before reissue")
    ensure_layout(root)

    result_evidence = dispatch_result_evidence(root, dispatch_id, repo)
    archived_packet = None
    if not result_evidence:
        archived_packet = archive_packet_if_safe(root, dispatch_id, repo, args.reason, new_dispatch_id)

    append_event(
        root,
        {
            "event": "reissue_requested",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": args.agent,
            "new_dispatch_id": new_dispatch_id,
            "archived_packet": archived_packet,
            "source_result_evidence": result_evidence,
            "reason": args.reason,
            "status": "reissued",
        },
    )
    append_event(
        root,
        {
            "event": "created",
            "dispatch_id": new_dispatch_id,
            "contract_id": contract.contract_id,
            "contract_path": contract.path.as_posix(),
            "contract_status": contract.status,
            "goal": contract.goal,
            "repos": contract.repos,
            "allowed_files": contract.allowed_files,
            "forbidden_files": contract.forbidden_files,
            "status": "created",
            "reissue_of": dispatch_id,
            "reissue_reason": args.reason,
        },
    )
    policy = evaluate_dispatch_policy(contract, new_dispatch_id, repo, args.agent)
    if policy["decision"] != "allow":
        blocked = append_policy_block(root, contract, new_dispatch_id, repo, args.agent, policy)
        print(json.dumps(blocked, ensure_ascii=False, indent=2, sort_keys=True))
        return 1
    packet = build_packet(contract, new_dispatch_id, repo, args.agent, policy=policy)
    packet["reissue"] = {
        "source_dispatch_id": dispatch_id,
        "reason": args.reason,
        "archived_packet": archived_packet,
        "source_result_evidence": result_evidence,
    }
    packet_path = root / INBOX_DIR / repo / f"{new_dispatch_id}.{repo}.json"
    if packet_path.exists():
        raise SystemExit(f"packet already exists: {packet_path}")
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(
        root,
        {
            "event": "sent",
            "dispatch_id": new_dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": args.agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "sent",
            "reissue_of": dispatch_id,
        },
    )
    enqueue_dispatch_job(root, new_dispatch_id, repo, contract)
    print(
        json.dumps(
            {
                "ok": True,
                "dispatch_id": dispatch_id,
                "new_dispatch_id": new_dispatch_id,
                "repo": repo,
                "agent": args.agent,
                "archived_packet": archived_packet,
                "source_result_evidence": result_evidence,
                "packet": packet_path.relative_to(root).as_posix(),
                "return_to": packet["return_to"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def summarize(root: Path) -> dict[str, Any]:
    events = load_events(root)
    dispatches: dict[str, dict[str, Any]] = {}
    for event in events:
        dispatch_id = event.get("dispatch_id")
        if not dispatch_id:
            continue
        row = dispatches.setdefault(str(dispatch_id), {"dispatch_id": dispatch_id, "events": 0, "sent": [], "collected": []})
        row["events"] += 1
        if event.get("event") == "created":
            row.update(
                {
                    "contract_id": event.get("contract_id"),
                    "contract_path": event.get("contract_path"),
                    "contract_status": event.get("contract_status"),
                    "goal": event.get("goal"),
                    "status": event.get("status"),
                }
            )
        elif event.get("event") == "sent":
            row["sent"].append(event.get("repo"))
            row["status"] = "sent"
        elif event.get("event") == "collected":
            row["collected"].append(event.get("repo"))
            row["status"] = "collected"
        elif event.get("event") in {"running", "watched"}:
            row["status"] = event.get("status")
            row["repo"] = event.get("repo")
        elif event.get("event") in TERMINAL_STATES:
            row["status"] = event.get("event")
            row["reason"] = event.get("reason")
        elif event.get("event") == "stopped":
            row["status"] = "stopped"
            row["reason"] = event.get("reason")
    inbox_counts = {repo: len(list((root / INBOX_DIR / repo).glob("*.json"))) for repo in REPOS}
    outbox_counts = {repo: len(list((root / OUTBOX_DIR / repo).glob("*.json"))) for repo in REPOS}
    return {
        "dispatches": list(dispatches.values()),
        "inbox": inbox_counts,
        "outbox": outbox_counts,
        "runtime_profile": runtime_profile_state(root),
    }


def cmd_status(args: argparse.Namespace) -> int:
    root = repo_root()
    data = summarize(root)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    profile = data["runtime_profile"]
    profile_line = f"runtime_profile={profile['profile']} live_child_execution_blocked={profile['live_child_execution_blocked']}"
    if not data["dispatches"]:
        print("No dispatches.")
        print(profile_line)
        return 0
    for row in data["dispatches"]:
        sent = ",".join(str(repo) for repo in row.get("sent") or []) or "-"
        collected = ",".join(str(repo) for repo in row.get("collected") or []) or "-"
        print(f"{row['dispatch_id']}: {row.get('status', 'unknown')} contract={row.get('contract_id')} sent={sent} collected={collected}")
    print(f"inbox={data['inbox']} outbox={data['outbox']}")
    print(profile_line)
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    root = repo_root()
    profile_cmd = getattr(args, "profile_cmd", None) or "show"
    if profile_cmd == "set":
        write_runtime_profile(root, args.profile, args.allow_live_child_execution)
        print(json.dumps({"ok": True, **runtime_profile_state(root)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if profile_cmd == "clear":
        (root / RUNTIME_PROFILE_FILE).unlink(missing_ok=True)
        print(json.dumps({"ok": True, **runtime_profile_state(root)}, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps(runtime_profile_state(root), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    root = repo_root()
    ensure_layout(root)
    repos = [args.repo] if args.repo else list(REPOS)
    already = {
        (str(event.get("repo")), str(event.get("result")))
        for event in load_events(root)
        if event.get("event") == "collected"
    }
    collected = []
    for repo in repos:
        for path in sorted((root / OUTBOX_DIR / repo).glob("*.json")):
            rel = path.relative_to(root).as_posix()
            if (repo, rel) in already:
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"invalid result JSON: {rel}: {exc}") from exc
            expected_dispatch_id = path.name.removesuffix(f".{repo}.result.json")
            errors = validate_result_packet(payload, repo, expected_dispatch_id)
            if errors:
                raise SystemExit(f"malformed result packet: {rel}: {', '.join(errors)}")
            dispatch_id = str(payload.get("dispatch_id") or path.stem.split(".", 1)[0])
            append_event(
                root,
                {
                    "event": "collected",
                    "dispatch_id": dispatch_id,
                    "repo": repo,
                    "result": rel,
                    "result_status": payload.get("status"),
                    "status": "collected",
                },
            )
            already.add((repo, rel))
            collected.append({"repo": repo, "path": rel, "status": payload.get("status")})
    print(json.dumps({"ok": True, "collected": collected}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def validate_result_packet(payload: dict[str, Any], repo: str, expected_dispatch_id: str | None = None) -> list[str]:
    if payload.get("schema_version") != "aios.dispatch.result.v1":
        return []
    required = ["target_repo", "dispatch_id", "contract_id", "status", "evidence", "stop_conditions_triggered"]
    errors = [f"missing {field}" for field in required if field not in payload]
    if payload.get("target_repo") != repo:
        errors.append(f"target_repo {payload.get('target_repo')} != {repo}")
    if expected_dispatch_id and payload.get("dispatch_id") != expected_dispatch_id:
        errors.append(f"dispatch_id {payload.get('dispatch_id')} != {expected_dispatch_id}")
    if not isinstance(payload.get("evidence"), list):
        errors.append("evidence must be a list")
    if not isinstance(payload.get("stop_conditions_triggered"), list):
        errors.append("stop_conditions_triggered must be a list")
    return errors


def append_transition(root: Path, dispatch_id: str, state: str, reason: str) -> None:
    append_event(
        root,
        {
            "event": state,
            "dispatch_id": dispatch_id,
            "reason": reason,
            "status": state,
        },
    )


def maybe_write_closeout_memory(root: Path, dispatch_id: str, reason: str, disabled: bool = False) -> dict[str, Any]:
    if disabled:
        result = {"ok": True, "skipped": True, "reason": "disabled_by_flag"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    created = dispatch_created(root, dispatch_id)
    if not created:
        result = {"ok": False, "skipped": True, "reason": "missing_created_event"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    try:
        contract = read_contract(Path(str(created["contract_path"])))
    except (OSError, SystemExit) as exc:
        result = {"ok": False, "skipped": True, "reason": f"contract_unreadable:{exc}"}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    if contract.status != "closed":
        result = {
            "ok": True,
            "skipped": True,
            "reason": f"contract_status_{contract.status}",
            "contract_id": contract.contract_id,
        }
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    emitter = root / "scripts" / "aios_contract_to_memory.py"
    memoryos_dir = root / "memoryOS"
    if not emitter.exists() or not memoryos_dir.exists():
        result = {
            "ok": True,
            "skipped": True,
            "reason": "memoryos_or_emitter_missing",
            "contract_id": contract.contract_id,
        }
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
        return result
    emit = subprocess.run(
        [
            sys.executable,
            emitter.as_posix(),
            "emit",
            "--root",
            root.as_posix(),
            "--contract",
            contract.contract_id,
            "--closed-by",
            "aios_dispatch.release",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if emit.returncode != 0:
        result = {"ok": False, "skipped": True, "reason": "emit_failed", "stderr": emit.stderr[-500:]}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, "contract_id": contract.contract_id, **result})
        return result
    ingest = subprocess.run(
        [sys.executable, "-m", "memoryos.cli", "--root", memoryos_dir.as_posix(), "ingest-contract-closeout", "--json"],
        input=emit.stdout,
        cwd=memoryos_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    if ingest.returncode != 0:
        result = {"ok": False, "skipped": True, "reason": "ingest_failed", "stderr": ingest.stderr[-500:]}
        append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, "contract_id": contract.contract_id, **result})
        return result
    try:
        payload = json.loads(ingest.stdout)
    except json.JSONDecodeError:
        payload = {}
    result = {
        "ok": True,
        "skipped": False,
        "contract_id": contract.contract_id,
        "draft_id": payload.get("draft_id"),
        "written": payload.get("written"),
        "reason": reason,
    }
    append_event(root, {"event": "memory_writeback", "dispatch_id": dispatch_id, **result})
    return result


def strict_close_release_check(root: Path, dispatch_id: str, args: argparse.Namespace) -> dict[str, Any] | None:
    if getattr(args, "operator_override_strict_close", False):
        if not args.reason:
            return {"ok": False, "reason": "override_without_reason"}
        append_event(
            root,
            {
                "event": "strict_close_override",
                "dispatch_id": dispatch_id,
                "reason": args.reason,
                "status": "released",
            },
        )
        return None
    created = dispatch_created(root, dispatch_id)
    if not created:
        return None
    try:
        contract = read_contract(Path(str(created["contract_path"])))
    except (OSError, SystemExit):
        return None
    if contract.status != "closed":
        return None
    payload = evaluate_contract(contract.path, root=root)
    if int(payload.get("unmet", 0)) <= 0:
        return None
    close_type = getattr(args, "close_type", None)
    followup = getattr(args, "followup_asc", None)
    if close_type not in CLOSE_TYPES:
        return {
            "ok": False,
            "reason": "strict_close_unclassified",
            "contract_id": contract.contract_id,
            "recommended_close_type": payload.get("recommended_close_type"),
            "unmet": payload.get("unmet"),
        }
    if close_type == "closed_partial_with_followup" and not (followup and re.match(r"ASC-\d{4}$", followup)):
        return {
            "ok": False,
            "reason": "strict_close_followup_required",
            "contract_id": contract.contract_id,
            "close_type": close_type,
        }
    append_event(
        root,
        {
            "event": "strict_close_classified",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "close_type": close_type,
            "followup_asc": followup,
            "unmet": payload.get("unmet"),
            "manual": payload.get("manual"),
            "status": "released",
        },
    )
    return None


def import_genesis_challenge(root: Path):
    genesis_root = (root / "GenesisOS").resolve()
    if not (genesis_root / "genesisos").exists():
        genesis_root = (Path(__file__).resolve().parents[1] / "GenesisOS").resolve()
    package_dir = genesis_root / "genesisos"
    if genesis_root.as_posix() not in sys.path:
        sys.path.insert(0, genesis_root.as_posix())
    loaded = sys.modules.get("genesisos")
    loaded_paths = [Path(path).resolve() for path in getattr(loaded, "__path__", [])] if loaded else []
    if loaded and package_dir not in loaded_paths:
        for name in list(sys.modules):
            if name == "genesisos" or name.startswith("genesisos."):
                del sys.modules[name]
    from genesisos.challenge import run  # type: ignore

    return run


def genesis_challenge_release_check(root: Path, dispatch_id: str, args: argparse.Namespace) -> dict[str, Any] | None:
    if getattr(args, "without_genesis_challenge", False):
        append_event(
            root,
            {
                "event": "genesis_challenge_skipped",
                "dispatch_id": dispatch_id,
                "reason": args.reason,
                "status": "released",
            },
        )
        return None
    created = dispatch_created(root, dispatch_id)
    if not created:
        return None
    contract_path = Path(str(created["contract_path"]))
    registry_root = (root / "docs" / "contracts").resolve()
    try:
        resolved_contract_path = contract_path.resolve()
    except OSError as exc:
        return {"ok": False, "reason": "genesis_challenge_failed", "error": str(exc)}
    try:
        resolved_contract_path.relative_to(registry_root)
    except ValueError:
        append_event(
            root,
            {
                "event": "genesis_challenge_skipped",
                "dispatch_id": dispatch_id,
                "reason": "contract_outside_registry",
                "contract_path": contract_path.as_posix(),
                "status": "released",
            },
        )
        return None
    contract = read_contract(contract_path)
    if contract.status not in {"accepted", "closed"}:
        append_event(
            root,
            {
                "event": "genesis_challenge_skipped",
                "dispatch_id": dispatch_id,
                "contract_id": contract.contract_id,
                "reason": "contract_not_accepted",
                "status": "released",
            },
        )
        return None
    try:
        run_challenge = import_genesis_challenge(root)
        report = run_challenge(contract.contract_id, myworld_root=root)
    except (OSError, ValueError, KeyError, ImportError, FileNotFoundError) as exc:
        return {"ok": False, "reason": "genesis_challenge_failed", "error": str(exc)}
    append_event(
        root,
        {
            "event": "genesis_challenge",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "risk_level": report.get("risk_level"),
            "soft_block": report.get("soft_block"),
            "recommendation": report.get("recommendation"),
            "report": report.get("output_path"),
            "status": "released" if not report.get("soft_block") else "held",
        },
    )
    if not report.get("soft_block"):
        return None
    if getattr(args, "operator_override_genesis_block", False):
        if not args.reason:
            return {"ok": False, "reason": "genesis_override_without_reason", "challenge": report}
        append_event(
            root,
            {
                "event": "genesis_challenge_override",
                "dispatch_id": dispatch_id,
                "contract_id": contract.contract_id,
                "reason": args.reason,
                "challenge": report.get("output_path"),
                "status": "released",
            },
        )
        return None
    return {"ok": False, "reason": "genesis_challenge_soft_block", "challenge": report}


def recover_escalated_release(root: Path, dispatch_id: str, reason: str) -> dict[str, Any] | None:
    last_event = latest_dispatch_event(root, dispatch_id)
    advisory_events = {"authority_check", "genesis_challenge", "genesis_challenge_skipped", "genesis_challenge_override"}
    if last_event and last_event.get("event") in advisory_events:
        for event in reversed(load_events(root)):
            if event.get("dispatch_id") == dispatch_id and event.get("event") not in advisory_events:
                last_event = event
                break
    if not last_event or last_event.get("event") != "escalated":
        return None
    created = dispatch_created(root, dispatch_id)
    if not created:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "reason": "missing_created_event",
                "status": "released",
            },
        )
        return {"ok": False, "reason": "missing_created_event"}

    repo = str(last_event.get("repo") or "")
    agent = str(last_event.get("agent") or "codex")
    if repo not in REPOS:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "reason": f"unsupported_repo:{repo}",
                "status": "released",
            },
        )
        return {"ok": False, "reason": f"unsupported_repo:{repo}"}

    try:
        contract = read_contract(Path(str(created["contract_path"])))
        if contract.repos and repo not in contract.repos:
            raise ValueError(f"{repo} is not in contract scope: {', '.join(contract.repos)}")
        if contract.status not in {"accepted", "closed"}:
            raise ValueError(f"contract {contract.contract_id} is {contract.status}")
        packet_path = root / INBOX_DIR / repo / f"{dispatch_id}.{repo}.json"
        if packet_path.exists():
            return {"ok": True, "skipped": True, "reason": "packet_already_exists", "repo": repo}
        policy = {
            "schema_version": "aios.action_policy.v1",
            "decision": "allow",
            "allowed_to_execute": True,
            "required_checkpoint": False,
            "reason_codes": ["operator_override_after_escalation"],
            "operator_override": True,
            "override_reason": reason,
            "previous_policy": last_event.get("policy"),
        }
        packet = build_packet(contract, dispatch_id, repo, agent, policy=policy)
        packet["operator_override"] = True
        packet["override_reason"] = reason
        packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, KeyError, ValueError) as exc:
        append_event(
            root,
            {
                "event": "release_recovery_failed",
                "dispatch_id": dispatch_id,
                "repo": repo,
                "agent": agent,
                "reason": str(exc),
                "status": "released",
            },
        )
        return {"ok": False, "reason": str(exc), "repo": repo}

    append_event(
        root,
        {
            "event": "dispatch.recovery",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "reason": reason,
            "operator_override": True,
            "status": "sent",
        },
    )
    append_event(
        root,
        {
            "event": "sent",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": repo,
            "agent": agent,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "sent",
        },
    )
    return {"ok": True, "repo": repo, "packet": packet_path.relative_to(root).as_posix()}


def cmd_transition(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; pass --dispatch-id")
    authority_payload = None
    if args.state == "released":
        genesis_error = genesis_challenge_release_check(root, dispatch_id, args)
        if genesis_error:
            append_event(
                root,
                {
                    "event": "genesis_challenge_blocked",
                    "dispatch_id": dispatch_id,
                    "reason": genesis_error["reason"],
                    "status": "held",
                    "genesis_challenge": genesis_error,
                },
            )
            print(json.dumps({"ok": False, "dispatch_id": dispatch_id, "status": "held", "genesis_challenge": genesis_error}, ensure_ascii=False))
            return 1
        strict_error = strict_close_release_check(root, dispatch_id, args)
        if strict_error:
            append_event(
                root,
                {
                    "event": "strict_close_blocked",
                    "dispatch_id": dispatch_id,
                    "reason": strict_error["reason"],
                    "status": "held",
                    "strict_close": strict_error,
                },
            )
            print(json.dumps({"ok": False, "dispatch_id": dispatch_id, "status": "held", "strict_close": strict_error}, ensure_ascii=False))
            return 1
    recovery = None
    if args.state == "released":
        agent = getattr(args, "agent", None) or current_agent_id()
        authority = verify_authority(agent, "release_dispatch")
        override = bool(getattr(args, "override_authority", False))
        audit_authority(root, authority, override=override, reason=args.reason)
        authority_payload = {**authority.to_json(), "override": override}
        append_event(
            root,
            {
                "event": "authority_check",
                "dispatch_id": dispatch_id,
                "agent": agent,
                "action": "release_dispatch",
                "authority": authority_payload,
                "status": "released" if authority.allowed or override or authority.soft_fail else "authority_soft_denied",
            },
        )
        if not (authority.allowed or override or authority.soft_fail):
            print(json.dumps(
                {
                    "ok": False,
                    "dispatch_id": dispatch_id,
                    "status": "authority_denied",
                    "recovery": None,
                    "memory_writeback": None,
                    "authority": authority_payload,
                },
                ensure_ascii=False,
            ))
            return 1
        recovery = recover_escalated_release(root, dispatch_id, args.reason)
    append_transition(root, dispatch_id, args.state, args.reason)
    memory_writeback = None
    if args.state == "released":
        memory_writeback = maybe_write_closeout_memory(
            root,
            dispatch_id,
            args.reason,
            disabled=getattr(args, "no_memory_write", False),
        )
    print(json.dumps(
        {
            "ok": True,
            "dispatch_id": dispatch_id,
            "status": args.state,
            "recovery": recovery,
            "memory_writeback": memory_writeback,
            "authority": authority_payload,
        },
        ensure_ascii=False,
    ))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    root = repo_root()
    dispatch_id = args.dispatch_id or latest_dispatch_id(root)
    if not dispatch_id:
        raise SystemExit("no dispatch found; pass --dispatch-id")
    append_event(
        root,
        {
            "event": "stopped",
            "dispatch_id": dispatch_id,
            "reason": args.reason,
            "status": "stopped",
        },
    )
    print(json.dumps({"ok": True, "dispatch_id": dispatch_id, "status": "stopped"}, ensure_ascii=False))
    return 0


def section_after_heading(body: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", body, flags=re.MULTILINE)
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_heading.start()] if next_heading else rest


def bash_blocks(text: str) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", text, flags=re.DOTALL)


def repo_matches_cwd(repo: str, cwd: Path | None, root: Path) -> bool:
    if repo == "myworld":
        return cwd is None or cwd.resolve() == root.resolve() or cwd.name == "myworld"
    return cwd is not None and repo in cwd.parts


def safe_argv(command: str) -> list[str]:
    if any(token in command for token in SHELL_META):
        raise ValueError(f"unsafe shell token in command: {command}")
    argv = shlex.split(command)
    if not argv:
        raise ValueError("empty command")
    executable = Path(argv[0]).name
    if executable == "git":
        if len(argv) >= 3 and argv[1:3] == ["diff", "--check"]:
            return argv
        raise ValueError(f"unsupported git verification command: {command}")
    if executable not in {"python", "python3", "pytest", "bash", "sleep"}:
        raise ValueError(f"unsupported executable in verification command: {argv[0]}")
    return argv


def extract_verification_commands(contract: Contract, repo: str, root: Path) -> list[dict[str, Any]]:
    gate = section_after_heading(contract.body, "Verification Gate")
    if not gate:
        return []
    gate = gate.split("Operational smoke equivalent:", 1)[0]
    commands: list[dict[str, Any]] = []
    cwd: Path | None = None
    for block in bash_blocks(gate):
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("cd "):
                target = shlex.split(line)[1]
                cwd = Path(target).expanduser()
                if not cwd.is_absolute():
                    cwd = (root / cwd).resolve()
                continue
            if not repo_matches_cwd(repo, cwd, root):
                continue
            argv = safe_argv(line)
            commands.append({"argv": argv, "cwd": (cwd or root).as_posix(), "line": line})
    return commands


def bounded_lines(text: str, limit: int = 20) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= limit * 2:
        return lines
    return lines[:limit] + ["..."] + lines[-limit:]


def cmd_watch(args: argparse.Namespace) -> int:
    if not args.once:
        raise SystemExit("watch V1 is on-demand only; pass --once")
    root = repo_root()
    ensure_layout(root)
    packet_path = (
        root / INBOX_DIR / args.repo / f"{args.dispatch_id}.{args.repo}.json"
        if args.dispatch_id
        else latest_packet(root, args.repo)
    )
    if args.dispatch_id and (not packet_path or not packet_path.exists()):
        archived_packet = root / ".aios" / "archive" / "inbox" / args.repo / f"{args.dispatch_id}.{args.repo}.json"
        if archived_packet.exists():
            packet_path = archived_packet
    if not packet_path or not packet_path.exists():
        raise SystemExit(f"packet not found for repo {args.repo}")
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    dispatch_id = str(packet["dispatch_id"])
    contract = read_contract(Path(str(packet["contract_path"])))
    preflight_stop_conditions: list[str] = []
    try:
        commands = extract_verification_commands(contract, args.repo, root)
    except ValueError as exc:
        commands = []
        preflight_stop_conditions.append("arbitrary_command_execution")
        preflight_error = str(exc)
    else:
        preflight_error = ""
    append_event(
        root,
        {
            "event": "running",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": args.repo,
            "packet": packet_path.relative_to(root).as_posix(),
            "status": "running",
        },
    )

    log_path = root / LOG_DIR / f"{dispatch_id}.{args.repo}.log"
    evidence: list[dict[str, Any]] = []
    full_log: list[str] = []
    stop_conditions: list[str] = list(preflight_stop_conditions)
    status = "passed"
    if preflight_error:
        status = "held"
        full_log.append(preflight_error)
    elif not commands:
        status = "held"
        stop_conditions.append("missing_verification_command")

    for command in commands:
        completed = subprocess.run(
            command["argv"],
            cwd=command["cwd"],
            text=True,
            capture_output=True,
        )
        full_log.extend(
            [
                f"$ cd {command['cwd']}",
                f"$ {command['line']}",
                f"[exit {completed.returncode}]",
                completed.stdout,
                completed.stderr,
            ]
        )
        evidence.append(
            {
                "cwd": command["cwd"],
                "command": command["line"],
                "returncode": completed.returncode,
                "stdout_summary": bounded_lines(completed.stdout),
                "stderr_summary": bounded_lines(completed.stderr),
            }
        )
        if completed.returncode != 0:
            status = "failed"
            stop_conditions.append("test_gate_failed")
            break

    log_path.write_text("\n".join(full_log), encoding="utf-8")
    result = {
        "schema_version": "aios.dispatch.result.v1",
        "target_repo": args.repo,
        "dispatch_id": dispatch_id,
        "contract_id": contract.contract_id,
        "status": status,
        "executed_at": now_iso(),
        "agent_assigned": packet.get("agent"),
        "agent_executed": "aios_dispatch.watch",
        "executed_reason": "verification_gate",
        "packet": packet_path.relative_to(root).as_posix(),
        "session_envelope": packet.get("session_envelope"),
        "evidence": evidence,
        "log_path": log_path.relative_to(root).as_posix(),
        "stop_conditions_triggered": stop_conditions,
    }
    result_path = root / OUTBOX_DIR / args.repo / f"{dispatch_id}.{args.repo}.result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(
        root,
        {
            "event": "watched",
            "dispatch_id": dispatch_id,
            "contract_id": contract.contract_id,
            "repo": args.repo,
            "result": result_path.relative_to(root).as_posix(),
            "result_status": status,
            "status": status,
        },
    )
    print(json.dumps({"ok": status == "passed", "dispatch_id": dispatch_id, "repo": args.repo, "status": status, "result": result_path.relative_to(root).as_posix()}, ensure_ascii=False))
    return 0 if status == "passed" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS control-plane dispatch CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="create a dispatch from a smart contract")
    create.add_argument("contract")
    create.add_argument("--dispatch-id")
    create.add_argument("--force", action="store_true")
    create.set_defaults(func=cmd_create)

    send = sub.add_parser("send", help="write a work packet to a child repo inbox")
    send.add_argument("--repo", required=True, choices=REPOS)
    send.add_argument("--agent", default="codex")
    send.add_argument("--dispatch-id")
    send.add_argument("--praxis", help="validated AIOS production praxis envelope JSON to attach to the packet")
    send.add_argument("--session-envelope", help="AIOS session_envelope.json to bind into the dispatch packet")
    send.add_argument("--allow-proposed", action="store_true", help="testing only; bypass accepted-contract guard")
    send.add_argument("--force", action="store_true")
    send.set_defaults(func=cmd_send)

    reissue = sub.add_parser("reissue", help="archive/cancel a stale dispatch packet and issue a new dispatch id")
    reissue.add_argument("--dispatch-id", required=True)
    reissue.add_argument("--repo", required=True, choices=REPOS)
    reissue.add_argument("--agent", required=True)
    reissue.add_argument("--new-dispatch-id", required=True)
    reissue.add_argument("--reason", required=True)
    reissue.set_defaults(func=cmd_reissue)

    status = sub.add_parser("status", help="show dispatch state")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    profile = sub.add_parser("profile", help="show or set the build/runtime isolation profile")
    profile.set_defaults(func=cmd_profile, profile_cmd="show")
    profile_sub = profile.add_subparsers(dest="profile_cmd")
    p_show = profile_sub.add_parser("show", help="print the active runtime profile")
    p_show.set_defaults(func=cmd_profile, profile_cmd="show")
    p_set = profile_sub.add_parser("set", help="write a local runtime profile under .aios/")
    p_set.add_argument("--profile", required=True, choices=RUNTIME_PROFILES)
    p_set.add_argument("--allow-live-child-execution", action="store_true",
                       help="explicitly permit live child execution under build_control")
    p_set.set_defaults(func=cmd_profile, profile_cmd="set")
    p_clear = profile_sub.add_parser("clear", help="remove the local runtime profile (revert to default)")
    p_clear.set_defaults(func=cmd_profile, profile_cmd="clear")

    collect = sub.add_parser("collect", help="collect result packets from outboxes")
    collect.add_argument("--repo", choices=REPOS)
    collect.set_defaults(func=cmd_collect)

    stop = sub.add_parser("stop", help="mark a dispatch stopped")
    stop.add_argument("--dispatch-id")
    stop.add_argument("--reason", default="operator_checkpoint")
    stop.set_defaults(func=cmd_stop)

    for command_name, state in STATE_COMMANDS.items():
        transition = sub.add_parser(command_name, help=f"mark a dispatch {state}")
        transition.add_argument("--dispatch-id")
        transition.add_argument("--reason", default=f"operator_{state}")
        if command_name == "release":
            transition.add_argument("--agent", default=current_agent_id(), help="agent id requesting release")
            transition.add_argument("--override-authority", action="store_true", help="record authority override for V1 soft-fail")
            transition.add_argument("--no-memory-write", action="store_true", help="skip closed-contract MemoryOS draft writeback")
            transition.add_argument("--close-type", choices=sorted(CLOSE_TYPES), help="strict close classification when unmet criteria remain")
            transition.add_argument("--followup-asc", help="required for closed_partial_with_followup")
            transition.add_argument("--operator-override-strict-close", action="store_true", help="emergency bypass for strict close checks; requires reason")
            transition.add_argument("--without-genesis-challenge", action="store_true", help="skip GenesisOS pre-close challenge with explicit event")
            transition.add_argument("--operator-override-genesis-block", action="store_true", help="override GenesisOS soft-block; requires reason")
        transition.set_defaults(func=cmd_transition, state=state)

    watch = sub.add_parser("watch", help="run one packet's verification gate and write a result packet")
    watch.add_argument("--repo", required=True, choices=REPOS)
    watch.add_argument("--dispatch-id")
    watch.add_argument("--once", action="store_true")
    watch.set_defaults(func=cmd_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except BrokenPipeError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
