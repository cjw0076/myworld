#!/usr/bin/env python3
"""AIOS control-plane monitor.

The monitor reads MyWorld control-plane artifacts and reports drift. It does
not execute child repo work and does not edit child repo files.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOS = ("hivemind", "memoryOS", "CapabilityOS", "GenesisOS")
STATE_LOG = Path(".aios/state/dispatches.jsonl")
MONITOR_LOG = Path(".aios/state/monitor.jsonl")
MONITOR_LATEST = Path(".aios/state/monitor.latest.json")
MONITOR_ASSESSMENT_LOG = Path(".aios/state/monitor_assessments.jsonl")
MONITOR_ASSESSMENT_LATEST = Path(".aios/state/monitor_assessment.latest.json")
MONITOR_EVENTS = Path(".aios/state/monitor_events.jsonl")
MONITOR_PID = Path(".aios/run/aios_monitor.pid")
MONITOR_STOP = Path(".aios/run/aios_monitor.stop")
RECONCILIATIONS_PATH = Path("docs/AIOS_MONITOR_RECONCILIATIONS.json")
STATUS_ORDER = {
    "proposed": 0,
    "accepted": 1,
    "active": 2,
    "closed": 3,
    "superseded": 3,
}
SEVERITY_ORDER = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
ALERT_RULES = {
    "dispatch_results_pending": {
        "severity": "high",
        "owner": "myworld",
        "action": "collect_result_or_run_watcher",
        "reason": "A sent dispatch has no collected result packet for at least one target repo.",
    },
    "dispatch_contract_path_missing": {
        "severity": "high",
        "owner": "myworld",
        "action": "escalate_missing_contract_artifact",
        "reason": "A dispatch references a missing contract path, so the control-plane audit trail is incomplete.",
    },
    "dispatch_contract_status_stale": {
        "severity": "medium",
        "owner": "myworld",
        "action": "review_or_reconcile_exact_dispatch_drift",
        "reason": "A dispatch recorded an older contract status than the current contract file.",
    },
    "repo_dirty": {
        "severity": "medium",
        "owner": "alert_repo",
        "action": "hold_for_repo_owner_triage",
        "reason": "A child repo has uncommitted changes that need owner review before new work is stacked on it.",
    },
    "generated_cache_present": {
        "severity": "low",
        "owner": "alert_repo",
        "action": "clean_generated_cache_or_ignore_with_contract",
        "reason": "Generated cache artifacts are visible in repo status and may leak into durable records.",
    },
    "orphan_dirty_post_failure": {
        "severity": "high",
        "owner": "alert_repo",
        "action": "commit_orphan_work_or_reset",
        "reason": "A child watcher result detected work left in a dirty repo after a failed agent attempt.",
    },
    "dispatch_state_malformed_jsonl": {
        "severity": "medium",
        "owner": "myworld",
        "action": "repair_or_reconcile_dispatch_state_log",
        "reason": "The dispatch event log contains malformed JSONL; monitor skipped the bad line but the audit trail needs repair.",
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    current_key: str | None = None
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data[current_key]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if sep:
            current_key = key.strip()
            data[current_key] = value.strip()
    return data


def load_events(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    path = root / STATE_LOG
    if not path.exists():
        return [], []
    events: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            alerts.append(
                {
                    "code": "dispatch_state_malformed_jsonl",
                    "path": STATE_LOG.as_posix(),
                    "line": line_number,
                    "error": exc.msg,
                }
            )
    return events, alerts


def load_reconciliations(root: Path) -> list[dict[str, Any]]:
    path = root / RECONCILIATIONS_PATH
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("reconciliations", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def reconciliation_matches(alert: dict[str, Any], entry: dict[str, Any]) -> bool:
    match = entry.get("match")
    if not isinstance(match, dict) or not match:
        return False
    for key, expected in match.items():
        if str(alert.get(key)) != str(expected):
            return False
    return True


def reconcile_alerts(alerts: list[dict[str, Any]], reconciliations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    remaining: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []
    for alert in alerts:
        matched = next((entry for entry in reconciliations if reconciliation_matches(alert, entry)), None)
        if matched:
            applied.append(
                {
                    "id": matched.get("id"),
                    "reason": matched.get("reason"),
                    "match": matched.get("match"),
                    "accepted_by": matched.get("accepted_by"),
                    "accepted_at": matched.get("accepted_at"),
                    "authorized_by_contract": matched.get("authorized_by_contract"),
                }
            )
        else:
            remaining.append(alert)
    return remaining, applied


def normalize_dispatch_id(dispatch_id: Any, repo: Any = None) -> str:
    value = str(dispatch_id)
    repo_value = str(repo or "")
    suffixes = [f".{repo_value}"] if repo_value else []
    suffixes.extend(f".{known_repo}" for known_repo in REPOS)
    for suffix in suffixes:
        if suffix != "." and value.endswith(suffix):
            return value[: -len(suffix)]
    return value


def is_expected_status_progression(recorded: str | None, current: str | None) -> bool:
    if not recorded or not current:
        return False
    if recorded == current:
        return True
    if recorded == "accepted" and current == "closed":
        return True
    return STATUS_ORDER.get(current, -1) <= STATUS_ORDER.get(recorded, -1)


def dispatch_summary(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events, alerts = load_events(root)
    rows: dict[str, dict[str, Any]] = {}
    for event in events:
        dispatch_id = normalize_dispatch_id(event.get("dispatch_id"), event.get("repo"))
        if not dispatch_id:
            continue
        row = rows.setdefault(str(dispatch_id), {"dispatch_id": dispatch_id, "sent": [], "collected": []})
        if event.get("event") == "created":
            row.update(
                {
                    "contract_id": event.get("contract_id"),
                    "contract_path": event.get("contract_path"),
                    "recorded_contract_status": event.get("contract_status"),
                    "created_status": event.get("status"),
                }
            )
        elif event.get("event") == "sent":
            row["sent"].append(event.get("repo"))
        elif event.get("event") == "collected":
            row["collected"].append(event.get("repo"))
        elif event.get("event") == "stopped":
            row["stopped"] = True
            row["reason"] = event.get("reason")

    for row in rows.values():
        contract_path_value = str(row.get("contract_path") or "")
        contract_path = root / contract_path_value if contract_path_value else None
        if contract_path is None or not contract_path.is_file():
            frontmatter = {}
            if row.get("recorded_contract_status"):
                alerts.append(
                    {
                        "code": "dispatch_contract_path_missing",
                        "dispatch_id": row["dispatch_id"],
                        "contract_path": contract_path_value,
                    }
                )
        else:
            frontmatter = parse_frontmatter(contract_path)
        current_status = frontmatter.get("status")
        row["current_contract_status"] = current_status
        if (
            current_status
            and row.get("recorded_contract_status")
            and not is_expected_status_progression(str(row.get("recorded_contract_status")), current_status)
        ):
            alerts.append(
                {
                    "code": "dispatch_contract_status_stale",
                    "dispatch_id": row["dispatch_id"],
                    "recorded": row.get("recorded_contract_status"),
                    "current": current_status,
                    "contract_path": row.get("contract_path"),
                }
            )
        sent = set(str(repo) for repo in row.get("sent") or [])
        collected = set(str(repo) for repo in row.get("collected") or [])
        missing = sorted(sent - collected)
        if missing:
            alerts.append({"code": "dispatch_results_pending", "dispatch_id": row["dispatch_id"], "repos": missing})
    return list(rows.values()), alerts


def git_status(root: Path, repo: str) -> dict[str, Any]:
    path = root / repo
    if not path.exists():
        return {"repo": repo, "exists": False, "dirty": False, "entries": []}
    result = subprocess.run(
        ["git", "-C", path.as_posix(), "status", "--short", "--untracked-files=all"],
        text=True,
        capture_output=True,
        check=False,
    )
    entries = [line for line in result.stdout.splitlines() if line.strip()]
    generated = [line for line in entries if "__pycache__" in line or line.endswith(".pyc")]
    non_generated = [line for line in entries if line not in generated]
    return {
        "repo": repo,
        "exists": True,
        "returncode": result.returncode,
        "dirty": bool(non_generated),
        "entries": entries,
        "non_generated_entries": non_generated,
        "generated_cache_entries": generated,
    }


def orphan_result_packets(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    outbox = root / ".aios" / "outbox"
    if not outbox.exists():
        return rows
    for path in sorted(outbox.glob("*/*.result.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not payload.get("orphan_work_detected"):
            continue
        rows.append(
            {
                "repo": str(payload.get("target_repo") or path.parent.name),
                "dispatch_id": payload.get("dispatch_id"),
                "contract_id": payload.get("contract_id"),
                "result": path.relative_to(root).as_posix(),
                "orphan_work_files": payload.get("orphan_work_files") or [],
            }
        )
    return rows


def contract_rows(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((root / "docs/contracts").glob("ASC-*.md")):
        fm = parse_frontmatter(path)
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "contract_id": fm.get("contract_id"),
                "status": fm.get("status"),
                "accepted": fm.get("accepted"),
                "closed": fm.get("closed"),
            }
        )
    return rows


def snapshot(root: Path) -> dict[str, Any]:
    dispatches, alerts = dispatch_summary(root)
    repos = [git_status(root, repo) for repo in REPOS]
    repo_by_name = {repo["repo"]: repo for repo in repos}
    for repo in repos:
        if repo["dirty"]:
            alerts.append({"code": "repo_dirty", "repo": repo["repo"], "entries": repo["entries"]})
        if repo.get("generated_cache_entries"):
            alerts.append(
                {
                    "code": "generated_cache_present",
                    "repo": repo["repo"],
                    "entries": repo["generated_cache_entries"],
                }
            )
    for result in orphan_result_packets(root):
        repo = str(result.get("repo") or "")
        if repo_by_name.get(repo, {}).get("dirty"):
            alerts.append({"code": "orphan_dirty_post_failure", **result})
    reconciliations = load_reconciliations(root)
    alerts, reconciliations_applied = reconcile_alerts(alerts, reconciliations)
    return {
        "schema_version": "aios.monitor.v1",
        "generated_at": now_iso(),
        "contracts": contract_rows(root),
        "dispatches": dispatches,
        "repos": repos,
        "reconciliations_applied": reconciliations_applied,
        "alerts": alerts,
    }


def owner_for_alert(alert: dict[str, Any], rule: dict[str, str]) -> str:
    owner = rule.get("owner", "myworld")
    if owner == "alert_repo":
        return str(alert.get("repo") or "myworld")
    return owner


def assess_alert(alert: dict[str, Any]) -> dict[str, Any]:
    code = str(alert.get("code") or "unknown")
    rule = ALERT_RULES.get(
        code,
        {
            "severity": "medium",
            "owner": "myworld",
            "action": "operator_checkpoint",
            "reason": "Monitor emitted an alert without a specific assessment rule.",
        },
    )
    return {
        "code": code,
        "severity": rule["severity"],
        "owner": owner_for_alert(alert, rule),
        "action": rule["action"],
        "reason": rule["reason"],
        "alert": alert,
    }


def health_from_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "clear"
    worst = max(SEVERITY_ORDER.get(str(finding.get("severity")), 2) for finding in findings)
    if worst >= SEVERITY_ORDER["high"]:
        return "blocked"
    if worst >= SEVERITY_ORDER["medium"]:
        return "attention"
    return "watch"


def prioritized_actions(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not findings:
        return [
            {
                "owner": "myworld",
                "action": "continue_observing",
                "severity": "info",
                "reason": "No active monitor alerts.",
            }
        ]
    seen: set[tuple[str, str]] = set()
    rows: list[dict[str, Any]] = []
    ordered = sorted(
        findings,
        key=lambda item: SEVERITY_ORDER.get(str(item.get("severity")), 2),
        reverse=True,
    )
    for finding in ordered:
        key = (str(finding.get("owner")), str(finding.get("action")))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "owner": finding.get("owner"),
                "action": finding.get("action"),
                "severity": finding.get("severity"),
                "reason": finding.get("reason"),
            }
        )
    return rows


def genesis_critic_advisory(root: Path | None) -> list[dict[str, Any]]:
    if root is None:
        return []
    if not (root / "GenesisOS").exists() or not (root / "docs" / "contracts").exists():
        return []
    try:
        from aios_genesis_critic_dispatch import build_report

        report = build_report(root, limit=25)
    except Exception as exc:  # pragma: no cover - monitor must not fail on advisory import drift.
        return [
            {
                "code": "genesis_critic_unavailable",
                "severity": "info",
                "owner": "GenesisOS",
                "action": "review_genesis_critic_wrapper",
                "reason": f"GenesisOS critic advisory could not run: {exc}",
                "alert": {"code": "genesis_critic_unavailable"},
            }
        ]
    if int(report.get("flagged_count") or 0) <= 0:
        return []
    return [
        {
            "code": "genesis_prompt_prison_advisory",
            "severity": "info",
            "owner": "GenesisOS",
            "action": "review_prompt_prison_escape_vectors",
            "reason": "GenesisOS critic found advisory prompt-prison signatures in open contracts.",
            "alert": {
                "code": "genesis_prompt_prison_advisory",
                "flagged_count": report.get("flagged_count"),
                "scanned_count": report.get("scanned_count"),
                "report_schema_version": report.get("schema_version"),
                "sample": report.get("flagged", [])[:3],
            },
        }
    ]


def persona_axis_report(root: Path | None) -> dict[str, Any] | None:
    if root is None or not (root / "docs" / "contracts").exists():
        return None
    try:
        from aios_persona_audit import build_report

        return build_report(root, window=20)
    except Exception as exc:  # pragma: no cover - advisory axis must not break monitor.
        return {
            "schema_version": "aios.persona_audit.unavailable.v1",
            "authority": "advisory_only",
            "error": str(exc),
            "scores": {"persona_composite": 0.0},
        }


def persona_axis_advisory(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    composite = (report.get("scores") or {}).get("persona_composite", 0.0)
    return [
        {
            "code": "persona_axis_advisory",
            "severity": "info",
            "owner": "myworld",
            "action": "review_5_persona_axis",
            "reason": "AIOS 5-persona cognitive architecture score is advisory and orthogonal to governance.",
            "alert": {
                "code": "persona_axis_advisory",
                "persona_composite": composite,
                "contracts_scored": report.get("contracts_scored"),
                "report_schema_version": report.get("schema_version"),
            },
        }
    ]


def assess_snapshot(data: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    findings = [assess_alert(alert) for alert in data.get("alerts", [])]
    findings.extend(genesis_critic_advisory(root))
    persona_report = persona_axis_report(root)
    findings.extend(persona_axis_advisory(persona_report))
    payload = {
        "schema_version": "aios.monitor.assessment.v1",
        "generated_at": now_iso(),
        "snapshot_generated_at": data.get("generated_at"),
        "health": health_from_findings(findings),
        "watched": {
            "contracts": len(data.get("contracts", [])),
            "dispatches": len(data.get("dispatches", [])),
            "repos": len(data.get("repos", [])),
            "alerts": len(data.get("alerts", [])),
            "reconciliations_applied": len(data.get("reconciliations_applied", [])),
        },
        "findings": findings,
        "next_actions": prioritized_actions(findings),
    }
    if persona_report is not None:
        payload["persona_axis"] = persona_report
    return payload


def payload_has_key(value: Any, key: str) -> bool:
    if isinstance(value, dict):
        if key in value:
            return True
        return any(payload_has_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(payload_has_key(child, key) for child in value)
    return False


def write_snapshot(root: Path, data: dict[str, Any]) -> None:
    path = root / MONITOR_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    latest = root / MONITOR_LATEST
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_assessment(root: Path, data: dict[str, Any]) -> None:
    path = root / MONITOR_ASSESSMENT_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")
    latest = root / MONITOR_ASSESSMENT_LATEST
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_monitor_event(root: Path, event: str, status: str, detail: str = "") -> None:
    path = root / MONITOR_EVENTS
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": now_iso(),
        "event": event,
        "status": status,
        "detail": detail,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def sidecar_paths(root: Path) -> tuple[Path, Path]:
    pid_path = root / MONITOR_PID
    stop_path = root / MONITOR_STOP
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    return pid_path, stop_path


def cmd_snapshot(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    data = snapshot(root)
    if args.write:
        write_snapshot(root, data)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"contracts={len(data['contracts'])} dispatches={len(data['dispatches'])} alerts={len(data['alerts'])}")
        for alert in data["alerts"]:
            print(f"- {alert['code']}: {alert}")
    if args.fail_on_alert and data["alerts"]:
        return 1
    return 0


def cmd_assess(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    data = snapshot(root)
    assessment = assess_snapshot(data, root=root)
    if args.write:
        write_snapshot(root, data)
        write_assessment(root, assessment)
    if args.json:
        print(json.dumps(assessment, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            f"health={assessment['health']} alerts={assessment['watched']['alerts']} "
            f"actions={len(assessment['next_actions'])}"
        )
        for action in assessment["next_actions"]:
            print(f"- {action['severity']} {action['owner']}: {action['action']}")
    if args.fail_on_blocked and assessment["health"] == "blocked":
        return 1
    missing = [key for key in args.require_key if not payload_has_key(assessment, key)]
    if missing:
        print(f"missing required keys: {', '.join(missing)}", file=sys.stderr)
        return 1
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    pid_path, stop_path = sidecar_paths(root)
    interval = max(1, int(args.interval))
    iterations = int(args.iterations)
    if iterations > 0:
        stop_path.unlink(missing_ok=True)
    if args.write_pid:
        pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    append_monitor_event(root, "sidecar_start", "running", f"interval={interval}")
    completed = 0
    try:
        while True:
            if stop_path.exists():
                append_monitor_event(root, "sidecar_stop", "stopped", stop_path.as_posix())
                return 0
            data = snapshot(root)
            assessment = assess_snapshot(data, root=root)
            write_snapshot(root, data)
            write_assessment(root, assessment)
            completed += 1
            if not args.quiet:
                print(
                    f"{data['generated_at']} contracts={len(data['contracts'])} "
                    f"dispatches={len(data['dispatches'])} alerts={len(data['alerts'])} "
                    f"health={assessment['health']}",
                    flush=True,
                )
            if iterations > 0 and completed >= iterations:
                append_monitor_event(root, "sidecar_done", "ok", f"iterations={completed}")
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        append_monitor_event(root, "sidecar_interrupt", "stopped", "keyboard_interrupt")
        return 130
    finally:
        if args.write_pid and read_pid(pid_path) == os.getpid():
            pid_path.unlink(missing_ok=True)


def cmd_start(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    pid_path, stop_path = sidecar_paths(root)
    pid = read_pid(pid_path)
    if pid and is_pid_running(pid):
        print(f"AIOS monitor sidecar already running: pid {pid}")
        return 0
    stop_path.unlink(missing_ok=True)
    log_dir = root / ".aios/logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "aios_monitor.sidecar.log"
    cmd = [
        sys.executable,
        Path(__file__).resolve().as_posix(),
        "run",
        "--interval",
        str(args.interval),
        "--write-pid",
    ]
    with log_path.open("ab") as log:
        proc = subprocess.Popen(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_path.write_text(f"{proc.pid}\n", encoding="utf-8")
    append_monitor_event(root, "sidecar_spawn", "running", f"pid={proc.pid}")
    print(f"started AIOS monitor sidecar pid {proc.pid}")
    print(f"log={log_path.relative_to(root).as_posix()}")
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    pid_path, stop_path = sidecar_paths(root)
    stop_path.write_text(f"{now_iso()}\n", encoding="utf-8")
    pid = read_pid(pid_path)
    if pid and is_pid_running(pid):
        os.kill(pid, signal.SIGTERM)
        append_monitor_event(root, "sidecar_stop_requested", "stopping", f"pid={pid}")
        print(f"stop requested for AIOS monitor sidecar pid {pid}")
    else:
        append_monitor_event(root, "sidecar_stop_requested", "not_running", "")
        print("stop requested; no running AIOS monitor sidecar")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path.cwd().resolve()
    pid_path, stop_path = sidecar_paths(root)
    pid = read_pid(pid_path)
    running = bool(pid and is_pid_running(pid))
    latest_path = root / MONITOR_LATEST
    assessment_path = root / MONITOR_ASSESSMENT_LATEST
    latest: dict[str, Any] = {}
    assessment: dict[str, Any] = {}
    if latest_path.exists():
        latest = json.loads(latest_path.read_text(encoding="utf-8"))
    if assessment_path.exists():
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    status = {
        "root": root.as_posix(),
        "pid_file": pid_path.relative_to(root).as_posix(),
        "running": running,
        "pid": pid if running else None,
        "stop_file": stop_path.exists(),
        "latest_snapshot": latest_path.relative_to(root).as_posix() if latest else None,
        "latest_assessment": assessment_path.relative_to(root).as_posix() if assessment else None,
        "latest_generated_at": latest.get("generated_at"),
        "latest_alert_count": len(latest.get("alerts", [])) if latest else None,
        "latest_reconciliations_applied": len(latest.get("reconciliations_applied", [])) if latest else None,
        "latest_health": assessment.get("health"),
        "latest_next_action_count": len(assessment.get("next_actions", [])) if assessment else None,
        "log": ".aios/logs/aios_monitor.sidecar.log",
    }
    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in status.items():
            print(f"{key}={value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AIOS control-plane monitor")
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot", help="emit one control-plane monitor snapshot")
    snap.add_argument("--json", action="store_true")
    snap.add_argument("--write", action="store_true", help="append to .aios/state/monitor.jsonl")
    snap.add_argument("--fail-on-alert", action="store_true")
    snap.set_defaults(func=cmd_snapshot)
    assess = sub.add_parser("assess", help="classify monitor alerts and propose owner/action triage")
    assess.add_argument("--json", action="store_true")
    assess.add_argument("--write", action="store_true", help="append snapshot and assessment to .aios/state")
    assess.add_argument("--fail-on-blocked", action="store_true")
    assess.add_argument("--require-key", action="append", default=[], help="key that must appear anywhere in assessment JSON")
    assess.set_defaults(func=cmd_assess)
    run = sub.add_parser("run", help="run the sidecar monitor loop in the foreground")
    run.add_argument("--interval", type=int, default=int(os.environ.get("AIOS_MONITOR_INTERVAL", "30")))
    run.add_argument("--iterations", type=int, default=0, help="0 means run until stopped")
    run.add_argument("--quiet", action="store_true")
    run.add_argument("--write-pid", action="store_true")
    run.set_defaults(func=cmd_run)
    start = sub.add_parser("start", help="start the background sidecar monitor")
    start.add_argument("--interval", type=int, default=int(os.environ.get("AIOS_MONITOR_INTERVAL", "30")))
    start.set_defaults(func=cmd_start)
    stop = sub.add_parser("stop", help="request sidecar monitor stop")
    stop.set_defaults(func=cmd_stop)
    status = sub.add_parser("status", help="show sidecar monitor status")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
